"""
飞书Gateway实现
处理飞书消息的接收和发送
"""

import asyncio
import json
import hashlib
import hmac
from typing import Dict, Any, Optional, Callable
from datetime import datetime

import httpx
from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger()


class FeishuMessage(BaseModel):
    """飞书消息模型"""
    message_id: str
    root_id: Optional[str] = None
    parent_id: Optional[str] = None
    create_time: str
    chat_id: str
    chat_type: str
    msg_type: str
    content: str
    mentions: Optional[list] = None
    sender: Dict[str, Any]
    

class FeishuEvent(BaseModel):
    """飞书事件模型"""
    event_id: str
    token: Optional[str] = None
    create_time: str
    event_type: str
    event: Dict[str, Any]
    

class FeishuGateway:
    """飞书Gateway类"""
    
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        encrypt_key: Optional[str] = None,
        verification_token: Optional[str] = None
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.encrypt_key = encrypt_key
        self.verification_token = verification_token
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
        self.token_expire_time = 0
        self.message_handler: Optional[Callable] = None
        
    async def get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        # 检查token是否过期
        if self.access_token and datetime.now().timestamp() < self.token_expire_time:
            return self.access_token
            
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
                # 设置过期时间（提前5分钟刷新）
                expire = result.get("expire", 7200)
                self.token_expire_time = datetime.now().timestamp() + expire - 300
                logger.info("获取飞书访问令牌成功")
                return self.access_token
            else:
                logger.error("获取飞书访问令牌失败", error=result.get("msg"))
                raise Exception(f"获取token失败: {result.get('msg')}")
    
    def verify_signature(self, timestamp: str, nonce: str, signature: str, body: str) -> bool:
        """验证签名"""
        if not self.encrypt_key:
            return True
            
        # 构造签名字符串
        sign_base = f"{timestamp}{nonce}{self.encrypt_key}{body}"
        
        # 计算签名
        calculated_signature = hashlib.sha256(sign_base.encode()).hexdigest()
        
        return calculated_signature == signature
    
    async def handle_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理飞书事件"""
        try:
            event = FeishuEvent(**event_data)
            
            # 验证token
            if self.verification_token and event.token != self.verification_token:
                logger.warning("事件token验证失败")
                return {"code": 1, "msg": "token验证失败"}
            
            # 处理不同类型的事件
            if event.event_type == "im.message.receive_v1":
                return await self._handle_message_event(event.event)
            else:
                logger.info("收到未处理的事件类型", event_type=event.event_type)
                return {"code": 0, "msg": "success"}
                
        except Exception as e:
            logger.error("处理飞书事件失败", error=str(e))
            return {"code": 1, "msg": str(e)}
    
    async def _handle_message_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """处理消息事件"""
        try:
            message = FeishuMessage(**event.get("message", {}))
            
            logger.info(
                "收到飞书消息",
                message_id=message.message_id,
                chat_id=message.chat_id,
                msg_type=message.msg_type,
                sender=message.sender.get("sender_id", {}).get("open_id")
            )
            
            # 调用消息处理器
            if self.message_handler:
                response = await self.message_handler(message)
                
                # 如果有回复，发送回复消息
                if response:
                    await self.send_message(
                        receive_id=message.chat_id,
                        receive_id_type="chat_id",
                        msg_type="text",
                        content=response
                    )
            
            return {"code": 0, "msg": "success"}
            
        except Exception as e:
            logger.error("处理消息事件失败", error=str(e))
            return {"code": 1, "msg": str(e)}
    
    async def send_message(
        self,
        receive_id: str,
        receive_id_type: str,
        msg_type: str,
        content: str,
        reply_to_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送消息"""
        if not self.access_token:
            await self.get_tenant_access_token()
            
        url = f"{self.base_url}/im/v1/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "receive_id_type": receive_id_type
        }
        
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content
        }
        
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, params=params, json=payload)
            result = response.json()
            
            if result.get("code") == 0:
                logger.info("发送飞书消息成功", receive_id=receive_id)
                return result.get("data", {})
            else:
                logger.error("发送飞书消息失败", error=result.get("msg"))
                raise Exception(f"发送消息失败: {result.get('msg')}")
    
    def set_message_handler(self, handler: Callable):
        """设置消息处理器"""
        self.message_handler = handler
        
    async def get_user_info(self, open_id: str) -> Dict[str, Any]:
        """获取用户信息"""
        if not self.access_token:
            await self.get_tenant_access_token()
            
        url = f"{self.base_url}/contact/v3/users/{open_id}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        params = {
            "user_id_type": "open_id"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get("code") == 0:
                return result.get("data", {}).get("user", {})
            else:
                logger.error("获取用户信息失败", error=result.get("msg"))
                raise Exception(f"获取用户信息失败: {result.get('msg')}")
    
    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        if not self.access_token:
            await self.get_tenant_access_token()
            
        url = f"{self.base_url}/im/v1/chats/{chat_id}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            result = response.json()
            
            if result.get("code") == 0:
                return result.get("data", {})
            else:
                logger.error("获取会话信息失败", error=result.get("msg"))
                raise Exception(f"获取会话信息失败: {result.get('msg')}")
