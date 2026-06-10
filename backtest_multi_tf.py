#!/usr/bin/env python3
"""
多周期共振回测 - 8H趋势过滤 + 2H下单

策略逻辑:
  趋势判断(8H): 收盘价 > 祥云主轨 → 多头趋势, 收盘价 < 祥云主轨 → 空头趋势
  入场(2H): 多头趋势只做多, 空头趋势只做空
  止损(2H): 灵云主轨动态止损

资金管理:
  初始资金: 1,000,000
  每单风险: 2% 权益 / 固定 $20,000

交易成本:
  手续费: 万分之五 (开仓+平仓)
  滑点: 万分之五
"""

import pandas as pd
import numpy as np
import os

INITIAL_CAPITAL = 1_000_000
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0005
OUTPUT_DIR = "/home/parallels/wwwroot/jindouyunLH/backtest_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATA_8H = "/home/parallels/wwwroot/jindouyunLH/TV 数据/BYBIT_BTCUSDT.P, 480_76a54.csv"
DATA_2H = "/home/parallels/wwwroot/jindouyunLH/TV 数据/BYBIT_BTCUSDT.P, 120_f98f9.csv"


def load_and_prepare_data(file_8h, file_2h):
    """加载 8H 和 2H 数据, 将 8H 趋势映射到 2H 时间轴"""
    df_8h = pd.read_csv(file_8h)
    df_8h['time'] = pd.to_datetime(df_8h['time'])
    df_8h = df_8h.sort_values('time').reset_index(drop=True)

    df_2h = pd.read_csv(file_2h)
    df_2h['time'] = pd.to_datetime(df_2h['time'])
    df_2h = df_2h.sort_values('time').reset_index(drop=True)

    # 8H 趋势: 收盘价 > 祥云主轨 = 多头, < = 空头
    df_8h['trend'] = 0
    df_8h.loc[df_8h['close'] > df_8h['祥云•主轨'], 'trend'] = 1
    df_8h.loc[df_8h['close'] < df_8h['祥云•主轨'], 'trend'] = -1

    # 将 8H 趋势映射到 2H 时间轴
    trend_map = []
    idx_8h = 0
    for i in range(len(df_2h)):
        time_2h = df_2h.iloc[i]['time']
        while idx_8h < len(df_8h) and df_8h.iloc[idx_8h]['time'] <= time_2h:
            idx_8h += 1
        if idx_8h > 0:
            trend_map.append(df_8h.iloc[idx_8h - 1]['trend'])
        else:
            trend_map.append(0)

    df_2h['trend_8h'] = trend_map
    df_2h['xy_main'] = df_2h['祥云•主轨']
    df_2h['xy_long_break'] = df_2h['祥云•多头涨破⬆']
    df_2h['xy_short_break'] = df_2h['祥云•空头跌破⬇']
    df_2h['ly_main'] = df_2h['灵云•主轨']

    print(f"8H 数据: {len(df_8h)} 根K线, 范围 {df_8h['time'].iloc[0]} 至 {df_8h['time'].iloc[-1]}")
    print(f"2H 数据: {len(df_2h)} 根K线, 范围 {df_2h['time'].iloc[0]} 至 {df_2h['time'].iloc[-1]}")

    long_count = len(df_2h[df_2h['trend_8h'] == 1])
    short_count = len(df_2h[df_2h['trend_8h'] == -1])
    neutral_count = len(df_2h[df_2h['trend_8h'] == 0])
    total = len(df_2h)
    print(f"趋势分布: 多头{long_count}根({long_count/total*100:.1f}%), "
          f"空头{short_count}根({short_count/total*100:.1f}%), "
          f"震荡{neutral_count}根({neutral_count/total*100:.1f}%)")

    return df_2h


class Trade:
    def __init__(self, side, entry_time, entry_price, stop_price, stake):
        self.side = side
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.stake = stake
        self.exit_time = None
        self.exit_price = None
        self.pnl = 0
        self.closed = False
        self.entry_fee = 0
        self.exit_fee = 0
        self.slippage_cost = 0

    def check_stop(self, cp, ct):
        if self.closed: return False
        if self.side == 'long' and cp <= self.stop_price:
            self.close(cp, ct, "stop_loss"); return True
        if self.side == 'short' and cp >= self.stop_price:
            self.close(cp, ct, "stop_loss"); return True
        return False

    def update_stop(self, nsp):
        if self.side == 'long' and nsp > self.stop_price:
            self.stop_price = nsp
        if self.side == 'short' and nsp < self.stop_price:
            self.stop_price = nsp

    def apply_slippage(self, price):
        return price * (1 + SLIPPAGE_RATE) if self.side == 'long' else price * (1 - SLIPPAGE_RATE)

    def close(self, price, time, reason=""):
        if self.closed: return
        self.exit_time = time
        self.exit_price = self.apply_slippage(price)
        self.closed = True
        self.entry_fee = self.stake * FEE_RATE
        self.exit_fee = self.stake * FEE_RATE
        total_fee = self.entry_fee + self.exit_fee
        slip = self.entry_price * SLIPPAGE_RATE + self.exit_price * SLIPPAGE_RATE
        self.slippage_cost = self.stake * (slip / self.entry_price)
        pc = (self.exit_price - self.entry_price) / self.entry_price if self.side == 'long' else (self.entry_price - self.exit_price) / self.entry_price
        self.pnl = self.stake * pc - total_fee - self.slippage_cost
        self.exit_reason = reason


class MultiTFBacktest:
    def __init__(self, df, ic, rm='fixed', ra=20000, rp=0.02):
        self.df = df
        self.capital = ic
        self.initial_capital = ic
        self.risk_mode = rm
        self.risk_amount = ra
        self.risk_pct = rp
        self.trades = []
        self.long_pos = None
        self.short_pos = None
        self.equity_curve = []
        self.total_fees = 0
        self.total_slippage = 0

    def calc_size(self, ep, sp):
        r = abs(ep - sp) / ep
        if r == 0 or r > 0.5: return 0
        if self.risk_mode == 'fixed': return self.risk_amount / r
        return (self.capital * self.risk_pct) / r

    def run(self, use_trend=True):
        mode = "8H趋势+2H下单" if use_trend else "纯2H(对照)"
        print(f"\n{'='*80}")
        print(f"回测模式: {mode} | 风险: {'固定$' + f'{self.risk_amount:,.0f}' if self.risk_mode == 'fixed' else f'{self.risk_pct*100:.0f}% 权益'}")
        print(f"{'='*80}")

        for i in range(1, len(self.df)):
            row = self.df.iloc[i]
            cp, ct, ly = row['close'], row['time'], row['ly_main']

            if self.long_pos and not self.long_pos.closed: self.long_pos.update_stop(ly)
            if self.short_pos and not self.short_pos.closed: self.short_pos.update_stop(ly)

            if self.long_pos:
                self.long_pos.check_stop(cp, ct)
                if self.long_pos.closed and self.long_pos.exit_time == ct:
                    self.capital += self.long_pos.pnl
                    self.total_fees += self.long_pos.entry_fee + self.long_pos.exit_fee
                    self.total_slippage += self.long_pos.slippage_cost
                    self.long_pos = None

            if self.short_pos:
                self.short_pos.check_stop(cp, ct)
                if self.short_pos.closed and self.short_pos.exit_time == ct:
                    self.capital += self.short_pos.pnl
                    self.total_fees += self.short_pos.entry_fee + self.short_pos.exit_fee
                    self.total_slippage += self.short_pos.slippage_cost
                    self.short_pos = None

            trend = row['trend_8h'] if use_trend else 0

            # 做多: 多头趋势(或无过滤) + 祥云多头涨破
            if row['xy_long_break'] == 1 and self.long_pos is None and self.short_pos is None:
                if trend >= 0 and i + 1 < len(self.df):
                    nr = self.df.iloc[i + 1]
                    ep, sp, et = nr['open'], nr['ly_main'], nr['time']
                    if sp < ep:
                        sz = self.calc_size(ep, sp)
                        if sz > 0 and self.capital >= sz * 0.1:
                            self.long_pos = Trade('long', et, ep, sp, sz)
                            self.trades.append(self.long_pos)

            # 做空: 空头趋势(或无过滤) + 祥云空头跌破
            if row['xy_short_break'] == 1 and self.short_pos is None and self.long_pos is None:
                if trend <= 0 and i + 1 < len(self.df):
                    nr = self.df.iloc[i + 1]
                    ep, sp, et = nr['open'], nr['ly_main'], nr['time']
                    if sp > ep:
                        sz = self.calc_size(ep, sp)
                        if sz > 0 and self.capital >= sz * 0.1:
                            self.short_pos = Trade('short', et, ep, sp, sz)
                            self.trades.append(self.short_pos)

            eq = self.capital
            if self.long_pos and not self.long_pos.closed:
                eq += (cp - self.long_pos.entry_price) / self.long_pos.entry_price * self.long_pos.stake
            if self.short_pos and not self.short_pos.closed:
                eq += (self.short_pos.entry_price - cp) / self.short_pos.entry_price * self.short_pos.stake
            self.equity_curve.append({'time': ct, 'equity': eq, 'price': cp})

        lr = self.df.iloc[-1]
        if self.long_pos and not self.long_pos.closed:
            self.long_pos.close(lr['close'], lr['time'], "end_of_data")
            self.capital += self.long_pos.pnl
            self.total_fees += self.long_pos.entry_fee + self.long_pos.exit_fee
            self.total_slippage += self.long_pos.slippage_cost
            self.long_pos = None
        if self.short_pos and not self.short_pos.closed:
            self.short_pos.close(lr['close'], lr['time'], "end_of_data")
            self.capital += self.short_pos.pnl
            self.total_fees += self.short_pos.entry_fee + self.short_pos.exit_fee
            self.total_slippage += self.short_pos.slippage_cost
            self.short_pos = None

        return self.report(mode)

    def report(self, mode):
        ct = [t for t in self.trades if t.closed]
        lt = [t for t in ct if t.side == 'long']
        st = [t for t in ct if t.side == 'short']
        wt = [t for t in ct if t.pnl > 0]
        tpnl = self.capital - self.initial_capital
        rp = tpnl / self.initial_capital * 100
        wr = len(wt) / len(ct) * 100 if ct else 0
        aw = np.mean([t.pnl for t in wt]) if wt else 0
        al = abs(np.mean([t.pnl for t in ct if t.pnl <= 0])) if (len(ct) - len(wt)) > 0 else 0
        pf = aw / al if al > 0 else 0
        edf = pd.DataFrame(self.equity_curve)
        edf['peak'] = edf['equity'].cummax()
        edf['dd'] = (edf['equity'] - edf['peak']) / edf['peak'] * 100
        md = edf['dd'].min()

        print(f"  交易: {len(ct)} (多{len(lt)}/空{len(st)}) | 胜率: {wr:.2f}% | 盈亏比: {pf:.2f} | 收益: {rp:.2f}% | 回撤: {md:.2f}%")
        print(f"  手续费: ${self.total_fees:,.2f} | 滑点: ${self.total_slippage:,.2f}")

        recs = [{'side':t.side,'entry_time':t.entry_time,'entry_price':t.entry_price,'stop_price':t.stop_price,
                 'stake':t.stake,'exit_time':t.exit_time,'exit_price':t.exit_price,'pnl':t.pnl,
                 'entry_fee':t.entry_fee,'exit_fee':t.exit_fee,'slippage_cost':t.slippage_cost,'exit_reason':t.exit_reason} for t in ct]

        return {
            'total_trades': len(ct), 'win_rate': wr, 'profit_factor': pf,
            'return_pct': rp, 'max_drawdown': md, 'total_fees': self.total_fees,
            'total_slippage': self.total_slippage, 'long_trades': len(lt), 'short_trades': len(st),
        }, pd.DataFrame(recs), edf


if __name__ == "__main__":
    print("="*80)
    print("多周期共振回测 - 8H趋势过滤 + 2H下单")
    print("="*80)

    df = load_and_prepare_data(DATA_8H, DATA_2H)

    configs = [
        ('multi_8h2h_fixed', '8H趋势+2H下单(固定$20K)', 'fixed', 20000, 0),
        ('multi_8h2h_pct', '8H趋势+2H下单(2%权益)', 'percentage', 0, 0.02),
        ('baseline_2h_fixed', '纯2H对照(固定$20K)', 'fixed', 20000, 0),
        ('baseline_2h_pct', '纯2H对照(2%权益)', 'percentage', 0, 0.02),
    ]

    results = {}
    for cid, name, rm, ra, rpct in configs:
        bt = MultiTFBacktest(df, INITIAL_CAPITAL, rm, ra, rpct)
        use_trend = 'multi' in cid
        stats, tdf, edf = bt.run(use_trend=use_trend)
        tdf.to_csv(os.path.join(OUTPUT_DIR, f"{cid}_trades.csv"), index=False)
        edf.to_csv(os.path.join(OUTPUT_DIR, f"{cid}_equity.csv"), index=False)
        results[cid] = (stats, name)

    print("\n" + "="*120)
    print("多周期共振 vs 纯下单周期 对比汇总")
    print("="*120)
    print(f"{'策略':<30} | {'交易':>6} | {'多':>5} | {'空':>5} | {'胜率':>7} | {'盈亏比':>7} | {'收益率':>10} | {'回撤':>10}")
    print("-"*120)
    for cid, (s, name) in results.items():
        print(f"{name:<30} | {s['total_trades']:>6} | {s['long_trades']:>5} | {s['short_trades']:>5} | "
              f"{s['win_rate']:>6.2f}% | {s['profit_factor']:>7.2f} | {s['return_pct']:>9.2f}% | {s['max_drawdown']:>9.2f}%")
