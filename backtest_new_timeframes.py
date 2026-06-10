#!/usr/bin/env python3
"""新增时间周期回测: 6H (360min), 8H (480min), 12H (720min)"""
import pandas as pd, numpy as np, os, sys
sys.path.insert(0, '/home/parallels')

INITIAL_CAPITAL = 1_000_000
OUTPUT_DIR = "/home/parallels/wwwroot/jindouyunLH/backtest_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 新增的三个时间周期
datasets = {
    '6h': "/home/parallels/wwwroot/jindouyunLH/TV 数据/BYBIT_BTCUSDT.P, 360_746a8.csv",
    '8h': "/home/parallels/wwwroot/jindouyunLH/TV 数据/BYBIT_BTCUSDT.P, 480_76a54.csv",
    '12h': "/home/parallels/wwwroot/jindouyunLH/TV 数据/BYBIT_BTCUSDT.P, 720_fbcb7.csv",
}

class Trade:
    def __init__(s, side, et, ep, sp, stake, fr, sr):
        s.side,s.entry_time,s.entry_price,s.stop_price,s.stake = side,et,ep,sp,stake
        s.exit_time,s.exit_price,s.pnl,s.closed = None,None,0,False
        s.entry_fee,s.exit_fee,s.slippage_cost = 0,0,0
        s.fee_rate,s.slippage_rate = fr,sr
    def check_stop(s, cp, ct):
        if s.closed: return False
        if s.side=='long' and cp<=s.stop_price: s.close(cp,ct,"stop_loss"); return True
        if s.side=='short' and cp>=s.stop_price: s.close(cp,ct,"stop_loss"); return True
        return False
    def update_stop(s, nsp):
        if s.side=='long' and nsp>s.stop_price: s.stop_price=nsp
        if s.side=='short' and nsp<s.stop_price: s.stop_price=nsp
    def apply_slippage(s, p): return p*(1+s.slippage_rate) if s.side=='long' else p*(1-s.slippage_rate)
    def close(s, price, time, reason=""):
        if s.closed: return
        s.exit_time, s.exit_price, s.closed = time, s.apply_slippage(price), True
        s.entry_fee = s.stake * s.fee_rate; s.exit_fee = s.stake * s.fee_rate
        slip = s.stake * ((s.entry_price*s.slippage_rate+s.exit_price*s.slippage_rate)/s.entry_price)
        s.slippage_cost = slip
        pc = (s.exit_price-s.entry_price)/s.entry_price if s.side=='long' else (s.entry_price-s.exit_price)/s.entry_price
        s.pnl = s.stake*pc - (s.entry_fee+s.exit_fee) - slip; s.exit_reason = reason

class Backtest:
    def __init__(s, df, ic, rm, ra, rp, fr, sr):
        s.df,s.capital,s.initial_capital = df,ic,ic
        s.risk_mode,s.risk_amount,s.risk_pct = rm,ra,rp
        s.fee_rate,s.slippage_rate = fr,sr
        s.trades,s.long_pos,s.short_pos,s.equity_curve = [],None,None,[]
        s.total_fees,s.total_slippage = 0,0
    def calc_size(s, ep, sp):
        r = abs(ep-sp)/ep
        if r==0 or r>0.5: return 0
        if s.risk_mode=='fixed': return s.risk_amount / r
        return (s.capital * s.risk_pct) / r
    def run(s):
        for i in range(1, len(s.df)):
            row, cp, ct = s.df.iloc[i], s.df.iloc[i]['close'], s.df.iloc[i]['time']
            ly = row['ly_main']
            if s.long_pos and not s.long_pos.closed: s.long_pos.update_stop(ly)
            if s.short_pos and not s.short_pos.closed: s.short_pos.update_stop(ly)
            if s.long_pos:
                s.long_pos.check_stop(cp, ct)
                if s.long_pos.closed and s.long_pos.exit_time==ct:
                    s.capital+=s.long_pos.pnl; s.total_fees+=s.long_pos.entry_fee+s.long_pos.exit_fee
                    s.total_slippage+=s.long_pos.slippage_cost; s.long_pos=None
            if s.short_pos:
                s.short_pos.check_stop(cp, ct)
                if s.short_pos.closed and s.short_pos.exit_time==ct:
                    s.capital+=s.short_pos.pnl; s.total_fees+=s.short_pos.entry_fee+s.short_pos.exit_fee
                    s.total_slippage+=s.short_pos.slippage_cost; s.short_pos=None
            if row['xy_long_break']==1 and s.long_pos is None and s.short_pos is None:
                if i+1<len(s.df):
                    nr=s.df.iloc[i+1]; ep=nr['open']; sp=nr['ly_main']; et=nr['time']
                    if sp<ep:
                        sz=s.calc_size(ep,sp)
                        if sz>0 and s.capital>=sz*0.1:
                            s.long_pos=Trade('long',et,ep,sp,sz,s.fee_rate,s.slippage_rate); s.trades.append(s.long_pos)
            if row['xy_short_break']==1 and s.short_pos is None and s.long_pos is None:
                if i+1<len(s.df):
                    nr=s.df.iloc[i+1]; ep=nr['open']; sp=nr['ly_main']; et=nr['time']
                    if sp>ep:
                        sz=s.calc_size(ep,sp)
                        if sz>0 and s.capital>=sz*0.1:
                            s.short_pos=Trade('short',et,ep,sp,sz,s.fee_rate,s.slippage_rate); s.trades.append(s.short_pos)
            eq=s.capital
            if s.long_pos and not s.long_pos.closed: eq+=(cp-s.long_pos.entry_price)/s.long_pos.entry_price*s.long_pos.stake
            if s.short_pos and not s.short_pos.closed: eq+=(s.short_pos.entry_price-cp)/s.short_pos.entry_price*s.short_pos.stake
            s.equity_curve.append({'time':ct,'equity':eq,'price':cp})
        lr=s.df.iloc[-1]
        if s.long_pos and not s.long_pos.closed:
            s.long_pos.close(lr['close'],lr['time'],"end_of_data"); s.capital+=s.long_pos.pnl
            s.total_fees+=s.long_pos.entry_fee+s.long_pos.exit_fee; s.total_slippage+=s.long_pos.slippage_cost; s.long_pos=None
        if s.short_pos and not s.short_pos.closed:
            s.short_pos.close(lr['close'],lr['time'],"end_of_data"); s.capital+=s.short_pos.pnl
            s.total_fees+=s.short_pos.entry_fee+s.short_pos.exit_fee; s.total_slippage+=s.short_pos.slippage_cost; s.short_pos=None
        return s.report()
    def report(s):
        ct=[t for t in s.trades if t.closed]
        recs=[{'side':t.side,'entry_time':t.entry_time,'entry_price':t.entry_price,'stop_price':t.stop_price,
               'stake':t.stake,'exit_time':t.exit_time,'exit_price':t.exit_price,'pnl':t.pnl,
               'entry_fee':t.entry_fee,'exit_fee':t.exit_fee,'slippage_cost':t.slippage_cost,'exit_reason':t.exit_reason} for t in ct]
        tdf=pd.DataFrame(recs); edf=pd.DataFrame(s.equity_curve)
        tpnl=s.capital-s.initial_capital; rp=tpnl/s.initial_capital*100
        wt=len([t for t in ct if t.pnl>0]); wr=wt/len(ct)*100 if ct else 0
        aw=np.mean([t.pnl for t in ct if t.pnl>0]) if wt>0 else 0
        al=abs(np.mean([t.pnl for t in ct if t.pnl<=0])) if (len(ct)-wt)>0 else 0
        pf=aw/al if al>0 else 0
        edf['peak']=edf['equity'].cummax(); edf['dd']=(edf['equity']-edf['peak'])/edf['peak']*100
        md=edf['dd'].min()
        return {'total_trades':len(ct),'win_rate':wr,'profit_factor':pf,'return_pct':rp,'max_drawdown':md},tdf,edf

def prepare_data(csv_file):
    df = pd.read_csv(csv_file)
    df['time'] = pd.to_datetime(df['time'])
    try: df['time'] = df['time'].dt.tz_localize('Asia/Shanghai')
    except TypeError: df['time'] = df['time'].dt.tz_convert('Asia/Shanghai')
    df['xy_main'] = df.get('祥云•主轨', df.get('变盘线'))
    df['xy_long_break'] = df['祥云•多头涨破⬆']
    df['xy_short_break'] = df['祥云•空头跌破⬇']
    df['ly_main'] = df['灵云•主轨']
    return df

# 运行回测
results_fixed = {}
results_pct = {}

for tf_name, csv_file in datasets.items():
    print(f"\n{'='*80}")
    print(f"周期: {tf_name.upper()}")
    print(f"{'='*80}")
    
    df = prepare_data(csv_file)
    print(f"K线: {len(df)} | 范围: {df['time'].iloc[0]} 至 {df['time'].iloc[-1]}")
    
    # 固定风险 $20,000
    print(f"\n  → 固定风险 $20,000...")
    bt = Backtest(df, INITIAL_CAPITAL, 'fixed', 20000, 0, 0.0005, 0.0005)
    stats, tdf, edf = bt.run()
    tf = os.path.join(OUTPUT_DIR, f"config_20000_{tf_name}_trades.csv")
    ef = os.path.join(OUTPUT_DIR, f"config_20000_{tf_name}_equity.csv")
    tdf.to_csv(tf, index=False); edf.to_csv(ef, index=False)
    print(f"    交易: {stats['total_trades']} | 胜率: {stats['win_rate']:.2f}% | 盈亏比: {stats['profit_factor']:.2f} | 收益: {stats['return_pct']:.2f}% | 回撤: {stats['max_drawdown']:.2f}%")
    results_fixed[tf_name] = stats
    
    # 2% 权益风险
    print(f"\n  → 2% 权益风险...")
    bt = Backtest(df, INITIAL_CAPITAL, 'percentage', 0, 0.02, 0.0005, 0.0005)
    stats, tdf, edf = bt.run()
    tf = os.path.join(OUTPUT_DIR, f"config_2pct_{tf_name}_trades.csv")
    ef = os.path.join(OUTPUT_DIR, f"config_2pct_{tf_name}_equity.csv")
    tdf.to_csv(tf, index=False); edf.to_csv(ef, index=False)
    print(f"    交易: {stats['total_trades']} | 胜率: {stats['win_rate']:.2f}% | 盈亏比: {stats['profit_factor']:.2f} | 收益: {stats['return_pct']:.2f}% | 回撤: {stats['max_drawdown']:.2f}%")
    results_pct[tf_name] = stats

# 汇总
print("\n" + "="*100)
print("新增周期回测汇总")
print("="*100)
print(f"\n{'周期':>5} | {'策略':<20} | {'交易':>6} | {'胜率':>7} | {'盈亏比':>7} | {'收益率':>10} | {'回撤':>10}")
print("-"*100)
for tf_name in ['6h', '8h', '12h']:
    if tf_name in results_fixed:
        s = results_fixed[tf_name]
        print(f"{tf_name:>5} | {'固定风险 $20,000':<20} | {s['total_trades']:>6} | {s['win_rate']:>6.2f}% | {s['profit_factor']:>7.2f} | {s['return_pct']:>9.2f}% | {s['max_drawdown']:>9.2f}%")
    if tf_name in results_pct:
        s = results_pct[tf_name]
        print(f"{tf_name:>5} | {'2% 权益风险':<20} | {s['total_trades']:>6} | {s['win_rate']:>6.2f}% | {s['profit_factor']:>7.2f} | {s['return_pct']:>9.2f}% | {s['max_drawdown']:>9.2f}%")
