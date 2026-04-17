#!/usr/bin/env python3
"""
飞书Gateway配置和初始化脚本
用于配置飞书机器人并测试连接
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# 加载环境变量
load_dotenv()


class FeishuGatewaySetup:
    """飞书Gateway配置类"""
    
    def __init__(self):
        self.app_id = os.getenv("FEISHU_CUSTOMER_APP_ID")
        self.app_secret = os.getenv("FEISHU_CUSTOMER_APP_SECRET")
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
        
    async def get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            result = response.json()
            
            if result.get("code") == 0:
                self.access_token = result.get("tenant_access_token")
                return self.access_token
            else:
                raise Exception(f"获取token失败: {result.get('msg')}")
    
    async def get_bot_info(self) -> dict:
        """获取机器人信息"""
        if not self.access_token:
            await self.get_tenant_access_token()
            
        url = f"{self.base_url}/bot/v3/info"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            result = response.json()
            
            if result.get("code") == 0:
                return result.get("data", {})
            else:
                raise Exception(f"获取机器人信息失败: {result.get('msg')}")
    
    async def test_message_send(self, receive_id: str, message: str = "测试消息") -> bool:
        """测试发送消息"""
        if not self.access_token:
            await self.get_tenant_access_token()
            
        url = f"{self.base_url}/im/v1/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "receive_id_type": "open_id"
        }
        
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": f'{{"text": "{message}"}}'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, params=params, json=payload)
            result = response.json()
            
            return result.get("code") == 0
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.app_id:
            console.print("[red]错误: FEISHU_CUSTOMER_APP_ID 未设置[/red]")
            return False
            
        if not self.app_secret:
            console.print("[red]错误: FEISHU_CUSTOMER_APP_SECRET 未设置[/red]")
            return False
            
        return True
    
    async def setup(self):
        """执行配置流程"""
        console.print(Panel.fit(
            "[bold cyan]飞书Gateway配置工具[/bold cyan]\n"
            "配置并测试飞书机器人连接",
            border_style="cyan"
        ))
        
        # 验证配置
        if not self.validate_config():
            return False
        
        # 显示配置信息
        config_table = Table(title="配置信息")
        config_table.add_column("配置项", style="cyan")
        config_table.add_column("值", style="green")
        
        config_table.add_row("App ID", self.app_id)
        config_table.add_row("App Secret", "***" + self.app_secret[-4:] if len(self.app_secret) > 4 else "***")
        
        console.print(config_table)
        
        try:
            # 获取access token
            console.print("\n[yellow]正在获取访问令牌...[/yellow]")
            token = await self.get_tenant_access_token()
            console.print(f"[green]✓ 访问令牌获取成功[/green]")
            
            # 获取机器人信息
            console.print("\n[yellow]正在获取机器人信息...[/yellow]")
            bot_info = await self.get_bot_info()
            
            bot_table = Table(title="机器人信息")
            bot_table.add_column("属性", style="cyan")
            bot_table.add_column("值", style="green")
            
            bot_table.add_row("机器人名称", bot_info.get("bot", {}).get("name", "N/A"))
            bot_table.add_row("Open ID", bot_info.get("bot", {}).get("open_id", "N/A"))
            bot_table.add_row("激活状态", "已激活" if bot_info.get("bot", {}).get("activate_status") == 1 else "未激活")
            
            console.print(bot_table)
            
            console.print("\n[green]✓ 飞书Gateway配置成功！[/green]")
            return True
            
        except Exception as e:
            console.print(f"\n[red]✗ 配置失败: {str(e)}[/red]")
            return False


async def main():
    """主函数"""
    setup = FeishuGatewaySetup()
    success = await setup.setup()
    
    if success:
        console.print("\n[bold green]配置完成！可以开始使用飞书机器人了。[/bold green]")
        sys.exit(0)
    else:
        console.print("\n[bold red]配置失败，请检查配置后重试。[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
