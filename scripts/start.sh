#!/bin/bash

# Hermes-Agent智能客服系统启动脚本

set -e

echo "========================================="
echo "  Hermes-Agent智能客服系统"
echo "========================================="
echo ""

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $PYTHON_VERSION"

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "错误: .env文件不存在"
    echo "请复制.env.example为.env并配置环境变量"
    exit 1
fi

# 加载环境变量
export $(cat .env | grep -v '^#' | xargs)

# 检查必需的环境变量
REQUIRED_VARS=(
    "FEISHU_CUSTOMER_APP_ID"
    "FEISHU_CUSTOMER_APP_SECRET"
    "OPENROUTER_API_KEY"
)

for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        echo "错误: 环境变量 $VAR 未设置"
        exit 1
    fi
done

echo "环境变量检查通过"
echo ""

# 创建必要的目录
mkdir -p data/vectors
mkdir -p data/memory
mkdir -p data/trajectories
mkdir -p logs
mkdir -p workspace/customer_service/skills

echo "目录结构检查完成"
echo ""

# 启动系统
echo "正在启动系统..."
python3 src/main.py
