#!/usr/bin/env python3
"""
保存所有信号止损组合的回测结果到 backtest_results 目录
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

# 测试组合
TEST_COMBOS = [
    ('12H', '6H'), ('6H', '3H'), ('8H', '3H'), ('1D', '8H'),
    ('12H', '4H'), ('8H', '4H'), ('4H', '2H'), ('3H', '1H'),
    ('6H', '2H'), ('1D', '6H'),
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
                if sp < ep:
                    sz = calc_size(ep, sp)
                    if sz > 0 and capital >= sz * 0.1:
                        long_pos = Trade('long', et, ep, sp, sz); trades.append(long_pos)

        if row['short_break'] == 1 and short_pos is None and long_pos is None:
            if trend <= 0 and i + 1 < len(df):
                nr = df.iloc[i + 1]; ep, sp, et = nr['open'], nr['stop_line'], nr['time']
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
    recs = [{'side':t.side,'entry_time':t.entry_time,'entry_price':t.entry_price,'stop_price':t.stop_price,
             'stake':t.stake,'exit_time':t.exit_time,'exit_price':t.exit_price,'pnl':t.pnl,
             'entry_fee':t.entry_fee,'exit_fee':t.exit_fee,'slippage_cost':t.slippage_cost,'exit_reason':t.exit_reason} for t in ct]

    edf = pd.DataFrame(equity_curve)
    return pd.DataFrame(recs), edf


def prepare_and_run(trend_tf, entry_tf, sig_src, stop_src, cid_prefix):
    df_t = load_data(trend_tf).copy()
    df_t['trend'] = 0
    df_t.loc[df_t['close'] > df_t['祥云•主轨'], 'trend'] = 1
    df_t.loc[df_t['close'] < df_t['祥云•主轨'], 'trend'] = -1

    df_e = load_data(entry_tf).copy()

    trend_map = []
    idx_t = 0
    for i in range(len(df_e)):
        t_e = df_e.iloc[i]['time']
        while idx_t < len(df_t) and df_t.iloc[idx_t]['time'] <= t_e:
            idx_t += 1
        trend_map.append(df_t.iloc[idx_t - 1]['trend'] if idx_t > 0 else 0)

    df_e['trend'] = trend_map

    if sig_src == 'xy':
        df_e['long_break'] = df_e['祥云•多头涨破⬆']
        df_e['short_break'] = df_e['祥云•空头跌破⬇']
    else:
        df_e['long_break'] = df_e['灵云•多头涨破⬆']
        df_e['short_break'] = df_e['灵云•空头跌破⬇']

    if stop_src == 'xy':
        df_e['stop_line'] = df_e['祥云•主轨']
    else:
        df_e['stop_line'] = df_e['灵云•主轨']

    for rm, ra, rpct, rlabel in [('fixed', 20000, 0, 'fixed'), ('percentage', 0, 0.02, 'pct')]:
        cid = f"{cid_prefix}_{rlabel}"
        tdf, edf = run_backtest(df_e, rm, ra, rpct, use_trend=True)
        tdf.to_csv(os.path.join(OUTPUT_DIR, f"{cid}_trades.csv"), index=False)
        edf.to_csv(os.path.join(OUTPUT_DIR, f"{cid}_equity.csv"), index=False)
        print(f"  已保存: {cid}")


if __name__ == "__main__":
    sig_stop_map = {
        'xy_xy': ('xy', 'xy'),
        'xy_ly': ('xy', 'ly'),
        'ly_xy': ('ly', 'xy'),
        'ly_ly': ('ly', 'ly'),
    }

    for trend_tf, entry_tf in TEST_COMBOS:
        print(f"\n趋势={trend_tf} 下单={entry_tf}")
        t_lower = trend_tf.lower().replace('d', 'd')
        e_lower = entry_tf.lower()
        for ss_label, (sig_src, stop_src) in sig_stop_map.items():
            cid_prefix = f"ss_{t_lower}_{e_lower}_{ss_label}"
            prepare_and_run(trend_tf, entry_tf, sig_src, stop_src, cid_prefix)

    print("\n所有信号止损组合结果已保存!")
