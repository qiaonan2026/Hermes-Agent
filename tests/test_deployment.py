"""
部署验证脚本
检查系统配置和依赖
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
print(f"  Python版本: {sys.version}")
print(f"  Python路径: {sys.executable}")
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

# 4. 检查环境变量
print("【4】环境变量检查")
from dotenv import load_dotenv
load_dotenv()

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
    value = os.getenv(var)
    is_set = value is not None and value != ""
    all_env_set = all_env_set and is_set
    status = "✓" if is_set else "✗"
    display_value = value[:10] + "..." if value and len(value) > 10 else value
    print(f"  {status} {var} = {display_value if is_set else '未设置'}")

print()
print("  可选环境变量:")
for var in optional_env_vars:
    value = os.getenv(var)
    is_set = value is not None and value != ""
    status = "✓" if is_set else "-"
    display_value = value[:10] + "..." if value and len(value) > 10 else value
    print(f"  {status} {var} = {display_value if is_set else '未设置'}")

print()

# 5. 检查Python依赖
print("【5】Python依赖检查")
dependencies = [
    ("yaml", "PyYAML"),
    ("pydantic", "Pydantic"),
    ("httpx", "httpx"),
    ("structlog", "structlog"),
    ("dotenv", "python-dotenv"),
    ("rich", "rich")
]

missing_deps = []
for module, package in dependencies:
    try:
        __import__(module)
        print(f"  ✓ {package}")
    except ImportError:
        print(f"  ✗ {package} (未安装)")
        missing_deps.append(package)

print()

# 6. 配置文件验证
print("【6】配置文件验证")
try:
    import yaml
    config_file = project_root / "config" / "hermes_config.yaml"
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 检查关键配置
    checks = [
        ("hermes.profile", config.get("hermes", {}).get("profile")),
        ("gateways.feishu.enabled", config.get("gateways", {}).get("feishu", {}).get("enabled")),
        ("memory.honcho.enabled", config.get("memory", {}).get("honcho", {}).get("enabled")),
        ("skills.auto_generate", config.get("skills", {}).get("auto_generate"))
    ]
    
    for key, value in checks:
        status = "✓" if value else "✗"
        print(f"  {status} {key} = {value}")
        
except Exception as e:
    print(f"  ✗ 配置文件解析失败: {e}")

print()

# 7. 总结
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

if missing_deps:
    issues.append(f"缺少依赖: {', '.join(missing_deps)}")

if issues:
    print("  状态: ⚠️  存在问题")
    print()
    print("  问题列表:")
    for issue in issues:
        print(f"    - {issue}")
    print()
    print("  建议操作:")
    if missing_deps:
        print(f"    1. 安装缺失依赖: pip install {' '.join(missing_deps)}")
    if not all_env_set:
        print("    2. 配置.env文件中的环境变量")
else:
    print("  状态: ✓ 所有检查通过")
    print()
    print("  系统已准备就绪，可以启动！")
    print()
    print("  启动命令:")
    print("    python src/main.py")
    print("  或")
    print("    ./scripts/start.sh")

print()
print("=" * 60)
