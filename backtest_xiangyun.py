#!/usr/bin/env python3
"""
祥云突破策略回测 - 含手续费和滑点

策略逻辑：
做多：
  - 入场：祥云多头涨破信号 == 1
  - 止损：灵云主轨（动态）
  
做空：
  - 入场：祥云空头跌破信号 == 1
  - 止损：灵云主轨（动态）

资金管理：
  - 初始资金：1,000,000
  - 每单风险：总资金的 5%（以损定量）
  
交易成本：
  - 手续费：万分之五（0.0005），开仓+平仓各一次
  - 滑点：万分之五（0.0005）
"""

import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================
# 配置参数
# ==========================================
CSV_FILE = "/home/parallels/wwwroot/jindouyunLH/TV 数据/BYBIT_BTCUSDT.P, 240_1bd03.csv"
INITIAL_CAPITAL = 1_000_000  # 初始资金
RISK_PER_TRADE = 20000       # 每单固定风险金：20,000
FEE_RATE = 0.0005            # 手续费：万分之五
SLIPPAGE_RATE = 0.0005       # 滑点：万分之五

# ==========================================
# 加载数据
# ==========================================
df = pd.read_csv(CSV_FILE)
df['time'] = pd.to_datetime(df['time'])

# 重命名字段方便使用
df['xy_main'] = df['祥云•主轨']      # 祥云主轨
df['xy_sub'] = df['祥云•副轨']       # 祥云副轨
df['xy_long_break'] = df['祥云•多头涨破⬆']
df['xy_short_break'] = df['祥云•空头跌破⬇']
df['ly_main'] = df['灵云•主轨']      # 灵云主轨
df['ly_sub'] = df['灵云•副轨']       # 灵云副轨
df['ly_long_break'] = df['灵云•多头涨破⬆']
df['ly_short_break'] = df['灵云•空头跌破⬇']

# ==========================================
# 回测引擎
# ==========================================
class Trade:
    def __init__(self, side, entry_time, entry_price, stop_price, stake):
        self.side = side  # 'long' or 'short'
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.stake = stake  # 仓位大小（USDT）
        self.exit_time = None
        self.exit_price = None
        self.pnl = 0
        self.closed = False
        self.entry_fee = 0
        self.exit_fee = 0
        self.slippage_cost = 0
        
    def check_stop(self, current_price, current_time):
        """检查是否触发止损"""
        if self.closed:
            return False
            
        if self.side == 'long':
            # 做多：价格跌破止损线
            if current_price <= self.stop_price:
                self.close(current_price, current_time, "stop_loss")
                return True
        else:
            # 做空：价格涨突破损线
            if current_price >= self.stop_price:
                self.close(current_price, current_time, "stop_loss")
                return True
        return False
    
    def update_stop(self, new_stop_price):
        """更新动态止损（只向有利方向移动）"""
        if self.side == 'long':
            # 做多：止损只上移
            if new_stop_price > self.stop_price:
                self.stop_price = new_stop_price
        else:
            # 做空：止损只下移
            if new_stop_price < self.stop_price:
                self.stop_price = new_stop_price
    
    def apply_slippage(self, price):
        """应用滑点"""
        if self.side == 'long':
            # 做多：买入价更高，卖出价更低
            return price * (1 + SLIPPAGE_RATE)
        else:
            # 做空：卖出价更低，买入价更高
            return price * (1 - SLIPPAGE_RATE)
    
    def calculate_fees(self, entry_price, exit_price):
        """计算手续费（开仓+平仓）"""
        self.entry_fee = self.stake * FEE_RATE
        self.exit_fee = self.stake * FEE_RATE
        total_fee = self.entry_fee + self.exit_fee
        return total_fee
    
    def close(self, price, time, reason=""):
        if self.closed:
            return
            
        self.exit_time = time
        
        # 应用滑点到出场价
        self.exit_price = self.apply_slippage(price)
        self.closed = True
        
        # 计算手续费
        total_fee = self.calculate_fees(self.entry_price, self.exit_price)
        
        # 计算滑点成本
        if self.side == 'long':
            slippage_diff = self.entry_price * SLIPPAGE_RATE + self.exit_price * SLIPPAGE_RATE
        else:
            slippage_diff = self.entry_price * SLIPPAGE_RATE + self.exit_price * SLIPPAGE_RATE
        self.slippage_cost = self.stake * (slippage_diff / self.entry_price)
        
        # 计算盈亏
        if self.side == 'long':
            price_change = (self.exit_price - self.entry_price) / self.entry_price
        else:
            price_change = (self.entry_price - self.exit_price) / self.entry_price
            
        # 净盈亏 = 毛利 - 手续费 - 滑点成本
        gross_pnl = self.stake * price_change
        self.pnl = gross_pnl - total_fee - self.slippage_cost
        self.exit_reason = reason


class Backtest:
    def __init__(self, df, initial_capital, risk_amount):
        self.df = df
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.risk_amount = risk_amount  # 每单固定风险金
        self.trades = []
        self.long_position = None
        self.short_position = None
        self.equity_curve = []
        self.total_fees = 0
        self.total_slippage = 0
        
    def calculate_position_size(self, entry_price, stop_price):
        """以损定量：仓位 = 固定风险金 / 止损距离比例"""
        stop_distance_ratio = abs(entry_price - stop_price) / entry_price
        if stop_distance_ratio == 0 or stop_distance_ratio > 0.5:  # 止损距离过大则跳过
            return 0
        position_size = self.risk_amount / stop_distance_ratio
        return position_size
    
    def run(self):
        print("=" * 80)
        print("祥云突破策略回测（含手续费和滑点）")
        print("=" * 80)
        print(f"初始资金: ${self.initial_capital:,.0f}")
        print(f"每单固定风险: ${self.risk_amount:,.0f}")
        print(f"手续费: {FEE_RATE*10000:.1f}/万（开仓+平仓）")
        print(f"滑点: {SLIPPAGE_RATE*10000:.1f}/万")
        print(f"数据范围: {self.df['time'].iloc[0]} 至 {self.df['time'].iloc[-1]}")
        print(f"K 线数量: {len(self.df)}")
        print("=" * 80)
        print()
        
        for i in range(1, len(self.df)):
            row = self.df.iloc[i]
            current_price = row['close']
            current_time = row['time']
            
            # 更新动态止损
            ly_main = row['ly_main']
            
            if self.long_position and not self.long_position.closed:
                self.long_position.update_stop(ly_main)
                
            if self.short_position and not self.short_position.closed:
                self.short_position.update_stop(ly_main)
            
            # 检查止损
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
            
            # 入场信号 - 信号确认后换 K 入场
            # 做多：祥云多头涨破
            if row['xy_long_break'] == 1 and self.long_position is None and self.short_position is None:
                if i + 1 < len(self.df):
                    next_row = self.df.iloc[i + 1]
                    entry_price = next_row['open']  # 下一根 K 线开盘价
                    entry_time = next_row['time']
                    stop_price = next_row['ly_main']
                    
                    if stop_price < entry_price:  # 止损必须在入场价下方
                        position_size = self.calculate_position_size(entry_price, stop_price)
                        if position_size > 0 and self.capital >= position_size * 0.1:  # 确保有足够资金
                            self.long_position = Trade(
                                'long', entry_time, entry_price, stop_price, position_size
                            )
                            self.trades.append(self.long_position)
            
            # 做空：祥云空头跌破
            if row['xy_short_break'] == 1 and self.short_position is None and self.long_position is None:
                if i + 1 < len(self.df):
                    next_row = self.df.iloc[i + 1]
                    entry_price = next_row['open']  # 下一根 K 线开盘价
                    entry_time = next_row['time']
                    stop_price = next_row['ly_main']
                    
                    if stop_price > entry_price:  # 止损必须在入场价上方
                        position_size = self.calculate_position_size(entry_price, stop_price)
                        if position_size > 0 and self.capital >= position_size * 0.1:
                            self.short_position = Trade(
                                'short', entry_time, entry_price, stop_price, position_size
                            )
                            self.trades.append(self.short_position)
            
            # 记录权益曲线
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
        
        # 强制平仓未结束的持仓
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
        """生成回测报告"""
        closed_trades = [t for t in self.trades if t.closed]
        long_trades = [t for t in closed_trades if t.side == 'long']
        short_trades = [t for t in closed_trades if t.side == 'short']
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl <= 0]
        
        total_pnl = self.capital - self.initial_capital
        return_pct = (total_pnl / self.initial_capital) * 100
        
        # 计算最大回撤
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        # 计算胜率
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        # 计算盈亏比
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = abs(np.mean([t.pnl for t in losing_trades])) if losing_trades else 0
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        
        print("=" * 80)
        print("回测结果报告")
        print("=" * 80)
        
        print("\n📊 资金情况")
        print(f"  初始资金:      ${self.initial_capital:>12,.2f}")
        print(f"  最终资金:      ${self.capital:>12,.2f}")
        print(f"  总盈亏:        ${total_pnl:>12,.2f}")
        print(f"  收益率:        {return_pct:>11.2f}%")
        
        print("\n💸 交易成本")
        print(f"  总手续费:      ${self.total_fees:>12,.2f}")
        print(f"  总滑点成本:    ${self.total_slippage:>12,.2f}")
        print(f"  总成本:        ${self.total_fees + self.total_slippage:>12,.2f}")
        print(f"  成本占本金:    {(self.total_fees + self.total_slippage) / self.initial_capital * 100:>10.4f}%")
        
        print("\n📈 交易统计")
        print(f"  总交易次数:    {len(closed_trades):>12}")
        print(f"    做多:        {len(long_trades):>12}")
        print(f"    做空:        {len(short_trades):>12}")
        print(f"  盈利次数:      {len(winning_trades):>12}")
        print(f"  亏损次数:      {len(losing_trades):>12}")
        print(f"  胜率:          {win_rate:>11.2f}%")
        
        print("\n💰 盈亏分析")
        print(f"  平均盈利:      ${avg_win:>12,.2f}")
        print(f"  平均亏损:      ${avg_loss:>12,.2f}")
        print(f"  盈亏比:        {profit_factor:>11.2f}")
        print(f"  最大回撤:      {max_drawdown:>11.2f}%")
        
        # 做多做空分别统计
        if long_trades:
            long_wins = [t for t in long_trades if t.pnl > 0]
            long_wr = len(long_wins) / len(long_trades) * 100
            long_pnl = sum(t.pnl for t in long_trades)
            print(f"\n  做多明细:")
            print(f"    交易次数:    {len(long_trades):>12}")
            print(f"    胜率:        {long_wr:>11.2f}%")
            print(f"    总盈亏:      ${long_pnl:>12,.2f}")
            
        if short_trades:
            short_wins = [t for t in short_trades if t.pnl > 0]
            short_wr = len(short_wins) / len(short_trades) * 100
            short_pnl = sum(t.pnl for t in short_trades)
            print(f"\n  做空明细:")
            print(f"    交易次数:    {len(short_trades):>12}")
            print(f"    胜率:        {short_wr:>11.2f}%")
            print(f"    总盈亏:      ${short_pnl:>12,.2f}")
        
        # 显示前 20 笔交易
        print(f"\n📋 交易明细（前 20 笔）")
        print(f"{'序号':>4} {'方向':>4} {'入场时间':>22} {'入场价':>10} {'止损价':>10} {'出场时间':>22} {'出场价':>10} {'净盈亏':>12} {'手续费':>10} {'原因':>10}")
        print("-" * 145)
        
        for idx, trade in enumerate(closed_trades[:20]):
            direction = "多" if trade.side == 'long' else "空"
            total_fee = trade.entry_fee + trade.exit_fee
            print(f"{idx+1:>4} {direction:>4} {str(trade.entry_time):>22} {trade.entry_price:>10,.1f} {trade.stop_price:>10,.1f} "
                  f"{str(trade.exit_time):>22} {trade.exit_price:>10,.1f} ${trade.pnl:>11,.2f} ${total_fee:>9,.2f} {trade.exit_reason:>10}")
        
        # 保存交易记录
        trade_records = []
        for t in closed_trades:
            trade_records.append({
                'side': t.side,
                'entry_time': t.entry_time,
                'entry_price': t.entry_price,
                'stop_price': t.stop_price,
                'exit_time': t.exit_time,
                'exit_price': t.exit_price,
                'pnl': t.pnl,
                'entry_fee': t.entry_fee,
                'exit_fee': t.exit_fee,
                'slippage_cost': t.slippage_cost,
                'exit_reason': t.exit_reason
            })
        
        trade_df = pd.DataFrame(trade_records)
        trade_file = "/home/parallels/backtest_trades_with_costs.csv"
        trade_df.to_csv(trade_file, index=False)
        print(f"\n💾 完整交易记录已保存至: {trade_file}")
        
        # 保存权益曲线
        equity_df.to_csv("/home/parallels/backtest_equity_with_costs.csv", index=False)
        print(f"💾 权益曲线已保存至: /home/parallels/backtest_equity_with_costs.csv")
        
        print("\n" + "=" * 80)
        
        return {
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'total_trades': len(closed_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'total_fees': self.total_fees,
            'total_slippage': self.total_slippage
        }


# ==========================================
# 运行回测
# ==========================================
if __name__ == "__main__":
    bt = Backtest(df, INITIAL_CAPITAL, RISK_PER_TRADE)
    result = bt.run()
