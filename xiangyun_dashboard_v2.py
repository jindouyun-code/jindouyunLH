#!/usr/bin/env python3
"""
祥云量化监控面板 - 中文版 (v2)
支持多周期共振回测 + 信号止损组合展示
"""

from flask import Flask, render_template_string, jsonify, request
import pandas as pd
import numpy as np
import os

APP = Flask(__name__)

RESULTS_DIR = "/home/parallels/wwwroot/jindouyunLH/backtest_results"

# 辅助函数：为38个组合生成配置
def _gen_multi_configs(risk_suffix, risk_label):
    """生成多周期共振配置列表"""
    combos = [
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
    return [
        {"id": f"ss_{t}_{e}_{s}_{st}_{risk_suffix}", 
         "name": f"{t.upper()}+{e.upper()} ({'祥云' if s=='xy' else '灵云'}+{'祥云' if st=='xy' else '灵云'}) {risk_label}", 
         "desc": f"{t.upper()}趋势+{e.upper()}下单", 
         "file_prefix": f"ss_{t}_{e}_{s}_{st}_{risk_suffix}"}
        for t, e, s, st in combos
    ]

# 回测配置分组
CONFIG_GROUPS = [
    {
        "group_name": "多周期共振 (2%权益)",
        "group_key": "multi_pct",
        "configs": [
            {"id": "ss_6h_3h_xy_ly_pct", "name": "6H趋势+3H下单 (祥云+灵云)", "desc": "收益率380%, 回撤-19.2%", "file_prefix": "ss_6h_3h_xy_ly_pct"},
            {"id": "ss_8h_3h_xy_ly_pct", "name": "8H趋势+3H下单 (祥云+灵云)", "desc": "收益率305%, 回撤-22.4%", "file_prefix": "ss_8h_3h_xy_ly_pct"},
            {"id": "ss_6h_3h_xy_xy_pct", "name": "6H趋势+3H下单 (祥云+祥云)", "desc": "收益率273%, 回撤-16.8%", "file_prefix": "ss_6h_3h_xy_xy_pct"},
            {"id": "ss_8h_3h_xy_xy_pct", "name": "8H趋势+3H下单 (祥云+祥云)", "desc": "收益率256%, 回撤-24.2%", "file_prefix": "ss_8h_3h_xy_xy_pct"},
            {"id": "ss_1d_8h_xy_xy_pct", "name": "1D趋势+8H下单 (祥云+祥云)", "desc": "收益率189%, 回撤-16.1%", "file_prefix": "ss_1d_8h_xy_xy_pct"},
            {"id": "ss_3h_1h_xy_ly_pct", "name": "3H趋势+1H下单 (祥云+灵云)", "desc": "收益率188%, 回撤-34.5%", "file_prefix": "ss_3h_1h_xy_ly_pct"},
            {"id": "ss_12h_6h_ly_ly_pct", "name": "12H趋势+6H下单 (灵云+灵云)", "desc": "收益率187%, 回撤-21.9%", "file_prefix": "ss_12h_6h_ly_ly_pct"},
            {"id": "ss_4h_2h_xy_ly_pct", "name": "4H趋势+2H下单 (祥云+灵云)", "desc": "收益率187%, 回撤-41.2%", "file_prefix": "ss_4h_2h_xy_ly_pct"},
            {"id": "ss_1d_6h_ly_ly_pct", "name": "1D趋势+6H下单 (灵云+灵云)", "desc": "收益率184%, 回撤-18.8%", "file_prefix": "ss_1d_6h_ly_ly_pct"},
            {"id": "ss_1d_6h_ly_xy_pct", "name": "1D趋势+6H下单 (灵云+祥云)", "desc": "收益率173%, 回撤-10.6%", "file_prefix": "ss_1d_6h_ly_xy_pct"},
            {"id": "ss_8h_4h_xy_ly_pct", "name": "8H趋势+4H下单 (祥云+灵云)", "desc": "收益率170%, 回撤-22.9%", "file_prefix": "ss_8h_4h_xy_ly_pct"},
            {"id": "ss_8h_4h_xy_xy_pct", "name": "8H趋势+4H下单 (祥云+祥云)", "desc": "收益率161%, 回撤-21.9%", "file_prefix": "ss_8h_4h_xy_xy_pct"},
            {"id": "ss_4h_2h_ly_ly_pct", "name": "4H趋势+2H下单 (灵云+灵云)", "desc": "收益率155%, 回撤-36.5%", "file_prefix": "ss_4h_2h_ly_ly_pct"},
            {"id": "ss_1d_8h_xy_ly_pct", "name": "1D趋势+8H下单 (祥云+灵云)", "desc": "收益率155%, 回撤-15.8%", "file_prefix": "ss_1d_8h_xy_ly_pct"},
            {"id": "ss_12h_4h_xy_xy_pct", "name": "12H趋势+4H下单 (祥云+祥云)", "desc": "收益率144%, 回撤-21.5%", "file_prefix": "ss_12h_4h_xy_xy_pct"},
            {"id": "ss_1d_6h_xy_ly_pct", "name": "1D趋势+6H下单 (祥云+灵云)", "desc": "收益率148%, 回撤-15.2%", "file_prefix": "ss_1d_6h_xy_ly_pct"},
            {"id": "ss_12h_6h_xy_ly_pct", "name": "12H趋势+6H下单 (祥云+灵云)", "desc": "收益率126%, 回撤-15.0%", "file_prefix": "ss_12h_6h_xy_ly_pct"},
            {"id": "ss_12h_6h_ly_xy_pct", "name": "12H趋势+6H下单 (灵云+祥云)", "desc": "收益率126%, 回撤-11.3%", "file_prefix": "ss_12h_6h_ly_xy_pct"},
            {"id": "ss_12h_4h_xy_ly_pct", "name": "12H趋势+4H下单 (祥云+灵云)", "desc": "收益率117%, 回撤-25.3%", "file_prefix": "ss_12h_4h_xy_ly_pct"},
            {"id": "ss_4h_2h_ly_xy_pct", "name": "4H趋势+2H下单 (灵云+祥云)", "desc": "收益率110%, 回撤-23.5%", "file_prefix": "ss_4h_2h_ly_xy_pct"},
            {"id": "ss_6h_2h_xy_ly_pct", "name": "6H趋势+2H下单 (祥云+灵云)", "desc": "收益率111%, 回撤-28.5%", "file_prefix": "ss_6h_2h_xy_ly_pct"},
            {"id": "ss_1d_8h_ly_xy_pct", "name": "1D趋势+8H下单 (灵云+祥云)", "desc": "收益率107%, 回撤-10.9%", "file_prefix": "ss_1d_8h_ly_xy_pct"},
            {"id": "ss_6h_2h_ly_xy_pct", "name": "6H趋势+2H下单 (灵云+祥云)", "desc": "收益率96%, 回撤-22.3%", "file_prefix": "ss_6h_2h_ly_xy_pct"},
            {"id": "ss_8h_4h_ly_xy_pct", "name": "8H趋势+4H下单 (灵云+祥云)", "desc": "收益率98%, 回撤-26.7%", "file_prefix": "ss_8h_4h_ly_xy_pct"},
            {"id": "ss_12h_4h_ly_xy_pct", "name": "12H趋势+4H下单 (灵云+祥云)", "desc": "收益率94%, 回撤-22.3%", "file_prefix": "ss_12h_4h_ly_xy_pct"},
            {"id": "ss_4h_2h_xy_xy_pct", "name": "4H趋势+2H下单 (祥云+祥云)", "desc": "收益率87%, 回撤-28.7%", "file_prefix": "ss_4h_2h_xy_xy_pct"},
            {"id": "ss_6h_2h_xy_xy_pct", "name": "6H趋势+2H下单 (祥云+祥云)", "desc": "收益率84%, 回撤-26.5%", "file_prefix": "ss_6h_2h_xy_xy_pct"},
            {"id": "ss_1d_6h_xy_xy_pct", "name": "1D趋势+6H下单 (祥云+祥云)", "desc": "收益率79%, 回撤-21.6%", "file_prefix": "ss_1d_6h_xy_xy_pct"},
            {"id": "ss_8h_3h_ly_xy_pct", "name": "8H趋势+3H下单 (灵云+祥云)", "desc": "收益率89%, 回撤-31.2%", "file_prefix": "ss_8h_3h_ly_xy_pct"},
            {"id": "ss_6h_3h_ly_xy_pct", "name": "6H趋势+3H下单 (灵云+祥云)", "desc": "收益率66%, 回撤-22.8%", "file_prefix": "ss_6h_3h_ly_xy_pct"},
            {"id": "ss_3h_1h_xy_xy_pct", "name": "3H趋势+1H下单 (祥云+祥云)", "desc": "收益率66%, 回撤-29.2%", "file_prefix": "ss_3h_1h_xy_xy_pct"},
            {"id": "ss_12h_6h_xy_xy_pct", "name": "12H趋势+6H下单 (祥云+祥云)", "desc": "收益率49%, 回撤-20.5%", "file_prefix": "ss_12h_6h_xy_xy_pct"},
            {"id": "ss_6h_2h_ly_ly_pct", "name": "6H趋势+2H下单 (灵云+灵云)", "desc": "收益率61%, 回撤-52.3%", "file_prefix": "ss_6h_2h_ly_ly_pct"},
            {"id": "ss_1d_8h_ly_ly_pct", "name": "1D趋势+8H下单 (灵云+灵云)", "desc": "收益率72%, 回撤-22.1%", "file_prefix": "ss_1d_8h_ly_ly_pct"},
            {"id": "ss_12h_4h_ly_ly_pct", "name": "12H趋势+4H下单 (灵云+灵云)", "desc": "收益率97%, 回撤-29.0%", "file_prefix": "ss_12h_4h_ly_ly_pct"},
            {"id": "ss_3h_1h_ly_xy_pct", "name": "3H趋势+1H下单 (灵云+祥云)", "desc": "收益率44%, 回撤-21.4%", "file_prefix": "ss_3h_1h_ly_xy_pct"},
            {"id": "ss_8h_3h_ly_ly_pct", "name": "8H趋势+3H下单 (灵云+灵云)", "desc": "收益率96%, 回撤-51.0%", "file_prefix": "ss_8h_3h_ly_ly_pct"},
            {"id": "ss_6h_3h_ly_ly_pct", "name": "6H趋势+3H下单 (灵云+灵云)", "desc": "收益率38%, 回撤-56.0%", "file_prefix": "ss_6h_3h_ly_ly_pct"},
            {"id": "ss_3h_1h_ly_ly_pct", "name": "3H趋势+1H下单 (灵云+灵云)", "desc": "收益率35%, 回撤-50.2%", "file_prefix": "ss_3h_1h_ly_ly_pct"},
        ]
    },
    {
        "group_name": "多周期共振 (5%权益)",
        "group_key": "multi_p5pct",
        "configs": _gen_multi_configs('p5pct', '5%权益'),
    },
    {
        "group_name": "多周期共振 (50K固定)",
        "group_key": "multi_50k",
        "configs": _gen_multi_configs('50k', '50K固定'),
    },
    {
        "group_name": "原始单周期 (固定$20K)",
        "group_key": "orig_fixed",
        "configs": [
            {"id": "config_4", "name": "固定风险 $20,000 (4H)", "desc": "基准配置, 4H数据", "file_prefix": "config_4"},
            {"id": "config_20000_6h", "name": "固定风险 $20,000 (6H)", "desc": "6H数据", "file_prefix": "config_20000_6h"},
            {"id": "config_3h_20000", "name": "固定风险 $20,000 (3H)", "desc": "3H数据", "file_prefix": "config_3h_20000"},
            {"id": "config_20000_8h", "name": "固定风险 $20,000 (8H)", "desc": "8H数据", "file_prefix": "config_20000_8h"},
            {"id": "config_2h_20000", "name": "固定风险 $20,000 (2H)", "desc": "2H数据", "file_prefix": "config_4_2h_fixed"},
            {"id": "config_1h_20000", "name": "固定风险 $20,000 (1H)", "desc": "1H数据", "file_prefix": "config_4_1h_fixed"},
            {"id": "config_20000_12h", "name": "固定风险 $20,000 (12H)", "desc": "12H数据", "file_prefix": "config_20000_12h"},
            {"id": "config_1d_20000", "name": "固定风险 $20,000 (1D)", "desc": "1D日线数据", "file_prefix": "config_4_1d_fixed"},
        ]
    },
    {
        "group_name": "原始单周期 (2%权益)",
        "group_key": "orig_pct",
        "configs": [
            {"id": "config_2pct_4h", "name": "2% 权益风险 (4H)", "desc": "4H数据", "file_prefix": "config_2pct_4h"},
            {"id": "config_2pct_6h", "name": "2% 权益风险 (6H)", "desc": "6H数据", "file_prefix": "config_2pct_6h"},
            {"id": "config_2pct_3h", "name": "2% 权益风险 (3H)", "desc": "3H数据", "file_prefix": "config_2pct_3h"},
            {"id": "config_2pct_8h", "name": "2% 权益风险 (8H)", "desc": "8H数据", "file_prefix": "config_2pct_8h"},
            {"id": "config_2pct_2h", "name": "2% 权益风险 (2H)", "desc": "2H数据", "file_prefix": "config_2pct_2h"},
            {"id": "config_2pct_1h", "name": "2% 权益风险 (1H)", "desc": "1H数据", "file_prefix": "config_2pct_1h"},
            {"id": "config_2pct_12h", "name": "2% 权益风险 (12H)", "desc": "12H数据", "file_prefix": "config_2pct_12h"},
            {"id": "config_2pct_1d", "name": "2% 权益风险 (1D)", "desc": "1D日线数据", "file_prefix": "config_2pct_1d"},
        ]
    },
]

# 扁平化所有配置
ALL_CONFIGS = []
for g in CONFIG_GROUPS:
    ALL_CONFIGS.extend(g["configs"])

DEFAULT_CONFIG_ID = "ss_6h_3h_xy_ly_pct"


def load_config(config):
    """加载回测数据"""
    prefix = config["file_prefix"]
    trades_file = os.path.join(RESULTS_DIR, f"{prefix}_trades.csv")
    equity_file = os.path.join(RESULTS_DIR, f"{prefix}_equity.csv")
    
    if not os.path.exists(trades_file) or not os.path.exists(equity_file):
        return None, None
    
    trades_df = pd.read_csv(trades_file)
    equity_df = pd.read_csv(equity_file)
    
    return trades_df, equity_df


def calculate_stats(trades_df, equity_df, config):
    """计算统计数据"""
    total_trades = len(trades_df)
    win_trades = len(trades_df[trades_df['pnl'] > 0])
    loss_trades = total_trades - win_trades
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    
    long_trades = trades_df[trades_df['side'] == 'long']
    short_trades = trades_df[trades_df['side'] == 'short']
    long_wr = (len(long_trades[long_trades['pnl'] > 0]) / len(long_trades) * 100) if len(long_trades) > 0 else 0
    short_wr = (len(short_trades[short_trades['pnl'] > 0]) / len(short_trades) * 100) if len(short_trades) > 0 else 0
    
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if win_trades > 0 else 0
    avg_loss = abs(trades_df[trades_df['pnl'] <= 0]['pnl'].mean()) if loss_trades > 0 else 0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
    
    total_pnl = trades_df['pnl'].sum()
    initial_capital = 1_000_000
    final_equity = initial_capital + total_pnl
    return_pct = (total_pnl / initial_capital * 100)
    
    equity_df = equity_df.copy()
    equity_df['peak'] = equity_df['equity'].cummax()
    equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
    max_drawdown = equity_df['drawdown'].min()
    
    total_fees = (trades_df['entry_fee'] + trades_df['exit_fee']).sum() if 'entry_fee' in trades_df.columns else 0
    total_slippage = trades_df['slippage_cost'].sum() if 'slippage_cost' in trades_df.columns else 0
    
    # 为每笔交易计算出场后的账户余额
    trades_list = trades_df.to_dict('records')
    running_balance = initial_capital
    for trade in trades_list:
        running_balance += trade['pnl']
        trade['balance_after'] = round(running_balance, 2)
    
    equity_data = equity_df[['time', 'equity']].copy()
    equity_data['time'] = equity_data['time'].astype(str)
    
    return {
        'equity': final_equity, 'return_pct': return_pct, 'total_pnl': total_pnl,
        'win_rate': win_rate, 'profit_factor': profit_factor, 'max_drawdown': max_drawdown,
        'total_trades': total_trades, 'win_trades': win_trades, 'loss_trades': loss_trades,
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'long_trades': len(long_trades), 'long_wr': round(long_wr, 2),
        'long_pnl': long_trades['pnl'].sum() if len(long_trades) > 0 else 0,
        'short_trades': len(short_trades), 'short_wr': round(short_wr, 2),
        'short_pnl': short_trades['pnl'].sum() if len(short_trades) > 0 else 0,
        'total_fees': total_fees, 'total_slippage': total_slippage,
        'trades': trades_list, 'equity_data': equity_data.to_dict('records'),
        'config_name': config['name'], 'config_description': config['desc'],
        'config_id': config['id']
    }


def get_all_configs_stats():
    """获取所有配置的概览数据"""
    results = []
    for config in ALL_CONFIGS:
        try:
            trades_df, equity_df = load_config(config)
            if trades_df is None:
                continue
            stats = calculate_stats(trades_df, equity_df, config)
            results.append({
                'id': config['id'], 'name': config['name'], 'description': config['desc'],
                'total_trades': stats['total_trades'], 'win_rate': stats['win_rate'],
                'profit_factor': stats['profit_factor'], 'return_pct': stats['return_pct'],
                'max_drawdown': stats['max_drawdown']
            })
        except Exception as e:
            pass
    return results


# ==========================================
# 模板
# ==========================================
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>筋斗云量化监控系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f7fa; color: #333; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
        .header h1 { font-size: 24px; margin-bottom: 5px; }
        .header p { opacity: 0.8; font-size: 14px; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .stat-card .label { color: #666; font-size: 14px; margin-bottom: 5px; }
        .stat-card .value { font-size: 28px; font-weight: bold; color: #333; }
        .stat-card .value.green { color: #22c55e; }
        .stat-card .value.red { color: #ef4444; }
        .stat-card .change { font-size: 12px; margin-top: 5px; }
        .panel { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .panel h2 { font-size: 18px; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f9fafb; font-weight: 600; color: #666; }
        .badge { padding: 3px 8px; border-radius: 5px; font-size: 12px; }
        .badge.long { background: #dcfce7; color: #166534; }
        .badge.short { background: #fee2e2; color: #991b1b; }
        .badge.profit { background: #dcfce7; color: #166534; }
        .badge.loss { background: #fee2e2; color: #991b1b; }
        .refresh-btn { position: fixed; bottom: 20px; right: 20px; background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 25px; cursor: pointer; }
        .chart-container { height: 300px; margin-top: 20px; }
        
        /* 回测历史列表样式 */
        .backtest-list { 
            list-style: none; 
            display: grid; 
            grid-template-columns: 1fr; 
            gap: 10px; 
            max-height: 350px;
            overflow-y: auto;
            padding-right: 5px;
        }
        .backtest-list::-webkit-scrollbar { width: 6px; }
        .backtest-list::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
        .backtest-list::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 3px; }
        .backtest-list::-webkit-scrollbar-thumb:hover { background: #a1a1a1; }
        .backtest-item { 
            padding: 12px; 
            border: 1px solid #e5e7eb; 
            border-radius: 8px; 
            cursor: pointer;
            transition: all 0.2s;
            background: white;
        }
        .backtest-item:hover { 
            border-color: #667eea; 
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
            transform: translateY(-2px);
        }
        .backtest-item.active { 
            border-color: #667eea; 
            background: #f0f4ff;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }
        .backtest-item .config-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #333; }
        .backtest-item .config-desc { font-size: 12px; color: #666; margin-bottom: 8px; }
        .backtest-item .config-stats { display: flex; gap: 12px; flex-wrap: wrap; }
        .backtest-item .config-stats .stat { font-size: 12px; }
        .backtest-item .config-stats .stat-value { font-weight: 600; color: #333; }
        .backtest-item .config-stats .stat-value.green { color: #22c55e; }
        .backtest-item .config-stats .stat-value.red { color: #ef4444; }
        
        .current-config-banner { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 12px 20px; 
            border-radius: 8px; 
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .current-config-banner .config-label { font-size: 13px; opacity: 0.9; }
        .current-config-banner .config-name { font-size: 18px; font-weight: 600; margin-top: 2px; }
        
        /* 分组标签 */
        .group-header {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid;
        }
        .group-header.multi { color: #667eea; border-color: #667eea; }
        .group-header.orig-fixed { color: #764ba2; border-color: #764ba2; }
        .group-header.orig-pct { color: #f59e0b; border-color: #f59e0b; }
        
        /* 分组容器 */
        .groups-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        .group-panel {
            background: #fafafa;
            border-radius: 8px;
            padding: 15px;
        }
        
        @media (max-width: 1200px) {
            .groups-container { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>筋斗云量化监控系统</h1>
        <p>祥云突破策略 | 多周期共振回测 | BTC/USDT</p>
    </div>
    
    <div class="container">
        <!-- 当前配置横幅 -->
        <div class="current-config-banner" id="current-banner">
            <div>
                <div class="config-label">当前回测配置</div>
                <div class="config-name" id="current-config-name">{{ configs[0].name }}</div>
            </div>
            <div style="font-size: 13px; opacity: 0.9;" id="current-config-desc">{{ configs[0].description }}</div>
        </div>
        
        <!-- 核心指标 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">初始资金</div>
                <div class="value">$1,000,000</div>
            </div>
            <div class="stat-card">
                <div class="label">当前净值</div>
                <div class="value" id="stat-equity">{{ "%.0f"|format(equity) }}</div>
                <div class="change" id="stat-return">{{ "%.2f"|format(return_pct) }}%</div>
            </div>
            <div class="stat-card">
                <div class="label">总盈亏</div>
                <div class="value {{ 'green' if total_pnl > 0 else 'red' }}" id="stat-pnl">{{ "+" if total_pnl > 0 else "" }}${{ "{:,.0f}".format(total_pnl) }}</div>
            </div>
            <div class="stat-card">
                <div class="label">胜率</div>
                <div class="value" id="stat-winrate">{{ "%.1f"|format(win_rate) }}%</div>
            </div>
            <div class="stat-card">
                <div class="label">盈亏比</div>
                <div class="value" id="stat-pf">{{ "%.2f"|format(profit_factor) }}</div>
            </div>
            <div class="stat-card">
                <div class="label">最大回撤</div>
                <div class="value red" id="stat-dd">{{ "%.2f"|format(max_drawdown) }}%</div>
            </div>
        </div>
        
        <!-- 回测历史列表 - 按周期分组 -->
        <div class="panel">
            <h2>📜 回测历史（点击切换）</h2>
            <div class="groups-container">
                {% for group in config_groups %}
                <div class="group-panel">
                    <div class="group-header {{ 'multi' if group.group_key == 'multi_pct' else ('orig-fixed' if group.group_key == 'orig_fixed' else 'orig-pct') }}">
                        {{ group.group_name }}
                    </div>
                    <ul class="backtest-list" id="backtest-list-{{ group.group_key }}">
                        {% for config in group.configs %}
                        <li class="backtest-item {{ 'active' if (loop.first and group.group_key == active_group_key) else '' }}" 
                            onclick="loadConfig('{{ config.id }}')" 
                            data-id="{{ config.id }}">
                            <div class="config-name">{{ config.name }}</div>
                            <div class="config-desc">{{ config.description }}</div>
                            <div class="config-stats">
                                <span class="stat">交易: <span class="stat-value">{{ config.total_trades }}</span></span>
                                <span class="stat">胜率: <span class="stat-value {{ 'green' if config.win_rate > 50 else 'red' }}">{{ "%.1f"|format(config.win_rate) }}%</span></span>
                                <span class="stat">盈亏比: <span class="stat-value">{{ "%.2f"|format(config.profit_factor) }}</span></span>
                                <span class="stat">收益: <span class="stat-value {{ 'green' if config.return_pct > 0 else 'red' }}">{{ "%.1f"|format(config.return_pct) }}%</span></span>
                                <span class="stat">回撤: <span class="stat-value red">{{ "%.1f"|format(config.max_drawdown) }}%</span></span>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- 收益曲线 -->
        <div class="panel">
            <h2>📈 收益曲线</h2>
            <div class="chart-container">
                <canvas id="equityChart"></canvas>
            </div>
        </div>
        
        <!-- 交易统计 -->
        <div class="panel">
            <h2>📊 交易统计</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                <div>
                    <table id="stats-table-1">
                        <tr><th>指标</th><th>数值</th></tr>
                        <tr><td>总交易次数</td><td id="stat-total-trades">{{ total_trades }}</td></tr>
                        <tr><td>盈利次数</td><td style="color: green;" id="stat-wins">{{ win_trades }}</td></tr>
                        <tr><td>亏损次数</td><td style="color: red;" id="stat-losses">{{ loss_trades }}</td></tr>
                        <tr><td>平均盈利（含手续费）</td><td style="color: green;" id="stat-avg-win">${{ "{:,.0f}".format(avg_win) }}</td></tr>
                        <tr><td>平均亏损（含手续费）</td><td style="color: red;" id="stat-avg-loss">${{ "{:,.0f}".format(avg_loss) }}</td></tr>
                        <tr><td>总手续费+滑点</td><td id="stat-total-fees" style="color: #e67e22;">${{ "{:,.2f}".format(total_fees + total_slippage) }}</td></tr>
                    </table>
                </div>
                <div>
                    <table id="stats-table-2">
                        <tr><th>方向</th><th>次数</th><th>胜率</th><th>盈亏</th></tr>
                        <tr>
                            <td><span class="badge long">做多</span></td>
                            <td id="stat-long-trades">{{ long_trades }}</td>
                            <td id="stat-long-wr">{{ long_wr }}%</td>
                            <td id="stat-long-pnl" style="color: {{ 'green' if long_pnl > 0 else 'red' }};">${{ "{:,.0f}".format(long_pnl) }}</td>
                        </tr>
                        <tr>
                            <td><span class="badge short">做空</span></td>
                            <td id="stat-short-trades">{{ short_trades }}</td>
                            <td id="stat-short-wr">{{ short_wr }}%</td>
                            <td id="stat-short-pnl" style="color: {{ 'green' if short_pnl > 0 else 'red' }};">${{ "{:,.0f}".format(short_pnl) }}</td>
                        </tr>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- 交易明细 -->
        <div class="panel">
            <h2>📋 交易明细（共 <span id="trades-count">{{ total_trades }}</span> 笔）</h2>
            <table>
                <thead>
                    <tr>
                        <th>序号</th><th>方向</th><th>入场时间</th><th>入场价</th><th>入场金额</th>
                        <th>出场时间</th><th>出场价</th><th>盈亏</th><th>手续费</th><th>账户余额</th><th>原因</th>
                    </tr>
                </thead>
                <tbody id="trades-tbody">
                    <!-- 由 JavaScript 动态渲染 -->
                </tbody>
            </table>
            <div id="pagination" style="display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 20px; padding: 15px 0;">
                <!-- 分页控件由 JavaScript 渲染 -->
            </div>
        </div>
    </div>
    
    <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
    
    <script>
        // 初始数据（从后端注入）
        let tradesData = {{ trades|tojson }};
        let equityData = {{ equity_data|tojson }};
        let currentConfigId = '{{ configs[0].id }}';
        const PAGE_SIZE = 20;
        let currentPage = 1;
        let totalPages = Math.ceil(tradesData.length / PAGE_SIZE);
        let equityChart = null;
        
        function renderTrades(page) {
            const tbody = document.getElementById('trades-tbody');
            const start = (page - 1) * PAGE_SIZE;
            const end = start + PAGE_SIZE;
            const pageTrades = tradesData.slice(start, end);
            
            tbody.innerHTML = pageTrades.map((trade, idx) => {
                const globalIndex = start + idx + 1;
                const isProfit = parseFloat(trade.pnl) > 0;
                const totalFee = parseFloat(trade.entry_fee) + parseFloat(trade.exit_fee);
                const stake = parseFloat(trade.stake) || 0;
                const sideClass = trade.side === 'long' ? 'long' : 'short';
                const sideText = trade.side === 'long' ? '做多' : '做空';
                const pnlClass = isProfit ? 'profit' : 'loss';
                const pnlText = (isProfit ? '+' : '') + '$' + parseFloat(trade.pnl).toFixed(2);
                const entryDate = trade.entry_time.substring(0, 10);
                const entryTime = trade.entry_time.substring(11, 19);
                const exitDate = trade.exit_time.substring(0, 10);
                const exitTime = trade.exit_time.substring(11, 19);
                const balanceAfter = trade.balance_after ? '$' + parseFloat(trade.balance_after).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '-';
                
                return `<tr>
                    <td>${globalIndex}</td>
                    <td><span class="badge ${sideClass}">${sideText}</span></td>
                    <td><div style="line-height: 1.4;"><div style="font-weight: 500;">${entryDate}</div><div style="font-size: 12px; color: #666;">${entryTime}</div></div></td>
                    <td>${parseFloat(trade.entry_price).toLocaleString('en-US', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
                    <td>$${stake.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td><div style="line-height: 1.4;"><div style="font-weight: 500;">${exitDate}</div><div style="font-size: 12px; color: #666;">${exitTime}</div></div></td>
                    <td>${parseFloat(trade.exit_price).toLocaleString('en-US', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
                    <td><span class="badge ${pnlClass}">${pnlText}</span></td>
                    <td>$${totalFee.toFixed(2)}</td>
                    <td style="font-weight: 600; color: ${parseFloat(trade.balance_after || 0) >= 1000000 ? '#22c55e' : '#ef4444'};">${balanceAfter}</td>
                    <td>${trade.exit_reason}</td>
                </tr>`;
            }).join('');
            
            renderPagination();
        }
        
        function renderPagination() {
            const pagination = document.getElementById('pagination');
            if (totalPages <= 1) {
                pagination.innerHTML = '';
                return;
            }
            
            let html = '';
            
            html += `<button onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''} 
                     style="padding: 8px 16px; border: 1px solid #ddd; background: ${currentPage === 1 ? '#f5f5f5' : 'white'}; 
                            border-radius: 5px; cursor: ${currentPage === 1 ? 'not-allowed' : 'pointer'}; 
                            opacity: ${currentPage === 1 ? '0.5' : '1'};">上一页</button>`;
            
            let startPage = Math.max(1, currentPage - 3);
            let endPage = Math.min(totalPages, startPage + 6);
            if (endPage - startPage < 6) {
                startPage = Math.max(1, endPage - 6);
            }
            
            if (startPage > 1) {
                html += `<button onclick="goToPage(1)" style="padding: 8px 12px; border: 1px solid #ddd; background: white; border-radius: 5px; cursor: pointer;">1</button>`;
                if (startPage > 2) html += '<span style="padding: 0 5px;">...</span>';
            }
            
            for (let i = startPage; i <= endPage; i++) {
                const isActive = i === currentPage;
                html += `<button onclick="goToPage(${i})" 
                         style="padding: 8px 12px; border: 1px solid ${isActive ? '#667eea' : '#ddd'}; 
                                background: ${isActive ? '#667eea' : 'white'}; 
                                color: ${isActive ? 'white' : '#333'};
                                border-radius: 5px; cursor: pointer; font-weight: ${isActive ? 'bold' : 'normal'};">${i}</button>`;
            }
            
            if (endPage < totalPages) {
                if (endPage < totalPages - 1) html += '<span style="padding: 0 5px;">...</span>';
                html += `<button onclick="goToPage(${totalPages})" style="padding: 8px 12px; border: 1px solid #ddd; background: white; border-radius: 5px; cursor: pointer;">${totalPages}</button>`;
            }
            
            html += `<button onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''} 
                     style="padding: 8px 16px; border: 1px solid #ddd; background: ${currentPage === totalPages ? '#f5f5f5' : 'white'}; 
                            border-radius: 5px; cursor: ${currentPage === totalPages ? 'not-allowed' : 'pointer'}; 
                            opacity: ${currentPage === totalPages ? '0.5' : '1'};">下一页</button>`;
            
            html += `<span style="margin-left: 15px; color: #666; font-size: 14px;">第 ${currentPage} / ${totalPages} 页</span>`;
            
            pagination.innerHTML = html;
        }
        
        function goToPage(page) {
            if (page < 1 || page > totalPages) return;
            currentPage = page;
            renderTrades(currentPage);
            document.getElementById('trades-tbody').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        function updateEquityChart() {
            if (equityChart) {
                equityChart.destroy();
            }
            const ctx = document.getElementById('equityChart').getContext('2d');
            equityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: equityData.map(d => d.time),
                    datasets: [{
                        label: '账户净值 (USD)',
                        data: equityData.map(d => d.equity),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        fill: true,
                        tension: 0.1,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        zoom: {
                            pan: { enabled: true, mode: 'x' },
                            zoom: {
                                wheel: { enabled: true },
                                pinch: { enabled: true },
                                mode: 'x',
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            ticks: { maxTicksLimit: 10 },
                            min: equityData.length > 200 ? equityData[equityData.length - 200].time : undefined
                        },
                        y: { display: true, ticks: { callback: v => '$' + v.toLocaleString() } }
                    }
                }
            });
        }
        
        function loadConfig(configId) {
            // 显示加载状态
            document.querySelectorAll('.backtest-item').forEach(item => {
                item.classList.remove('active');
            });
            document.querySelector(`.backtest-item[data-id="${configId}"]`).classList.add('active');
            
            // 请求后端数据
            fetch(`/api/config/${configId}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        const stats = data.data;
                        tradesData = stats.trades;
                        equityData = stats.equity_data;
                        currentPage = 1;
                        totalPages = Math.ceil(tradesData.length / PAGE_SIZE);
                        
                        // 更新统计卡片
                        document.getElementById('stat-equity').textContent = '$' + Math.round(stats.equity).toLocaleString();
                        document.getElementById('stat-return').textContent = stats.return_pct.toFixed(2) + '%';
                        document.getElementById('stat-pnl').textContent = (stats.total_pnl > 0 ? '+' : '') + '$' + Math.round(stats.total_pnl).toLocaleString();
                        document.getElementById('stat-pnl').className = 'value ' + (stats.total_pnl > 0 ? 'green' : 'red');
                        document.getElementById('stat-winrate').textContent = stats.win_rate.toFixed(1) + '%';
                        document.getElementById('stat-pf').textContent = stats.profit_factor.toFixed(2);
                        document.getElementById('stat-dd').textContent = stats.max_drawdown.toFixed(2) + '%';
                        
                        // 更新横幅
                        document.getElementById('current-config-name').textContent = stats.config_name;
                        document.getElementById('current-config-desc').textContent = stats.config_description;
                        
                        // 更新交易统计表格
                        document.getElementById('stat-total-trades').textContent = stats.total_trades;
                        document.getElementById('stat-wins').textContent = stats.win_trades;
                        document.getElementById('stat-losses').textContent = stats.loss_trades;
                        document.getElementById('stat-avg-win').textContent = '$' + Math.round(stats.avg_win).toLocaleString();
                        document.getElementById('stat-avg-loss').textContent = '$' + Math.round(stats.avg_loss).toLocaleString();
                        document.getElementById('stat-total-fees').textContent = '$' + (stats.total_fees + stats.total_slippage).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        document.getElementById('stat-long-trades').textContent = stats.long_trades;
                        document.getElementById('stat-long-wr').textContent = stats.long_wr.toFixed(1) + '%';
                        document.getElementById('stat-long-pnl').textContent = '$' + Math.round(stats.long_pnl).toLocaleString();
                        document.getElementById('stat-long-pnl').style.color = stats.long_pnl > 0 ? 'green' : 'red';
                        document.getElementById('stat-short-trades').textContent = stats.short_trades;
                        document.getElementById('stat-short-wr').textContent = stats.short_wr.toFixed(1) + '%';
                        document.getElementById('stat-short-pnl').textContent = '$' + Math.round(stats.short_pnl).toLocaleString();
                        document.getElementById('stat-short-pnl').style.color = stats.short_pnl > 0 ? 'green' : 'red';
                        
                        // 更新交易计数
                        document.getElementById('trades-count').textContent = stats.total_trades;
                        
                        // 重新渲染
                        renderTrades(1);
                        updateEquityChart();
                    }
                })
                .catch(err => {
                    console.error('加载配置失败:', err);
                    alert('加载配置失败，请查看控制台');
                });
        }
        
        // 初始渲染
        renderTrades(1);
        updateEquityChart();
    </script>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
</body>
</html>
"""


# ==========================================
# 路由
# ==========================================
@APP.route('/')
def dashboard():
    """主仪表盘"""
    try:
        # 获取所有配置的概览
        all_stats = get_all_configs_stats()
        
        # 按分组组织数据
        config_groups_data = []
        active_group_key = None
        for group in CONFIG_GROUPS:
            group_configs = []
            for config in group['configs']:
                stat = next((s for s in all_stats if s['id'] == config['id']), None)
                if stat:
                    group_configs.append(stat)
            if group_configs:
                config_groups_data.append({
                    'group_name': group['group_name'],
                    'group_key': group['group_key'],
                    'configs': group_configs
                })
                # 查找默认配置所在的分组
                if config['id'] == DEFAULT_CONFIG_ID:
                    active_group_key = group['group_key']
        
        if not active_group_key and config_groups_data:
            active_group_key = config_groups_data[0]['group_key']
        
        # 加载默认配置的数据
        config = next((c for c in ALL_CONFIGS if c['id'] == DEFAULT_CONFIG_ID), ALL_CONFIGS[0])
        trades_df, equity_df = load_config(config)
        stats = calculate_stats(trades_df, equity_df, config)
        
        return render_template_string(MAIN_TEMPLATE, 
                                     **stats, 
                                     config_groups=config_groups_data,
                                     active_group_key=active_group_key,
                                     configs=[config])
    except Exception as e:
        return f"<h1>数据加载失败</h1><p>错误: {str(e)}</p>"


@APP.route('/api/config/<config_id>')
def api_config(config_id):
    """获取指定配置的完整数据"""
    try:
        config = next((c for c in ALL_CONFIGS if c['id'] == config_id), None)
        if not config:
            return jsonify({'status': 'error', 'message': f'配置 {config_id} 不存在'}), 404
        
        trades_df, equity_df = load_config(config)
        if trades_df is None:
            return jsonify({'status': 'error', 'message': f'配置 {config_id} 的数据文件不存在'}), 404
        
        stats = calculate_stats(trades_df, equity_df, config)
        return jsonify({
            'status': 'success',
            'data': stats
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@APP.route('/api/stats')
def api_stats():
    """API 接口 - 默认配置"""
    try:
        config = next((c for c in ALL_CONFIGS if c['id'] == DEFAULT_CONFIG_ID), ALL_CONFIGS[0])
        trades_df, equity_df = load_config(config)
        stats = calculate_stats(trades_df, equity_df, config)
        return jsonify({
            'status': 'success',
            'data': {
                'equity': stats['equity'],
                'return_pct': stats['return_pct'],
                'total_pnl': stats['total_pnl'],
                'win_rate': stats['win_rate'],
                'profit_factor': stats['profit_factor'],
                'max_drawdown': stats['max_drawdown'],
                'total_trades': stats['total_trades']
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@APP.route('/api/trades')
def api_trades():
    """交易记录 API"""
    try:
        config = next((c for c in ALL_CONFIGS if c['id'] == DEFAULT_CONFIG_ID), ALL_CONFIGS[0])
        trades_df, _ = load_config(config)
        return jsonify({
            'status': 'success',
            'data': trades_df.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@APP.route('/api/configs')
def api_configs():
    """获取所有配置列表"""
    return jsonify({
        'status': 'success',
        'data': {
            'groups': CONFIG_GROUPS,
            'configs': ALL_CONFIGS
        }
    })


# ==========================================
# 启动
# ==========================================
if __name__ == '__main__':
    print("=" * 60)
    print("筋斗云量化监控系统 v2")
    print("=" * 60)
    print("访问地址: http://localhost:5000")
    print(f"回测配置数量: {len(ALL_CONFIGS)}")
    print(f"分组数量: {len(CONFIG_GROUPS)}")
    print("=" * 60)
    APP.run(host='0.0.0.0', port=5000, debug=False)
