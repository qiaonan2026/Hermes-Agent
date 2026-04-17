"""
简化版部署验证脚本
不依赖外部库，仅检查文件和配置
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("  Hermes-Agent智能客服系统 - 部署验证")
print("=" * 60)
print()

# 1. 检查Python版本
print("【1】Python环境检查")
print(f"  ✓ Python版本: {sys.version.split()[0]}")
print(f"  ✓ Python路径: {sys.executable}")
print()

# 2. 检查项目结构
print("【2】项目结构检查")
required_dirs = [
    "config",
    "workspace/customer_service",
    "src",
    "src/gateways",
    "src/memory",
    "src/skills",
    "src/training",
    "src/security",
    "src/monitoring",
    "scripts"
]

all_dirs_exist = True
for dir_path in required_dirs:
    full_path = project_root / dir_path
    exists = full_path.exists()
    all_dirs_exist = all_dirs_exist and exists
    status = "✓" if exists else "✗"
    print(f"  {status} {dir_path}")

print()

# 3. 检查关键文件
print("【3】关键文件检查")
required_files = [
    ".env",
    ".gitignore",
    "config/hermes_config.yaml",
    "config/user_profile_schema.json",
    "workspace/customer_service/SOUL.md",
    "workspace/customer_service/MEMORY.md",
    "src/main.py",
    "src/gateways/feishu_gateway.py",
    "requirements.txt"
]

all_files_exist = True
for file_path in required_files:
    full_path = project_root / file_path
    exists = full_path.exists()
    all_files_exist = all_files_exist and exists
    status = "✓" if exists else "✗"
    print(f"  {status} {file_path}")

print()

# 4. 检查环境变量（手动读取.env文件）
print("【4】环境变量检查")
env_file = project_root / ".env"
env_vars = {}

if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value

required_env_vars = [
    "FEISHU_CUSTOMER_APP_ID",
    "FEISHU_CUSTOMER_APP_SECRET"
]

optional_env_vars = [
    "VOLCENGINE_ARK_API_KEY",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY"
]

all_env_set = True
for var in required_env_vars:
    value = env_vars.get(var, "")
    is_set = value != ""
    all_env_set = all_env_set and is_set
    status = "✓" if is_set else "✗"
    display_value = value[:10] + "..." if len(value) > 10 else value
    print(f"  {status} {var} = {display_value if is_set else '未设置'}")

print()
print("  可选环境变量:")
for var in optional_env_vars:
    value = env_vars.get(var, "")
    is_set = value != ""
    status = "✓" if is_set else "-"
    display_value = value[:10] + "..." if len(value) > 10 else value
    print(f"  {status} {var} = {display_value if is_set else '未设置'}")

print()

# 5. 检查源代码模块
print("【5】源代码模块检查")
modules = [
    "src/gateways/feishu_gateway.py",
    "src/memory/honcho_client.py",
    "src/memory/retaindb_client.py",
    "src/memory/memory_fence.py",
    "src/skills/skill_manager.py",
    "src/training/atropos_client.py",
    "src/training/subagent_manager.py",
    "src/security/sandbox_manager.py",
    "src/security/security_manager.py",
    "src/monitoring/metrics_collector.py"
]

all_modules_exist = True
for module_path in modules:
    full_path = project_root / module_path
    exists = full_path.exists()
    all_modules_exist = all_modules_exist and exists
    status = "✓" if exists else "✗"
    print(f"  {status} {module_path}")

print()

# 6. 配置文件验证
print("【6】配置文件验证")
config_file = project_root / "config" / "hermes_config.yaml"
if config_file.exists():
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 简单检查关键配置项
    checks = [
        ("profile: customer_service", "profile: customer_service" in content),
        ("feishu gateway", "feishu:" in content),
        ("honcho memory", "honcho:" in content),
        ("skills auto_generate", "auto_generate:" in content)
    ]
    
    for key, found in checks:
        status = "✓" if found else "✗"
        print(f"  {status} {key}")
else:
    print("  ✗ 配置文件不存在")

print()

# 7. 统计信息
print("【7】项目统计")
python_files = list(project_root.glob("src/**/*.py"))
config_files = list(project_root.glob("config/**/*"))
md_files = list(project_root.glob("workspace/**/*.md"))

print(f"  ✓ Python源文件: {len(python_files)} 个")
print(f"  ✓ 配置文件: {len(config_files)} 个")
print(f"  ✓ Markdown文档: {len(md_files)} 个")
print()

# 8. 总结
print("=" * 60)
print("  验证总结")
print("=" * 60)

issues = []

if not all_dirs_exist:
    issues.append("部分目录缺失")

if not all_files_exist:
    issues.append("部分文件缺失")

if not all_env_set:
    issues.append("必需的环境变量未设置")

if not all_modules_exist:
    issues.append("部分源代码模块缺失")

if issues:
    print("  状态: ⚠️  存在问题")
    print()
    print("  问题列表:")
    for issue in issues:
        print(f"    - {issue}")
    print()
    print("  建议操作:")
    print("    1. 检查并修复上述问题")
    print("    2. 安装Python依赖: pip install -r requirements.txt")
else:
    print("  状态: ✓ 所有检查通过")
    print()
    print("  系统已准备就绪！")
    print()
    print("  下一步操作:")
    print("    1. 安装依赖: pip install -r requirements.txt")
    print("    2. 启动系统: python src/main.py")
    print("    或使用启动脚本: ./scripts/start.sh")

print()
print("=" * 60)
