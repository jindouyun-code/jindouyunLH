#!/usr/bin/env python3
"""
回测配置定义
每种配置定义风险管理模式和成本参数
"""

BACKTEST_CONFIGS = [
    {
        "id": "config_1",
        "name": "固定风险 $2,000",
        "description": "每单固定风险金 $2,000，以损定量",
        "risk_mode": "fixed",
        "risk_amount": 2000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config1_fixed_2000_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config1_fixed_2000_equity.csv"
    },
    {
        "id": "config_2",
        "name": "5% 权益风险（无成本）",
        "description": "每单风险为总资金的 5%，不计手续费和滑点",
        "risk_mode": "percentage",
        "risk_pct": 0.05,
        "fee_rate": 0,
        "slippage_rate": 0,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config2_5pct_no_cost_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config2_5pct_no_cost_equity.csv"
    },
    {
        "id": "config_3",
        "name": "5% 权益风险（含成本）",
        "description": "每单风险为总资金的 5%，含手续费和滑点各万分之五",
        "risk_mode": "percentage",
        "risk_pct": 0.05,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config3_5pct_with_cost_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config3_5pct_with_cost_equity.csv"
    },
    {
        "id": "config_4",
        "name": "固定风险 $20,000",
        "description": "每单固定风险金 $20,000，以损定量，含手续费和滑点",
        "risk_mode": "fixed",
        "risk_amount": 20000,
        "fee_rate": 0.0005,
        "slippage_rate": 0.0005,
        "trades_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config4_fixed_20000_trades.csv",
        "equity_file": "/home/parallels/wwwroot/jindouyunLH/backtest_results/config4_fixed_20000_equity.csv"
    }
]
