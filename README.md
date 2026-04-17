# Hermes-Agent智能客服系统

基于Hermes-Agent框架的智能客服自动化系统，能够处理客户咨询、自动学习优化回复质量。

## 项目结构

```
Hermes-Agent/
├── config/                 # 配置文件目录
│   └── hermes_config.yaml  # 主配置文件
├── workspace/              # 工作空间
│   └── customer_service/   # 客服Profile
│       ├── SOUL.md         # AI人格定义
│       └── MEMORY.md       # 知识库
├── src/                    # 源代码
│   ├── gateways/           # 消息平台Gateway
│   │   └── feishu_gateway.py  # 飞书Gateway实现
│   └── main.py             # 主程序
├── scripts/                # 脚本工具
│   └── setup_feishu_gateway.py  # 飞书配置脚本
├── tests/                  # 测试代码
├── docs/                   # 文档
├── .env.example            # 环境变量模板
├── requirements.txt        # Python依赖
└── README.md               # 项目说明
```

## 快速开始

### 1. 环境准备

确保系统已安装：
- Python 3.11+
- pip

### 2. 安装依赖

```bash
# 克隆项目
cd Hermes-Agent

# 安装Python依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入实际配置
# 必须配置的项目：
# - FEISHU_CUSTOMER_APP_ID: 飞书机器人App ID
# - FEISHU_CUSTOMER_APP_SECRET: 飞书机器人App Secret
# - OPENROUTER_API_KEY: OpenRouter API密钥
# - ANTHROPIC_API_KEY: Anthropic API密钥
```

### 4. 配置飞书机器人

```bash
# 运行飞书配置脚本
python scripts/setup_feishu_gateway.py
```

### 5. 启动系统

```bash
# 启动智能客服系统
python src/main.py
```

## 配置说明

### 飞书机器人配置

1. 在飞书开放平台创建企业自建应用
2. 获取App ID和App Secret
3. 配置事件订阅和消息接收权限
4. 将App ID和App Secret填入.env文件

### API配置

系统支持多个LLM提供商：
- **OpenRouter**: 支持多种模型，推荐使用
- **Anthropic**: Claude系列模型
- **OpenAI**: GPT系列模型（备用）

### 知识库配置

编辑 `workspace/customer_service/MEMORY.md` 文件，添加：
- 产品信息
- 政策条款
- 常见问题
- FAQ模板

### AI人格配置

编辑 `workspace/customer_service/SOUL.md` 文件，定义：
- 核心特征
- 沟通风格
- 行为规则
- 情绪处理策略

## 功能特性

### 已实现功能

- ✅ 飞书消息接收和发送
- ✅ 基础配置系统
- ✅ 知识库管理
- ✅ AI人格定义
- ✅ 环境变量管理

### 待实现功能

- ⏳ Honcho用户建模
- ⏳ RetainDB向量搜索
- ⏳ 技能自动生成
- ⏳ Atropos RL训练
- ⏳ 多模型路由
- ⏳ MCP服务器集成
- ⏳ 监控告警系统

## 开发指南

### 添加新的消息平台

1. 在 `src/gateways/` 创建新的Gateway类
2. 实现消息接收和发送接口
3. 在配置文件中添加相应配置
4. 在主程序中初始化Gateway

### 扩展知识库

1. 编辑 `MEMORY.md` 文件
2. 添加新的产品信息、FAQ等
3. 系统会自动加载更新

### 自定义AI人格

1. 编辑 `SOUL.md` 文件
2. 定义AI的核心特征和行为规则
3. 调整沟通风格和情绪处理策略

## 测试

```bash
# 运行测试
pytest tests/

# 运行测试并生成覆盖率报告
pytest --cov=src tests/
```

## 监控

系统支持Prometheus指标导出，可通过Grafana进行可视化监控。

## 安全

- 所有敏感信息通过环境变量配置
- 支持消息加密和签名验证
- 实现了敏感信息过滤
- 支持沙箱隔离执行

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue或Pull Request。
