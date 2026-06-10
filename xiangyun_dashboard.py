#!/usr/bin/env python3
"""
祥云量化监控面板 - 中文版
基于 Freqtrade API 的轻量级中文监控面板
支持多回测配置切换
"""

from flask import Flask, render_template_string, jsonify, request
import requests
import json
import os
import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================
# 配置
# ==========================================
APP = Flask(__name__)

# 回测配置列表
BACKTEST_CONFIGS = [
    {
        "id": "config_2pct_4h",
        "name": "2% 权益风险 (4H)",
        "description": "4H 数据，每单风险为总资金的 2%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.02,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_4h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_4h_equity.csv"
    },
    {
        "id": "config_2pct_3h",
        "name": "2% 权益风险 (3H)",
        "description": "3H 数据，每单风险为总资金的 2%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.02,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_3h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_3h_equity.csv"
    },
    {
        "id": "config_2pct_2h",
        "name": "2% 权益风险 (2H)",
        "description": "2H 数据，每单风险为总资金的 2%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.02,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_2h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_2h_equity.csv"
    },
    {
        "id": "config_2pct_1h",
        "name": "2% 权益风险 (1H)",
        "description": "1H 数据，每单风险为总资金的 2%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.02,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_1h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_1h_equity.csv"
    },
    {
        "id": "config_2pct_1d",
        "name": "2% 权益风险 (1D)",
        "description": "1D 日线数据，每单风险为总资金的 2%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.02,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_1d_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_1d_equity.csv"
    },
    {
        "id": "config_2pct_15m",
        "name": "2% 权益风险 (15M)",
        "description": "15分钟数据，每单风险为总资金的 2%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.02,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_15m_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_15m_equity.csv"
    },
    {
        "id": "config_4",
        "name": "固定风险 $20,000 (4H)",
        "description": "4H 数据（13,467根K线，含祥云主轨），每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_4_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_4_equity.csv"
    },
    {
        "id": "config_1d_20000",
        "name": "固定风险 $20,000 (1D)",
        "description": "1D 日线数据，每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_4_1d_fixed_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_4_1d_fixed_equity.csv"
    },
    {
        "id": "config_3h_20000",
        "name": "固定风险 $20,000 (3H)",
        "description": "3H (180分钟) 数据（17,956根K线，含祥云主轨），每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_3h_20000_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_3h_20000_equity.csv"
    },
    {
        "id": "config_2h_20000",
        "name": "固定风险 $20,000 (2H)",
        "description": "2H (120分钟) 数据，每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_4_2h_fixed_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_4_2h_fixed_equity.csv"
    },
    {
        "id": "config_1h_20000",
        "name": "固定风险 $20,000 (1H)",
        "description": "1H (60分钟) 数据，每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_4_1h_fixed_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_4_1h_fixed_equity.csv"
    },
    {
        "id": "config_15m_20000",
        "name": "固定风险 $20,000 (15M)",
        "description": "15分钟数据，每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_15m_20000_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_15m_20000_equity.csv"
    },
    {
        "id": "config_20000_6h",
        "name": "固定风险 $20,000 (6H)",
        "description": "6H (360分钟) 数据，每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_20000_6h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_20000_6h_equity.csv"
    },
    {
        "id": "config_20000_8h",
        "name": "固定风险 $20,000 (8H)",
        "description": "8H (480分钟) 数据，每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_20000_8h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_20000_8h_equity.csv"
    },
    {
        "id": "config_20000_12h",
        "name": "固定风险 $20,000 (12H)",
        "description": "12H (720分钟) 数据，每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_20000_12h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_20000_12h_equity.csv"
    },
    {
        "id": "config_2pct_6h",
        "name": "2% 权益风险 (6H)",
        "description": "6H (360分钟) 数据，每单风险为总资金的 2%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.02,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_6h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_6h_equity.csv"
    },
    {
        "id": "config_2pct_8h",
        "name": "2% 权益风险 (8H)",
        "description": "8H (480分钟) 数据，每单风险为总资金的 2%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.02,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_8h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_8h_equity.csv"
    },
    {
        "id": "config_2pct_12h",
        "name": "2% 权益风险 (12H)",
        "description": "12H (720分钟) 数据，每单风险为总资金的 2%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.02,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_12h_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config_2pct_12h_equity.csv"
    }
]

# 默认使用最后一个配置
DEFAULT_CONFIG_ID = "config_4"

# ==========================================
# 模板
# ==========================================
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>祥云量化监控系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f7fa; color: #333; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
        .header h1 { font-size: 24px; margin-bottom: 5px; }
        .header p { opacity: 0.8; font-size: 14px; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
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
        
        /* 回测历史列表样式 - 双列网格 */
        .backtest-list { 
            list-style: none; 
            display: grid; 
            grid-template-columns: 1fr; 
            gap: 12px; 
            max-height: 380px;
            overflow-y: auto;
            padding-right: 5px;
        }
        .backtest-list::-webkit-scrollbar {
            width: 6px;
        }
        .backtest-list::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 3px;
        }
        .backtest-list::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 3px;
        }
        .backtest-list::-webkit-scrollbar-thumb:hover {
            background: #a1a1a1;
        }
        .backtest-item { 
            padding: 15px; 
            border: 1px solid #e5e7eb; 
            border-radius: 8px; 
            cursor: pointer;
            transition: all 0.2s;
            background: white;
            height: 100%;
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
        .backtest-item .config-name { font-weight: 600; font-size: 16px; margin-bottom: 5px; color: #333; }
        .backtest-item .config-desc { font-size: 13px; color: #666; margin-bottom: 10px; }
        .backtest-item .config-stats { display: flex; gap: 15px; flex-wrap: wrap; }
        .backtest-item .config-stats .stat { font-size: 13px; }
        .backtest-item .config-stats .stat-value { font-weight: 600; color: #333; }
        .backtest-item .config-stats .stat-value.green { color: #22c55e; }
        .backtest-item .config-stats .stat-value.red { color: #ef4444; }
        
        @media (max-width: 768px) {
            .backtest-list { grid-template-columns: 1fr; }
        }
        
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
    </style>
</head>
<body>
    <div class="header">
        <h1>筋斗云量化监控系统</h1>
        <p>祥云突破策略 | BTC/USDT</p>
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
        
        <!-- 回测历史列表 -->
        <div class="panel">
            <h2>📜 回测历史（点击切换）</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <!-- 左侧：固定风险 $20,000 -->
                <div>
                    <h3 style="font-size: 16px; margin-bottom: 12px; color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 8px;">固定风险 $20,000</h3>
                    <ul class="backtest-list" id="backtest-list-fixed">
                        {% for config in backtest_list if '固定风险' in config.name %}
                        <li class="backtest-item {{ 'active' if loop.first else '' }}" 
                            onclick="loadConfig('{{ config.id }}')" 
                            data-id="{{ config.id }}">
                            <div class="config-name">{{ config.name }}</div>
                            <div class="config-desc">{{ config.description }}</div>
                            <div class="config-stats">
                                <span class="stat">交易次数: <span class="stat-value">{{ config.total_trades }}</span></span>
                                <span class="stat">胜率: <span class="stat-value {{ 'green' if config.win_rate > 50 else 'red' }}">{{ "%.1f"|format(config.win_rate) }}%</span></span>
                                <span class="stat">盈亏比: <span class="stat-value">{{ "%.2f"|format(config.profit_factor) }}</span></span>
                                <span class="stat">收益率: <span class="stat-value {{ 'green' if config.return_pct > 0 else 'red' }}">{{ "%.2f"|format(config.return_pct) }}%</span></span>
                                <span class="stat">最大回撤: <span class="stat-value red">{{ "%.2f"|format(config.max_drawdown) }}%</span></span>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
                <!-- 右侧：2% 权益风险 -->
                <div>
                    <h3 style="font-size: 16px; margin-bottom: 12px; color: #764ba2; border-bottom: 2px solid #764ba2; padding-bottom: 8px;">2% 权益风险</h3>
                    <ul class="backtest-list" id="backtest-list-pct">
                        {% for config in backtest_list if '2%' in config.name %}
                        <li class="backtest-item" 
                            onclick="loadConfig('{{ config.id }}')" 
                            data-id="{{ config.id }}">
                            <div class="config-name">{{ config.name }}</div>
                            <div class="config-desc">{{ config.description }}</div>
                            <div class="config-stats">
                                <span class="stat">交易次数: <span class="stat-value">{{ config.total_trades }}</span></span>
                                <span class="stat">胜率: <span class="stat-value {{ 'green' if config.win_rate > 50 else 'red' }}">{{ "%.1f"|format(config.win_rate) }}%</span></span>
                                <span class="stat">盈亏比: <span class="stat-value">{{ "%.2f"|format(config.profit_factor) }}</span></span>
                                <span class="stat">收益率: <span class="stat-value {{ 'green' if config.return_pct > 0 else 'red' }}">{{ "%.2f"|format(config.return_pct) }}%</span></span>
                                <span class="stat">最大回撤: <span class="stat-value red">{{ "%.2f"|format(config.max_drawdown) }}%</span></span>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
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
                        <tr><td>总手续费</td><td id="stat-total-fees" style="color: #e67e22;">${{ "{:,.2f}".format(total_fees) }}</td></tr>
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
                        <th>出场时间</th><th>出场价</th><th>盈亏</th><th>手续费</th><th>原因</th>
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
# 数据加载
# ==========================================
def load_backtest_data(config_id=None):
    """加载回测数据"""
    if config_id is None:
        config_id = DEFAULT_CONFIG_ID
    
    config = next((c for c in BACKTEST_CONFIGS if c['id'] == config_id), None)
    if not config:
        raise ValueError(f"配置 {config_id} 不存在")
    
    trades_df = pd.read_csv(config['trades_file'])
    equity_df = pd.read_csv(config['equity_file'])
    
    return trades_df, equity_df, config


def calculate_stats(trades_df, equity_df, config):
    """计算统计数据"""
    total_trades = len(trades_df)
    win_trades = len(trades_df[trades_df['pnl'] > 0])
    loss_trades = total_trades - win_trades
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    
    # 做多做空统计
    long_trades = trades_df[trades_df['side'] == 'long']
    short_trades = trades_df[trades_df['side'] == 'short']
    long_wr = (len(long_trades[long_trades['pnl'] > 0]) / len(long_trades) * 100) if len(long_trades) > 0 else 0
    short_wr = (len(short_trades[short_trades['pnl'] > 0]) / len(short_trades) * 100) if len(short_trades) > 0 else 0
    
    # 盈亏分析
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if win_trades > 0 else 0
    avg_loss = abs(trades_df[trades_df['pnl'] <= 0]['pnl'].mean()) if loss_trades > 0 else 0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
    
    # 总盈亏
    total_pnl = trades_df['pnl'].sum()
    initial_capital = 1_000_000
    final_equity = initial_capital + total_pnl
    return_pct = (total_pnl / initial_capital * 100)
    
    # 最大回撤
    equity_df['peak'] = equity_df['equity'].cummax()
    equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
    max_drawdown = equity_df['drawdown'].min()
    
    # 成本统计
    total_fees = (trades_df['entry_fee'] + trades_df['exit_fee']).sum() if 'entry_fee' in trades_df.columns else 0
    total_slippage = trades_df['slippage_cost'].sum() if 'slippage_cost' in trades_df.columns else 0
    
    equity_df_copy = equity_df[['time', 'equity']].copy()
    equity_df_copy['time'] = equity_df_copy['time'].astype(str)
    
    return {
        'equity': final_equity,
        'return_pct': return_pct,
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'total_trades': total_trades,
        'win_trades': win_trades,
        'loss_trades': loss_trades,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'long_trades': len(long_trades),
        'long_wr': round(long_wr, 2),
        'long_pnl': long_trades['pnl'].sum() if len(long_trades) > 0 else 0,
        'short_trades': len(short_trades),
        'short_wr': round(short_wr, 2),
        'short_pnl': short_trades['pnl'].sum() if len(short_trades) > 0 else 0,
        'total_fees': total_fees,
        'total_slippage': total_slippage,
        'trades': trades_df.to_dict('records'),
        'equity_data': equity_df_copy.to_dict('records'),
        'config_name': config['name'],
        'config_description': config['description'],
        'config_id': config['id']
    }


def get_all_configs_stats():
    """获取所有配置的概览数据"""
    results = []
    for config in BACKTEST_CONFIGS:
        try:
            trades_df, equity_df, cfg = load_backtest_data(config['id'])
            stats = calculate_stats(trades_df, equity_df, cfg)
            results.append({
                'id': config['id'],
                'name': config['name'],
                'description': config['description'],
                'total_trades': stats['total_trades'],
                'win_rate': stats['win_rate'],
                'profit_factor': stats['profit_factor'],
                'return_pct': stats['return_pct'],
                'max_drawdown': stats['max_drawdown']
            })
        except Exception as e:
            print(f"加载配置 {config['id']} 失败: {e}")
    return results


# ==========================================
# 路由
# ==========================================
@APP.route('/')
def dashboard():
    """主仪表盘"""
    try:
        # 获取所有配置的概览
        backtest_list = get_all_configs_stats()
        
        # 加载默认配置的数据
        trades_df, equity_df, config = load_backtest_data(DEFAULT_CONFIG_ID)
        stats = calculate_stats(trades_df, equity_df, config)
        
        return render_template_string(MAIN_TEMPLATE, **stats, 
                                     backtest_list=backtest_list, 
                                     configs=[config])
    except Exception as e:
        return f"<h1>数据加载失败</h1><p>错误: {str(e)}</p>"


@APP.route('/api/config/<config_id>')
def api_config(config_id):
    """获取指定配置的完整数据"""
    try:
        trades_df, equity_df, config = load_backtest_data(config_id)
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
        trades_df, equity_df, config = load_backtest_data(DEFAULT_CONFIG_ID)
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
        trades_df, _, _ = load_backtest_data(DEFAULT_CONFIG_ID)
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
        'data': BACKTEST_CONFIGS
    })


# ==========================================
# 启动
# ==========================================
if __name__ == '__main__':
    print("=" * 60)
    print("祥云量化监控系统")
    print("=" * 60)
    print("访问地址: http://localhost:5000")
    print(f"回测配置数量: {len(BACKTEST_CONFIGS)}")
    print("=" * 60)
    APP.run(host='0.0.0.0', port=5000, debug=False)
