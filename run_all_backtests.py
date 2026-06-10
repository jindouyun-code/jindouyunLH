#!/usr/bin/env python3
"""
批量运行所有回测配置，生成独立的数据文件
"""

import pandas as pd
import numpy as np
import os
import sys

# 导入配置
sys.path.insert(0, '/home/parallels/wwwroot/jindouyunLH')
from backtest_configs import BACKTEST_CONFIGS

CSV_FILE = "/home/parallels/wwwroot/jindouyunLH/TV 数据/BYBIT_BTCUSDT.P, 240_1bd03.csv"
INITIAL_CAPITAL = 1_000_000

# 创建输出目录
OUTPUT_DIR = "/home/parallels/wwwroot/jindouyunLH/backtest_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载数据
df = pd.read_csv(CSV_FILE)
df['time'] = pd.to_datetime(df['time'])
df['xy_main'] = df['祥云•主轨']
df['xy_sub'] = df['祥云•副轨']
df['xy_long_break'] = df['祥云•多头涨破⬆']
df['xy_short_break'] = df['祥云•空头跌破⬇']
df['ly_main'] = df['灵云•主轨']
df['ly_sub'] = df['灵云•副轨']
df['ly_long_break'] = df['灵云•多头涨破⬆']
df['ly_short_break'] = df['灵云•空头跌破⬇']


class Trade:
    def __init__(self, side, entry_time, entry_price, stop_price, stake, fee_rate, slippage_rate):
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
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        
    def check_stop(self, current_price, current_time):
        if self.closed:
            return False
        if self.side == 'long':
            if current_price <= self.stop_price:
                self.close(current_price, current_time, "stop_loss")
                return True
        else:
            if current_price >= self.stop_price:
                self.close(current_price, current_time, "stop_loss")
                return True
        return False
    
    def update_stop(self, new_stop_price):
        if self.side == 'long':
            if new_stop_price > self.stop_price:
                self.stop_price = new_stop_price
        else:
            if new_stop_price < self.stop_price:
                self.stop_price = new_stop_price
    
    def apply_slippage(self, price):
        if self.side == 'long':
            return price * (1 + self.slippage_rate)
        else:
            return price * (1 - self.slippage_rate)
    
    def calculate_fees(self, entry_price, exit_price):
        self.entry_fee = self.stake * self.fee_rate
        self.exit_fee = self.stake * self.fee_rate
        return self.entry_fee + self.exit_fee
    
    def close(self, price, time, reason=""):
        if self.closed:
            return
        self.exit_time = time
        self.exit_price = self.apply_slippage(price)
        self.closed = True
        total_fee = self.calculate_fees(self.entry_price, self.exit_price)
        
        if self.side == 'long':
            slippage_diff = self.entry_price * self.slippage_rate + self.exit_price * self.slippage_rate
        else:
            slippage_diff = self.entry_price * self.slippage_rate + self.exit_price * self.slippage_rate
        self.slippage_cost = self.stake * (slippage_diff / self.entry_price)
        
        if self.side == 'long':
            price_change = (self.exit_price - self.entry_price) / self.entry_price
        else:
            price_change = (self.entry_price - self.exit_price) / self.entry_price
            
        gross_pnl = self.stake * price_change
        self.pnl = gross_pnl - total_fee - self.slippage_cost
        self.exit_reason = reason


class Backtest:
    def __init__(self, df, initial_capital, risk_mode='fixed', risk_amount=0, risk_pct=0, 
                 fee_rate=0.0005, slippage_rate=0.0005):
        self.df = df
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.risk_mode = risk_mode
        self.risk_amount = risk_amount
        self.risk_pct = risk_pct
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.trades = []
        self.long_position = None
        self.short_position = None
        self.equity_curve = []
        self.total_fees = 0
        self.total_slippage = 0
        
    def calculate_position_size(self, entry_price, stop_price):
        stop_distance_ratio = abs(entry_price - stop_price) / entry_price
        if stop_distance_ratio == 0 or stop_distance_ratio > 0.5:
            return 0
        if self.risk_mode == 'fixed':
            position_size = self.risk_amount / stop_distance_ratio
        else:  # percentage
            current_risk = self.capital * self.risk_pct
            position_size = current_risk / stop_distance_ratio
        return position_size
    
    def run(self):
        for i in range(1, len(self.df)):
            row = self.df.iloc[i]
            current_price = row['close']
            current_time = row['time']
            
            ly_main = row['ly_main']
            
            if self.long_position and not self.long_position.closed:
                self.long_position.update_stop(ly_main)
            if self.short_position and not self.short_position.closed:
                self.short_position.update_stop(ly_main)
            
            if self.long_position:
                self.long_position.check_stop(current_price, current_time)
                if self.long_position.closed and self.long_position.exit_time == current_time:
                    self.capital += self.long_position.pnl
                    self.total_fees += self.long_position.entry_fee + self.long_position.exit_fee
                    self.total_slippage += self.long_position.slippage_cost
                    self.long_position = None
                    
            if self.short_position:
                self.short_position.check_stop(current_price, current_time)
                if self.short_position.closed and self.short_position.exit_time == current_time:
                    self.capital += self.short_position.pnl
                    self.total_fees += self.short_position.entry_fee + self.short_position.exit_fee
                    self.total_slippage += self.short_position.slippage_cost
                    self.short_position = None
            
            # 入场信号 - 记录信号，下一根 K 线开盘入场
            if row['xy_long_break'] == 1 and self.long_position is None and self.short_position is None:
                # 信号确认，等待下一根 K 线
                if i + 1 < len(self.df):
                    next_row = self.df.iloc[i + 1]
                    entry_price = next_row['open']
                    stop_price = next_row['ly_main']
                    entry_time = next_row['time']
                    if stop_price < entry_price:
                        position_size = self.calculate_position_size(entry_price, stop_price)
                        if position_size > 0 and self.capital >= position_size * 0.1:
                            self.long_position = Trade(
                                'long', entry_time, entry_price, stop_price, position_size,
                                self.fee_rate, self.slippage_rate
                            )
                            self.trades.append(self.long_position)
            
            if row['xy_short_break'] == 1 and self.short_position is None and self.long_position is None:
                # 信号确认，等待下一根 K 线
                if i + 1 < len(self.df):
                    next_row = self.df.iloc[i + 1]
                    entry_price = next_row['open']
                    stop_price = next_row['ly_main']
                    entry_time = next_row['time']
                    if stop_price > entry_price:
                        position_size = self.calculate_position_size(entry_price, stop_price)
                        if position_size > 0 and self.capital >= position_size * 0.1:
                            self.short_position = Trade(
                                'short', entry_time, entry_price, stop_price, position_size,
                                self.fee_rate, self.slippage_rate
                            )
                            self.trades.append(self.short_position)
            
            equity = self.capital
            if self.long_position and not self.long_position.closed:
                pnl = (current_price - self.long_position.entry_price) / self.long_position.entry_price * self.long_position.stake
                equity += pnl
            if self.short_position and not self.short_position.closed:
                pnl = (self.short_position.entry_price - current_price) / self.short_position.entry_price * self.short_position.stake
                equity += pnl
                
            self.equity_curve.append({
                'time': current_time,
                'equity': equity,
                'price': current_price
            })
        
        last_row = self.df.iloc[-1]
        if self.long_position and not self.long_position.closed:
            self.long_position.close(last_row['close'], last_row['time'], "end_of_data")
            self.capital += self.long_position.pnl
            self.total_fees += self.long_position.entry_fee + self.long_position.exit_fee
            self.total_slippage += self.long_position.slippage_cost
            self.long_position = None
            
        if self.short_position and not self.short_position.closed:
            self.short_position.close(last_row['close'], last_row['time'], "end_of_data")
            self.capital += self.short_position.pnl
            self.total_fees += self.short_position.entry_fee + self.short_position.exit_fee
            self.total_slippage += self.short_position.slippage_cost
            self.short_position = None
            
        return self.generate_report()
    
    def generate_report(self):
        closed_trades = [t for t in self.trades if t.closed]
        
        trade_records = []
        for t in closed_trades:
            trade_records.append({
                'side': t.side,
                'entry_time': t.entry_time,
                'entry_price': t.entry_price,
                'stop_price': t.stop_price,
                'stake': t.stake,
                'exit_time': t.exit_time,
                'exit_price': t.exit_price,
                'pnl': t.pnl,
                'entry_fee': t.entry_fee,
                'exit_fee': t.exit_fee,
                'slippage_cost': t.slippage_cost,
                'exit_reason': t.exit_reason
            })
        
        trade_df = pd.DataFrame(trade_records)
        equity_df = pd.DataFrame(self.equity_curve)
        
        total_pnl = self.capital - self.initial_capital
        return_pct = (total_pnl / self.initial_capital) * 100
        win_trades = len([t for t in closed_trades if t.pnl > 0])
        win_rate = (win_trades / len(closed_trades) * 100) if closed_trades else 0
        
        avg_win = np.mean([t.pnl for t in closed_trades if t.pnl > 0]) if win_trades > 0 else 0
        avg_loss = abs(np.mean([t.pnl for t in closed_trades if t.pnl <= 0])) if (len(closed_trades) - win_trades) > 0 else 0
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        return {
            'total_trades': len(closed_trades),
            'win_trades': win_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'final_equity': self.capital,
            'total_fees': self.total_fees,
            'total_slippage': self.total_slippage,
        }, trade_df, equity_df


def run_config(config):
    print(f"\n{'='*80}")
    print(f"运行配置: {config['name']}")
    print(f"描述: {config['description']}")
    print(f"{'='*80}")
    
    bt = Backtest(
        df,
        INITIAL_CAPITAL,
        risk_mode=config['risk_mode'],
        risk_amount=config.get('risk_amount', 0),
        risk_pct=config.get('risk_pct', 0),
        fee_rate=config['fee_rate'],
        slippage_rate=config['slippage_rate']
    )
    
    stats, trades_df, equity_df = bt.run()
    
    # 保存数据
    trades_df.to_csv(config['trades_file'], index=False)
    equity_df.to_csv(config['equity_file'], index=False)
    
    print(f"\n总交易次数: {stats['total_trades']}")
    print(f"胜率: {stats['win_rate']:.2f}%")
    print(f"盈亏比: {stats['profit_factor']:.2f}")
    print(f"收益率: {stats['return_pct']:.2f}%")
    print(f"最大回撤: {stats['max_drawdown']:.2f}%")
    print(f"\n交易记录已保存: {config['trades_file']}")
    print(f"权益曲线已保存: {config['equity_file']}")
    
    return stats


if __name__ == "__main__":
    all_stats = {}
    for config in BACKTEST_CONFIGS:
        stats = run_config(config)
        all_stats[config['id']] = stats
    
    print(f"\n{'='*80}")
    print("所有回测配置运行完成")
    print(f"{'='*80}")
    for config_id, stats in all_stats.items():
        print(f"{config_id}: {stats['total_trades']} trades, {stats['return_pct']:.2f}% return")
