#!/usr/bin/env python3
"""
信号止损组合测试 - 祥云信号/灵云信号 × 祥云止损/灵云止损

信号来源(下单周期): 祥云涨破跌破 / 灵云涨破跌破
止损来源(下单周期): 祥云主轨 / 灵云主轨
趋势过滤(趋势周期): 收盘价 > 祥云主轨

4种组合:
  1. 祥云信号 + 祥云止损
  2. 祥云信号 + 灵云止损 (原策略)
  3. 灵云信号 + 祥云止损
  4. 灵云信号 + 灵云止损
"""

import pandas as pd
import numpy as np
import os

INITIAL_CAPITAL = 1_000_000
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0005
OUTPUT_DIR = "/home/parallels/wwwroot/jindouyunLH/backtest_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATA_DIR = "/home/parallels/wwwroot/jindouyunLH/TV 数据"
DATA_FILES = {
    '1H':  f"{DATA_DIR}/BYBIT_BTCUSDT.P, 60_b5370.csv",
    '2H':  f"{DATA_DIR}/BYBIT_BTCUSDT.P, 120_f98f9.csv",
    '3H':  f"{DATA_DIR}/BYBIT_BTCUSDT.P, 180_87830.csv",
    '4H':  f"{DATA_DIR}/BYBIT_BTCUSDT.P, 240_867c7.csv",
    '6H':  f"{DATA_DIR}/BYBIT_BTCUSDT.P, 360_746a8.csv",
    '8H':  f"{DATA_DIR}/BYBIT_BTCUSDT.P, 480_76a54.csv",
    '12H': f"{DATA_DIR}/BYBIT_BTCUSDT.P, 720_fbcb7.csv",
    '1D':  f"{DATA_DIR}/BYBIT_BTCUSDT.P, 1D_56132.csv",
}

# 测试组合: (趋势周期, 下单周期)
TEST_COMBOS = [
    ('12H', '6H'),
    ('6H', '3H'),
    ('8H', '3H'),
    ('1D', '8H'),
    ('12H', '4H'),
    ('8H', '4H'),
    ('4H', '2H'),
    ('3H', '1H'),
    ('6H', '2H'),
    ('1D', '6H'),
]

_data_cache = {}


def load_data(tf):
    if tf not in _data_cache:
        df = pd.read_csv(DATA_FILES[tf])
        df['time'] = pd.to_datetime(df['time'])
        try: df['time'] = df['time'].dt.tz_localize('Asia/Shanghai')
        except TypeError: df['time'] = df['time'].dt.tz_convert('Asia/Shanghai')
        df = df.sort_values('time').reset_index(drop=True)
        _data_cache[tf] = df
    return _data_cache[tf]


def prepare_data(trend_tf, entry_tf, sig_src, stop_src):
    """加载数据并映射趋势"""
    df_t = load_data(trend_tf)
    df_e = load_data(entry_tf)

    # 趋势: 收盘价 > 祥云主轨 = 多头
    df_t = df_t.copy()
    df_t['trend'] = 0
    df_t.loc[df_t['close'] > df_t['祥云•主轨'], 'trend'] = 1
    df_t.loc[df_t['close'] < df_t['祥云•主轨'], 'trend'] = -1

    # 映射趋势到下单时间轴
    trend_map = []
    idx_t = 0
    for i in range(len(df_e)):
        t_e = df_e.iloc[i]['time']
        while idx_t < len(df_t) and df_t.iloc[idx_t]['time'] <= t_e:
            idx_t += 1
        trend_map.append(df_t.iloc[idx_t - 1]['trend'] if idx_t > 0 else 0)

    df_e = df_e.copy()
    df_e['trend'] = trend_map

    # 信号来源
    if sig_src == 'xy':
        df_e['long_break'] = df_e['祥云•多头涨破⬆']
        df_e['short_break'] = df_e['祥云•空头跌破⬇']
    else:  # ly
        df_e['long_break'] = df_e['灵云•多头涨破⬆']
        df_e['short_break'] = df_e['灵云•空头跌破⬇']

    # 止损来源
    if stop_src == 'xy':
        df_e['stop_line'] = df_e['祥云•主轨']
    else:  # ly
        df_e['stop_line'] = df_e['灵云•主轨']

    return df_e


class Trade:
    def __init__(self, side, et, ep, sp, stake):
        self.side, self.entry_time, self.entry_price, self.stop_price, self.stake = side, et, ep, sp, stake
        self.exit_time, self.exit_price, self.pnl, self.closed = None, None, 0, False
        self.entry_fee, self.exit_fee, self.slippage_cost = 0, 0, 0

    def check_stop(self, cp, ct):
        if self.closed: return False
        if self.side == 'long' and cp <= self.stop_price:
            self.close(cp, ct, "stop_loss"); return True
        if self.side == 'short' and cp >= self.stop_price:
            self.close(cp, ct, "stop_loss"); return True
        return False

    def update_stop(self, nsp):
        if self.side == 'long' and nsp > self.stop_price: self.stop_price = nsp
        if self.side == 'short' and nsp < self.stop_price: self.stop_price = nsp

    def close(self, price, time, reason=""):
        if self.closed: return
        self.exit_time, self.exit_price, self.closed = time, price * (1 + SLIPPAGE_RATE if self.side == 'long' else 1 - SLIPPAGE_RATE), True
        self.entry_fee = self.stake * FEE_RATE; self.exit_fee = self.stake * FEE_RATE
        slip = self.entry_price * SLIPPAGE_RATE + self.exit_price * SLIPPAGE_RATE
        self.slippage_cost = self.stake * (slip / self.entry_price)
        pc = (self.exit_price - self.entry_price) / self.entry_price if self.side == 'long' else (self.entry_price - self.exit_price) / self.entry_price
        self.pnl = self.stake * pc - self.entry_fee - self.exit_fee - self.slippage_cost
        self.exit_reason = reason


def run_backtest(df, risk_mode, risk_amount, risk_pct, use_trend):
    capital = INITIAL_CAPITAL
    long_pos = short_pos = None
    trades = []
    total_fees = total_slippage = 0
    equity_curve = []

    def calc_size(ep, sp):
        r = abs(ep - sp) / ep
        if r == 0 or r > 0.5: return 0
        if risk_mode == 'fixed': return risk_amount / r
        return (capital * risk_pct) / r

    for i in range(1, len(df)):
        row = df.iloc[i]
        cp, ct, sl = row['close'], row['time'], row['stop_line']

        if long_pos and not long_pos.closed: long_pos.update_stop(sl)
        if short_pos and not short_pos.closed: short_pos.update_stop(sl)

        if long_pos:
            long_pos.check_stop(cp, ct)
            if long_pos.closed and long_pos.exit_time == ct:
                capital += long_pos.pnl; total_fees += long_pos.entry_fee + long_pos.exit_fee
                total_slippage += long_pos.slippage_cost; long_pos = None

        if short_pos:
            short_pos.check_stop(cp, ct)
            if short_pos.closed and short_pos.exit_time == ct:
                capital += short_pos.pnl; total_fees += short_pos.entry_fee + short_pos.exit_fee
                total_slippage += short_pos.slippage_cost; short_pos = None

        trend = row['trend'] if use_trend else 0

        if row['long_break'] == 1 and long_pos is None and short_pos is None:
            if trend >= 0 and i + 1 < len(df):
                nr = df.iloc[i + 1]; ep, sp, et = nr['open'], nr['stop_line'], nr['time']
                if (side := ('long' if sp < ep else None)):
                    sz = calc_size(ep, sp)
                    if sz > 0 and capital >= sz * 0.1:
                        long_pos = Trade('long', et, ep, sp, sz); trades.append(long_pos)

        if row['short_break'] == 1 and short_pos is None and long_pos is None:
            if trend <= 0 and i + 1 < len(df):
                nr = df.iloc[i + 1]; ep, sp, et = nr['open'], nr['stop_line'], nr['time']
                if (side := ('short' if sp > ep else None)):
                    sz = calc_size(ep, sp)
                    if sz > 0 and capital >= sz * 0.1:
                        short_pos = Trade('short', et, ep, sp, sz); trades.append(short_pos)

        eq = capital
        if long_pos and not long_pos.closed: eq += (cp - long_pos.entry_price) / long_pos.entry_price * long_pos.stake
        if short_pos and not short_pos.closed: eq += (short_pos.entry_price - cp) / short_pos.entry_price * short_pos.stake
        equity_curve.append({'time': ct, 'equity': eq})

    lr = df.iloc[-1]
    if long_pos and not long_pos.closed:
        long_pos.close(lr['close'], lr['time'], "end_of_data"); capital += long_pos.pnl
        total_fees += long_pos.entry_fee + long_pos.exit_fee; total_slippage += long_pos.slippage_cost; long_pos = None
    if short_pos and not short_pos.closed:
        short_pos.close(lr['close'], lr['time'], "end_of_data"); capital += short_pos.pnl
        total_fees += short_pos.entry_fee + short_pos.exit_fee; total_slippage += short_pos.slippage_cost; short_pos = None

    ct = [t for t in trades if t.closed]
    lt = [t for t in ct if t.side == 'long']; st = [t for t in ct if t.side == 'short']
    wt = [t for t in ct if t.pnl > 0]
    tpnl = capital - INITIAL_CAPITAL; rp = tpnl / INITIAL_CAPITAL * 100
    wr = len(wt) / len(ct) * 100 if ct else 0
    aw = np.mean([t.pnl for t in wt]) if wt else 0
    al = abs(np.mean([t.pnl for t in ct if t.pnl <= 0])) if (len(ct) - len(wt)) > 0 else 0
    pf = aw / al if al > 0 else 0

    edf = pd.DataFrame(equity_curve)
    edf['peak'] = edf['equity'].cummax(); edf['dd'] = (edf['equity'] - edf['peak']) / edf['peak'] * 100
    md = edf['dd'].min()

    return {
        'total_trades': len(ct), 'long_trades': len(lt), 'short_trades': len(st),
        'win_rate': wr, 'profit_factor': pf, 'return_pct': rp, 'max_drawdown': md,
    }


if __name__ == "__main__":
    print("=" * 160)
    print("信号止损组合测试 - 祥云/灵云信号 × 祥云/灵云止损")
    print("=" * 160)

    sig_stop_combos = [
        ('xy', 'xy', '祥云信号+祥云止损'),
        ('xy', 'ly', '祥云信号+灵云止损(原)'),
        ('ly', 'xy', '灵云信号+祥云止损'),
        ('ly', 'ly', '灵云信号+灵云止损'),
    ]

    all_results = []

    for trend_tf, entry_tf in TEST_COMBOS:
        print(f"\n{'='*100}")
        print(f"趋势={trend_tf} 下单={entry_tf}")
        print(f"{'='*100}")
        print(f"{'信号止损组合':<25} | {'交易':>5} | {'多':>4} | {'空':>4} | {'胜率':>7} | {'盈亏比':>7} | {'收益率':>9} | {'回撤':>9}")
        print("-"*100)

        for sig_src, stop_src, label in sig_stop_combos:
            df = prepare_data(trend_tf, entry_tf, sig_src, stop_src)
            stats = run_backtest(df, 'percentage', 0, 0.02, use_trend=True)
            all_results.append({
                'trend_tf': trend_tf, 'entry_tf': entry_tf, 'combo': label,
                **stats
            })

            print(f"{label:<25} | {stats['total_trades']:>5} | {stats['long_trades']:>4} | {stats['short_trades']:>4} | "
                  f"{stats['win_rate']:>6.2f}% | {stats['profit_factor']:>7.2f} | {stats['return_pct']:>8.2f}% | {stats['max_drawdown']:>8.2f}%")

    # 汇总排序
    print("\n" + "=" * 160)
    print("全部信号止损组合汇总 (2%权益, 趋势过滤)")
    print("=" * 160)
    print(f"{'组合':<15} | {'信号止损':<20} | {'交易':>5} | {'多':>4} | {'空':>4} | {'胜率':>7} | {'盈亏比':>7} | {'收益率':>9} | {'回撤':>9}")
    print("-"*160)

    for r in all_results:
        print(f"{r['trend_tf']+r['entry_tf']:<15} | {r['combo']:<20} | {r['total_trades']:>5} | {r['long_trades']:>4} | {r['short_trades']:>4} | "
              f"{r['win_rate']:>6.2f}% | {r['profit_factor']:>7.2f} | {r['return_pct']:>8.2f}% | {r['max_drawdown']:>8.2f}%")

    # 按收益率 Top
    sorted_ret = sorted(all_results, key=lambda x: x['return_pct'], reverse=True)
    print("\n" + "=" * 140)
    print("收益率 Top 15")
    print("=" * 140)
    print(f"{'组合':<15} | {'信号止损':<20} | {'交易':>5} | {'胜率':>7} | {'盈亏比':>7} | {'收益率':>9} | {'回撤':>9}")
    print("-"*140)
    for r in sorted_ret[:15]:
        print(f"{r['trend_tf']+r['entry_tf']:<15} | {r['combo']:<20} | {r['total_trades']:>5} | {r['win_rate']:>6.2f}% | "
              f"{r['profit_factor']:>7.2f} | {r['return_pct']:>8.2f}% | {r['max_drawdown']:>8.2f}%")

    # 按回撤 Top
    sorted_dd = sorted(all_results, key=lambda x: abs(x['max_drawdown']))
    print("\n" + "=" * 140)
    print("回撤最小 Top 15")
    print("=" * 140)
    print(f"{'组合':<15} | {'信号止损':<20} | {'交易':>5} | {'胜率':>7} | {'盈亏比':>7} | {'收益率':>9} | {'回撤':>9}")
    print("-"*140)
    for r in sorted_dd[:15]:
        print(f"{r['trend_tf']+r['entry_tf']:<15} | {r['combo']:<20} | {r['total_trades']:>5} | {r['win_rate']:>6.2f}% | "
              f"{r['profit_factor']:>7.2f} | {r['return_pct']:>8.2f}% | {r['max_drawdown']:>8.2f}%")
