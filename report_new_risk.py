#!/usr/bin/env python3
"""
汇总 50K固定风险 和 5%权益风险 的回测结果
"""

import pandas as pd
import os

RESULTS_DIR = "/home/parallels/wwwroot/jindouyunLH/backtest_results"
INITIAL_CAPITAL = 1_000_000

# 39个组合
COMBOS = [
    ('6h', '3h', 'xy', 'ly'), ('8h', '3h', 'xy', 'ly'), ('6h', '3h', 'xy', 'xy'), ('8h', '3h', 'xy', 'xy'),
    ('1d', '8h', 'xy', 'xy'), ('3h', '1h', 'xy', 'ly'), ('12h', '6h', 'ly', 'ly'), ('4h', '2h', 'xy', 'ly'),
    ('1d', '6h', 'ly', 'ly'), ('1d', '8h', 'xy', 'ly'), ('8h', '4h', 'xy', 'ly'), ('8h', '4h', 'xy', 'xy'),
    ('4h', '2h', 'ly', 'ly'), ('12h', '4h', 'xy', 'xy'), ('1d', '6h', 'xy', 'ly'), ('12h', '6h', 'xy', 'ly'),
    ('12h', '6h', 'ly', 'xy'), ('12h', '4h', 'xy', 'ly'), ('4h', '2h', 'ly', 'xy'), ('6h', '2h', 'xy', 'ly'),
    ('1d', '8h', 'ly', 'xy'), ('6h', '2h', 'ly', 'xy'), ('8h', '4h', 'ly', 'xy'), ('12h', '4h', 'ly', 'xy'),
    ('4h', '2h', 'xy', 'xy'), ('6h', '2h', 'xy', 'xy'), ('1d', '6h', 'xy', 'xy'), ('8h', '3h', 'ly', 'xy'),
    ('6h', '3h', 'ly', 'xy'), ('3h', '1h', 'xy', 'xy'), ('12h', '6h', 'xy', 'xy'), ('6h', '2h', 'ly', 'ly'),
    ('1d', '8h', 'ly', 'ly'), ('12h', '4h', 'ly', 'ly'), ('3h', '1h', 'ly', 'xy'), ('8h', '3h', 'ly', 'ly'),
    ('6h', '3h', 'ly', 'ly'), ('3h', '1h', 'ly', 'ly'),
]

def load_stats(prefix):
    trades_file = os.path.join(RESULTS_DIR, f"{prefix}_trades.csv")
    equity_file = os.path.join(RESULTS_DIR, f"{prefix}_equity.csv")
    if not os.path.exists(trades_file) or not os.path.exists(equity_file):
        return None
    
    df = pd.read_csv(trades_file)
    eq_df = pd.read_csv(equity_file)
    
    total_trades = len(df)
    win_trades = len(df[df['pnl'] > 0])
    win_rate = win_trades / total_trades * 100 if total_trades > 0 else 0
    
    long_trades = df[df['side'] == 'long']
    short_trades = df[df['side'] == 'short']
    long_wr = len(long_trades[long_trades['pnl'] > 0]) / len(long_trades) * 100 if len(long_trades) > 0 else 0
    short_wr = len(short_trades[short_trades['pnl'] > 0]) / len(short_trades) * 100 if len(short_trades) > 0 else 0
    
    avg_win = df[df['pnl'] > 0]['pnl'].mean() if win_trades > 0 else 0
    avg_loss = abs(df[df['pnl'] <= 0]['pnl'].mean()) if (total_trades - win_trades) > 0 else 0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
    
    total_pnl = df['pnl'].sum()
    return_pct = total_pnl / INITIAL_CAPITAL * 100
    
    eq_df['peak'] = eq_df['equity'].cummax()
    eq_df['dd'] = (eq_df['equity'] - eq_df['peak']) / eq_df['peak'] * 100
    max_drawdown = eq_df['dd'].min()
    
    return {
        'total_trades': total_trades, 'win_rate': win_rate, 'profit_factor': profit_factor,
        'return_pct': return_pct, 'max_drawdown': max_drawdown,
        'long_trades': len(long_trades), 'short_trades': len(short_trades),
        'long_wr': long_wr, 'short_wr': short_wr,
    }


for risk_suffix, risk_label in [('50k', '50K固定风险'), ('p5pct', '5%权益风险')]:
    print("\n" + "=" * 140)
    print(f"多周期共振回测结果 - {risk_label}")
    print("=" * 140)
    print(f"{'组合':<12} | {'信号止损':<12} | {'交易':>5} | {'多':>4} | {'空':>4} | {'胜率':>7} | {'长胜':>6} | {'空胜':>6} | {'盈亏比':>7} | {'收益率':>9} | {'回撤':>9}")
    print("-" * 140)
    
    results = []
    for t, e, s, st in COMBOS:
        prefix = f"ss_{t}_{e}_{s}_{st}_{risk_suffix}"
        stats = load_stats(prefix)
        if stats:
            sig_label = ('祥' if s=='xy' else '灵') + ('祥' if st=='xy' else '灵')
            results.append({
                'combo': f"{t.upper()}+{e.upper()}",
                'sig': sig_label,
                't': t, 'e': e, 's': s, 'st': st,
                **stats
            })
    
    # 按收益率排序
    results_sorted = sorted(results, key=lambda x: x['return_pct'], reverse=True)
    
    for r in results_sorted:
        print(f"{r['combo']:<12} | {r['sig']:<12} | {r['total_trades']:>5} | {r['long_trades']:>4} | {r['short_trades']:>4} | "
              f"{r['win_rate']:>6.1f}% | {r['long_wr']:>5.1f}% | {r['short_wr']:>5.1f}% | {r['profit_factor']:>7.2f} | "
              f"{r['return_pct']:>8.1f}% | {r['max_drawdown']:>8.1f}%")
    
    # Top 10 收益率
    print("\n" + "=" * 100)
    print(f"收益率 Top 10 - {risk_label}")
    print("=" * 100)
    for i, r in enumerate(results_sorted[:10], 1):
        print(f"{i:2d}. {r['combo']} ({r['sig']}) - 收益率:{r['return_pct']:.1f}%, 胜率:{r['win_rate']:.1f}%, 盈亏比:{r['profit_factor']:.2f}, 回撤:{r['max_drawdown']:.1f}%")
    
    # Top 10 风险调整收益 (收益率/回撤绝对值)
    print("\n" + "=" * 100)
    print(f"风险调整收益 Top 10 (收益率/回撤) - {risk_label}")
    print("=" * 100)
    results_by_calmar = sorted(results, key=lambda x: x['return_pct'] / abs(x['max_drawdown']) if x['max_drawdown'] != 0 else 0, reverse=True)
    for i, r in enumerate(results_by_calmar[:10], 1):
        calmar = r['return_pct'] / abs(r['max_drawdown']) if r['max_drawdown'] != 0 else 0
        print(f"{i:2d}. {r['combo']} ({r['sig']}) - Calmar:{calmar:.2f}, 收益率:{r['return_pct']:.1f}%, 回撤:{r['max_drawdown']:.1f}%, 胜率:{r['win_rate']:.1f}%")
