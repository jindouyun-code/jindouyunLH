#!/usr/bin/env python3
"""
批量回测 - 为所有组合生成 5%权益风险 和 50K固定风险 结果

基于已有的39个组合，为每个组合生成两种新的风险模式结果
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

# 39个组合 (趋势周期, 下单周期, 信号源, 止损源)
COMBOS = [
    ('6H', '3H', 'xy', 'ly'), ('8H', '3H', 'xy', 'ly'), ('6H', '3H', 'xy', 'xy'), ('8H', '3H', 'xy', 'xy'),
    ('1D', '8H', 'xy', 'xy'), ('3H', '1H', 'xy', 'ly'), ('12H', '6H', 'ly', 'ly'), ('4H', '2H', 'xy', 'ly'),
    ('1D', '6H', 'ly', 'ly'), ('1D', '8H', 'xy', 'ly'), ('8H', '4H', 'xy', 'ly'), ('8H', '4H', 'xy', 'xy'),
    ('4H', '2H', 'ly', 'ly'), ('12H', '4H', 'xy', 'xy'), ('1D', '6H', 'xy', 'ly'), ('12H', '6H', 'xy', 'ly'),
    ('12H', '6H', 'ly', 'xy'), ('12H', '4H', 'xy', 'ly'), ('4H', '2H', 'ly', 'xy'), ('6H', '2H', 'xy', 'ly'),
    ('1D', '8H', 'ly', 'xy'), ('6H', '2H', 'ly', 'xy'), ('8H', '4H', 'ly', 'xy'), ('12H', '4H', 'ly', 'xy'),
    ('4H', '2H', 'xy', 'xy'), ('6H', '2H', 'xy', 'xy'), ('1D', '6H', 'xy', 'xy'), ('8H', '3H', 'ly', 'xy'),
    ('6H', '3H', 'ly', 'xy'), ('3H', '1H', 'xy', 'xy'), ('12H', '6H', 'xy', 'xy'), ('6H', '2H', 'ly', 'ly'),
    ('1D', '8H', 'ly', 'ly'), ('12H', '4H', 'ly', 'ly'), ('3H', '1H', 'ly', 'xy'), ('8H', '3H', 'ly', 'ly'),
    ('6H', '3H', 'ly', 'ly'), ('3H', '1H', 'ly', 'ly'),
]

# 新的风险模式
NEW_RISK_MODES = [
    ('fixed_50k', 'fixed', 50000, 0, '50k'),
    ('pct_5pct', 'percentage', 0, 0.05, 'p5pct'),
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
    df_t = load_data(trend_tf)
    df_e = load_data(entry_tf)

    df_t = df_t.copy()
    df_t['trend'] = 0
    df_t.loc[df_t['close'] > df_t['祥云•主轨'], 'trend'] = 1
    df_t.loc[df_t['close'] < df_t['祥云•主轨'], 'trend'] = -1

    trend_map = []
    idx_t = 0
    for i in range(len(df_e)):
        t_e = df_e.iloc[i]['time']
        while idx_t < len(df_t) and df_t.iloc[idx_t]['time'] <= t_e:
            idx_t += 1
        trend_map.append(df_t.iloc[idx_t - 1]['trend'] if idx_t > 0 else 0)

    df_e = df_e.copy()
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

    return df_e


class Trade:
    def __init__(self, side, et, ep, sp, stake):
        self.side, self.entry_time, self.entry_price, self.stop_price, self.stake = side, et, ep, sp, stake
        self.exit_time, self.exit_price, self.pnl, self.closed = None, None, 0, False
        self.entry_fee, self.exit_fee, self.slippage_cost = 0, 0, 0
        self.exit_reason = ""

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


def run_backtest_full(df, risk_mode, risk_amount, risk_pct):
    """完整回测，返回交易列表和权益曲线"""
    capital = INITIAL_CAPITAL
    long_pos = short_pos = None
    trades = []
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
                capital += long_pos.pnl; long_pos = None

        if short_pos:
            short_pos.check_stop(cp, ct)
            if short_pos.closed and short_pos.exit_time == ct:
                capital += short_pos.pnl; short_pos = None

        trend = row['trend']

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
        long_pos.close(lr['close'], lr['time'], "end_of_data"); capital += long_pos.pnl; long_pos = None
    if short_pos and not short_pos.closed:
        short_pos.close(lr['close'], lr['time'], "end_of_data"); capital += short_pos.pnl; short_pos = None

    return trades, equity_curve


def save_results(trades, equity_curve, prefix):
    """保存结果为CSV"""
    trades_data = []
    for t in trades:
        if not t.closed: continue
        trades_data.append({
            'side': t.side, 'entry_time': str(t.entry_time), 'entry_price': t.entry_price,
            'exit_time': str(t.exit_time), 'exit_price': t.exit_price, 'stake': t.stake,
            'pnl': t.pnl, 'entry_fee': t.entry_fee, 'exit_fee': t.exit_fee,
            'slippage_cost': t.slippage_cost, 'exit_reason': t.exit_reason
        })
    
    trades_df = pd.DataFrame(trades_data)
    equity_df = pd.DataFrame(equity_curve)
    equity_df['time'] = equity_df['time'].astype(str)
    
    trades_df.to_csv(os.path.join(OUTPUT_DIR, f"{prefix}_trades.csv"), index=False)
    equity_df.to_csv(os.path.join(OUTPUT_DIR, f"{prefix}_equity.csv"), index=False)
    
    return len(trades_data)


if __name__ == "__main__":
    print("=" * 120)
    print("批量回测 - 50K固定风险 + 5%权益风险")
    print("=" * 120)
    
    total_combos = len(COMBOS) * len(NEW_RISK_MODES)
    current = 0
    
    for trend_tf, entry_tf, sig_src, stop_src in COMBOS:
        # 准备数据
        df = prepare_data(trend_tf, entry_tf, sig_src, stop_src)
        
        for rm_id, rm_mode, rm_amount, rm_pct, rm_suffix in NEW_RISK_MODES:
            current += 1
            prefix = f"ss_{trend_tf.lower()}_{entry_tf.lower()}_{sig_src}_{stop_src}_{rm_suffix}"
            
            print(f"[{current}/{total_combos}] {trend_tf}+{entry_tf} ({sig_src}/{stop_src}) - {rm_suffix}...", end=" ")
            
            try:
                trades, equity = run_backtest_full(df, rm_mode, rm_amount, rm_pct)
                num_trades = save_results(trades, equity, prefix)
                
                # 计算简单统计
                closed = [t for t in trades if t.closed]
                wins = [t for t in closed if t.pnl > 0]
                ret = sum(t.pnl for t in closed) / INITIAL_CAPITAL * 100
                wr = len(wins) / len(closed) * 100 if closed else 0
                
                print(f"交易:{num_trades}, 收益:{ret:.1f}%, 胜率:{wr:.1f}%")
            except Exception as e:
                print(f"错误: {e}")
    
    print("\n" + "=" * 120)
    print("批量回测完成！")
    print("=" * 120)
