"""
Hermes-Agent智能客服系统主程序
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from structlog import get_logger
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.gateways import FeishuGateway, FeishuMessage

logger = get_logger()
console = Console()

# 加载环境变量
load_dotenv()


class HermesCustomerService:
    """Hermes智能客服系统"""
    
    def __init__(self, config_path: str = "config/hermes_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.feishu_gateway: Optional[FeishuGateway] = None
        self.running = False
        
    def _load_config(self) -> dict:
        """加载配置文件"""
        config_file = project_root / self.config_path
        
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # 替换环境变量
        config = self._replace_env_vars(config)
        return config
    
    def _replace_env_vars(self, config: dict) -> dict:
        """递归替换配置中的环境变量"""
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str):
            # 处理 ${VAR} 或 ${VAR:default} 格式
            if config.startswith("${") and config.endswith("}"):
                var_spec = config[2:-1]
                if ":" in var_spec:
                    var_name, default = var_spec.split(":", 1)
                    return os.getenv(var_name, default)
                else:
                    return os.getenv(var_spec, "")
        return config
    
    async def initialize(self):
        """初始化系统"""
        console.print(Panel.fit(
            "[bold cyan]Hermes智能客服系统[/bold cyan]\n"
            "正在初始化...",
            border_style="cyan"
        ))
        
        # 初始化飞书Gateway
        if self.config.get("gateways", {}).get("feishu", {}).get("enabled"):
            await self._init_feishu_gateway()
            
        console.print("[green]✓ 系统初始化完成[/green]")
        
    async def _init_feishu_gateway(self):
        """初始化飞书Gateway"""
        feishu_config = self.config["gateways"]["feishu"]
        
        self.feishu_gateway = FeishuGateway(
            app_id=feishu_config["app_id"],
            app_secret=feishu_config["app_secret"],
            encrypt_key=feishu_config.get("encrypt_key"),
            verification_token=feishu_config.get("verification_token")
        )
        
        # 设置消息处理器
        self.feishu_gateway.set_message_handler(self._handle_customer_message)
        
        # 获取访问令牌
        await self.feishu_gateway.get_tenant_access_token()
        
        console.print("[green]✓ 飞书Gateway初始化成功[/green]")
        
    async def _handle_customer_message(self, message: FeishuMessage) -> str:
        """处理客户消息"""
        try:
            # 解析消息内容
            content = json.loads(message.content) if message.msg_type == "text" else {}
            text = content.get("text", "")
            
            logger.info(
                "处理客户消息",
                message_id=message.message_id,
                chat_id=message.chat_id,
                text=text[:50]  # 只记录前50个字符
            )
            
            # TODO: 实现消息处理逻辑
            # 1. 理解客户意图
            # 2. 检索知识库
            # 3. 生成回复
            # 4. 记录对话历史
            
            # 简单回复示例
            response = f"收到您的消息：{text}\n我是智能客服助手，正在为您处理中..."
            
            return response
            
        except Exception as e:
            logger.error("处理客户消息失败", error=str(e))
            return "抱歉，处理您的消息时出现错误，请稍后重试。"
    
    async def start(self):
        """启动系统"""
        await self.initialize()
        
        console.print("\n[bold green]系统已启动，等待消息...[/bold green]")
        console.print("[dim]按 Ctrl+C 停止系统[/dim]\n")
        
        self.running = True
        
        # 显示系统状态
        self._show_status()
        
        # 保持运行
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await self.stop()
            
    async def stop(self):
        """停止系统"""
        console.print("\n[yellow]正在停止系统...[/yellow]")
        self.running = False
        console.print("[green]系统已停止[/green]")
        
    def _show_status(self):
        """显示系统状态"""
        status_table = Table(title="系统状态")
        status_table.add_column("组件", style="cyan")
        status_table.add_column("状态", style="green")
        
        # 飞书Gateway状态
        feishu_status = "已连接" if self.feishu_gateway and self.feishu_gateway.access_token else "未连接"
        status_table.add_row("飞书Gateway", feishu_status)
        
        # Profile信息
        profile = self.config.get("hermes", {}).get("profile", "N/A")
        status_table.add_row("Profile", profile)
        
        # 工作目录
        workspace = self.config.get("hermes", {}).get("workspace", "N/A")
        status_table.add_row("工作目录", workspace)
        
        console.print(status_table)


async def main():
    """主函数"""
    try:
        # 创建系统实例
        system = HermesCustomerService()
        
        # 启动系统
        await system.start()
        
    except Exception as e:
        console.print(f"\n[red]系统启动失败: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    import json
    asyncio.run(main())
