#!/bin/bash
# 祥云量化监控系统 - 服务器启动脚本
# 使用方法: ./start.sh

echo "============================================================"
echo "祥云量化监控系统"
echo "============================================================"

# 检查 Python3 是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python3"
    exit 1
fi

# 检查依赖
echo "检查依赖包..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装 Flask..."
    pip3 install flask pandas numpy
fi

# 启动服务
echo ""
echo "启动祥云量化监控系统..."
echo "访问地址: http://localhost:5000"
echo "============================================================"

nohup python3 xiangyun_dashboard.py > dashboard.log 2>&1 &
PID=$!

echo "服务已启动 (PID: $PID)"
echo "日志文件: dashboard.log"
echo ""
echo "停止服务: kill $PID"
echo "查看日志: tail -f dashboard.log"
