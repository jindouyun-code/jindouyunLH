# 祥云量化监控系统 - 服务器部署包

## 压缩包信息

**名称**: WEB展示.zip  
**内容**: 回测结果数据 + WEB 展示页面  
**创建日期**: 2026-05-18

---

## 部署步骤

### 1. 解压文件

```bash
unzip WEB展示.zip
cd WEB展示
```

### 2. 安装依赖

```bash
pip3 install flask pandas numpy
```

或者使用启动脚本自动安装：

```bash
chmod +x start.sh
./start.sh
```

### 3. 启动服务

```bash
python3 xiangyun_dashboard.py
```

服务将在 `http://localhost:5000` 启动

### 4. 后台运行（可选）

```bash
nohup python3 xiangyun_dashboard.py > dashboard.log 2>&1 &
```

---

## 系统要求

- **Python**: 3.8+
- **依赖包**:
  - Flask (WEB 框架)
  - pandas (数据处理)
  - numpy (数值计算)

---

## 包含内容

### 回测数据 (backtest_results/)

包含 18 个回测配置的交易记录和权益曲线数据：

**固定风险 $20,000 策略** (9个周期):
- 1D, 4H, 3H, 2H, 1H, 15M, 6H, 8H, 12H

**2% 权益风险策略** (9个周期):
- 1D, 4H, 3H, 2H, 1H, 15M, 6H, 8H, 12H

### WEB 页面

- `xiangyun_dashboard.py` - Flask WEB 应用
- `start.sh` - 启动脚本

---

## 功能特性

1. **多策略对比**: 支持固定风险和 2% 权益风险两种策略
2. **全周期展示**: 9 个时间周期数据完整展示
3. **交互式切换**: 点击即可切换不同配置
4. **收益曲线**: 可视化账户净值变化
5. **交易明细**: 分页展示所有交易记录
6. **统计面板**: 胜率、盈亏比、回撤等关键指标

---

## 访问地址

- **本地**: http://localhost:5000
- **局域网**: http://[服务器IP]:5000

---

## 注意事项

1. 确保服务器 5000 端口未被占用
2. 如需外网访问，请配置防火墙规则
3. 生产环境建议使用 Nginx + Gunicorn 部署
4. 数据包仅包含回测结果，不包含原始 K 线数据

---

## 文件结构

```
WEB展示/
├── xiangyun_dashboard.py    # WEB 应用主程序
├── start.sh                 # 启动脚本
├── README.md               # 说明文档
└── backtest_results/       # 回测结果数据
    ├── config_4_trades.csv
    ├── config_4_equity.csv
    ├── config_2pct_4h_trades.csv
    ├── config_2pct_4h_equity.csv
    └── ... (其他配置文件)
```

---

**版本**: v1.0  
**备份编号**: 001
