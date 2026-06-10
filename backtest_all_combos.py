#!/usr/bin/env python3
"""
批量多周期共振回测 - 17种组合全测

策略逻辑:
  趋势判断: 收盘价 > 祥云主轨 → 多头趋势, 收盘价 < 祥云主轨 → 空头趋势
  入场: 多头趋势只做多, 空头趋势只做空
  止损: 灵云主轨动态止损

每种组合测试两种资金模式: 固定$20K + 2%权益
"""

import pandas as pd
import numpy as np
import os
import sys

INITIAL_CAPITAL = 1_000_000
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0005
OUTPUT_DIR = "/home/parallels/wwwroot/jindouyunLH/backtest_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATA_DIR = "/home/parallels/wwwroot/jindouyunLH/TV 数据"

# 数据文件映射
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

# 17种有效组合 (趋势周期, 下单周期, 比例)
COMBOS = [
    ('1D', '4H', '6:1'), ('1D', '6H', '4:1'), ('1D', '8H', '3:1'), ('1D', '12H', '2:1'),
    ('12H', '2H', '6:1'), ('12H', '3H', '4:1'), ('12H', '4H', '3:1'), ('12H', '6H', '2:1'),
    ('8H', '2H', '4:1'), ('8H', '3H', '2.7:1'), ('8H', '4H', '2:1'),
    ('6H', '1H', '6:1'), ('6H', '2H', '3:1'), ('6H', '3H', '2:1'),
    ('4H', '1H', '4:1'), ('4H', '2H', '2:1'),
    ('3H', '1H', '3:1'),
]

# 数据缓存
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


def prepare_data(trend_tf, entry_tf):
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
    df_e['xy_long_break'] = df_e['祥云•多头涨破⬆']
    df_e['xy_short_break'] = df_e['祥云•空头跌破⬇']
    df_e['ly_main'] = df_e['灵云•主轨']

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
        cp, ct, ly = row['close'], row['time'], row['ly_main']

        if long_pos and not long_pos.closed: long_pos.update_stop(ly)
        if short_pos and not short_pos.closed: short_pos.update_stop(ly)

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

        if row['xy_long_break'] == 1 and long_pos is None and short_pos is None:
            if trend >= 0 and i + 1 < len(df):
                nr = df.iloc[i + 1]; ep, sp, et = nr['open'], nr['ly_main'], nr['time']
                if sp < ep:
                    sz = calc_size(ep, sp)
                    if sz > 0 and capital >= sz * 0.1:
                        long_pos = Trade('long', et, ep, sp, sz); trades.append(long_pos)

        if row['xy_short_break'] == 1 and short_pos is None and long_pos is None:
            if trend <= 0 and i + 1 < len(df):
                nr = df.iloc[i + 1]; ep, sp, et = nr['open'], nr['ly_main'], nr['time']
                if sp > ep:
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
        'total_fees': total_fees, 'total_slippage': total_slippage,
    }


if __name__ == "__main__":
    print("=" * 140)
    print("批量多周期共振回测 - 17种组合")
    print("=" * 140)

    all_results = []
    total = len(COMBOS) * 2  # 每种组合2种资金模式

    for idx, (trend_tf, entry_tf, ratio) in enumerate(COMBOS):
        print(f"\n[{idx*2+1}/{total}] 趋势={trend_tf} 下单={entry_tf} 比例={ratio} 加载数据...")
        df = prepare_data(trend_tf, entry_tf)

        for rm, ra, rpct, label in [('fixed', 20000, 0, '固定$20K'), ('percentage', 0, 0.02, '2%权益')]:
            stats = run_backtest(df, rm, ra, rpct, use_trend=True)
            baseline = run_backtest(df, rm, ra, rpct, use_trend=False)

            label_short = f"{trend_tf}+{entry_tf}({label})"
            bl_label = f"纯{entry_tf}({label})"

            # 保存趋势过滤结果
            cid = f"multi_{trend_tf.lower().replace('d','d')}_{entry_tf.lower()}_{rm[:3]}"
            all_results.append({
                'combo': label_short, 'type': '共振', 'ratio': ratio,
                **stats
            })
            all_results.append({
                'combo': bl_label, 'type': '纯下单', 'ratio': ratio,
                **baseline
            })

            print(f"  {label_short:<25} | 交易:{stats['total_trades']:>4} | 胜率:{stats['win_rate']:>6.2f}% | "
                  f"盈亏比:{stats['profit_factor']:>6.2f} | 收益:{stats['return_pct']:>8.2f}% | 回撤:{stats['max_drawdown']:>8.2f}%")
            print(f"  {bl_label:<25} | 交易:{baseline['total_trades']:>4} | 胜率:{baseline['win_rate']:>6.2f}% | "
                  f"盈亏比:{baseline['profit_factor']:>6.2f} | 收益:{baseline['return_pct']:>8.2f}% | 回撤:{baseline['max_drawdown']:>8.2f}%")

    # 最终汇总
    print("\n" + "=" * 160)
    print("全部17种组合对比汇总")
    print("=" * 160)
    print(f"{'组合':<25} | {'类型':<6} | {'比例':<6} | {'交易':>5} | {'多':>4} | {'空':>4} | {'胜率':>7} | "
          f"{'盈亏比':>7} | {'收益率':>9} | {'回撤':>9}")
    print("-" * 160)

    for r in all_results:
        print(f"{r['combo']:<25} | {r['type']:<6} | {r['ratio']:<6} | {r['total_trades']:>5} | "
              f"{r['long_trades']:>4} | {r['short_trades']:>4} | {r['win_rate']:>6.2f}% | "
              f"{r['profit_factor']:>7.2f} | {r['return_pct']:>8.2f}% | {r['max_drawdown']:>8.2f}%")

    # 共振模式 Top 10 按收益率排序
    multi = [r for r in all_results if r['type'] == '共振' and '2%权益' in r['combo']]
    multi.sort(key=lambda x: x['return_pct'], reverse=True)

    print("\n" + "=" * 140)
    print("共振策略 Top 10 (2%权益模式, 按收益率排序)")
    print("=" * 140)
    print(f"{'组合':<25} | {'比例':<6} | {'交易':>5} | {'胜率':>7} | {'盈亏比':>7} | {'收益率':>9} | {'回撤':>9}")
    print("-" * 140)
    for r in multi[:10]:
        print(f"{r['combo']:<25} | {r['ratio']:<6} | {r['total_trades']:>5} | {r['win_rate']:>6.2f}% | "
              f"{r['profit_factor']:>7.2f} | {r['return_pct']:>8.2f}% | {r['max_drawdown']:>8.2f}%")

    # 共振模式 Top 10 按回撤排序
    multi_dd = sorted(multi, key=lambda x: abs(x['max_drawdown']))
    print("\n" + "=" * 140)
    print("共振策略 Top 10 (2%权益模式, 按回撤从小到大排序)")
    print("=" * 140)
    print(f"{'组合':<25} | {'比例':<6} | {'交易':>5} | {'胜率':>7} | {'盈亏比':>7} | {'收益率':>9} | {'回撤':>9}")
    print("-" * 140)
    for r in multi_dd[:10]:
        print(f"{r['combo']:<25} | {r['ratio']:<6} | {r['total_trades']:>5} | {r['win_rate']:>6.2f}% | "
              f"{r['profit_factor']:>7.2f} | {r['return_pct']:>8.2f}% | {r['max_drawdown']:>8.2f}%")
