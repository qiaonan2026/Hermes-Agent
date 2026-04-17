"""
Honcho用户建模客户端
实现客户画像建模和跨会话记忆管理
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger()


class CustomerProfile(BaseModel):
    """客户画像模型"""
    customer_id: str
    open_id: str  # 飞书Open ID
    
    # 基本信息
    name: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    
    # 使用信息
    products: List[str] = Field(default_factory=list)
    subscription_level: Optional[str] = None
    registration_date: Optional[str] = None
    
    # 行为特征
    activity_level: str = "low"  # low, medium, high
    usage_frequency: str = "low"  # low, medium, high
    preferred_features: List[str] = Field(default_factory=list)
    consultation_frequency: int = 0
    
    # 偏好设置
    preferred_channel: str = "feishu"  # feishu, email, phone
    response_style: str = "detailed"  # detailed, concise
    preferred_contact_time: str = "work_hours"  # work_hours, anytime
    language_preference: str = "zh"  # zh, en
    
    # 历史记录
    total_consultations: int = 0
    resolved_issues: int = 0
    satisfaction_score: float = 0.0
    complaint_count: int = 0
    
    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # 辩证式理解
    dialectical_notes: List[Dict[str, Any]] = Field(default_factory=list)


class HonchoClient:
    """Honcho用户建模客户端"""
    
    def __init__(self, storage_path: str = "./data/honcho"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, CustomerProfile] = {}
        
    def load_profiles(self):
        """加载所有客户画像"""
        profiles_file = self.storage_path / "profiles.json"
        
        if profiles_file.exists():
            with open(profiles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for customer_id, profile_data in data.items():
                    self.profiles[customer_id] = CustomerProfile(**profile_data)
                    
        logger.info("加载客户画像", count=len(self.profiles))
        
    def save_profiles(self):
        """保存所有客户画像"""
        profiles_file = self.storage_path / "profiles.json"
        
        data = {
            customer_id: profile.model_dump()
            for customer_id, profile in self.profiles.items()
        }
        
        with open(profiles_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info("保存客户画像", count=len(self.profiles))
        
    def get_or_create_profile(self, customer_id: str, open_id: str) -> CustomerProfile:
        """获取或创建客户画像"""
        if customer_id not in self.profiles:
            profile = CustomerProfile(
                customer_id=customer_id,
                open_id=open_id
            )
            self.profiles[customer_id] = profile
            logger.info("创建新客户画像", customer_id=customer_id)
            
        return self.profiles[customer_id]
    
    def update_profile(self, customer_id: str, updates: Dict[str, Any]) -> CustomerProfile:
        """更新客户画像"""
        if customer_id not in self.profiles:
            raise ValueError(f"客户画像不存在: {customer_id}")
            
        profile = self.profiles[customer_id]
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
                
        # 更新时间戳
        profile.updated_at = datetime.now().isoformat()
        
        logger.info("更新客户画像", customer_id=customer_id, updates=list(updates.keys()))
        return profile
    
    def add_dialectical_note(
        self,
        customer_id: str,
        note_type: str,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """添加辩证式理解笔记"""
        if customer_id not in self.profiles:
            raise ValueError(f"客户画像不存在: {customer_id}")
            
        profile = self.profiles[customer_id]
        
        note = {
            "type": note_type,
            "content": content,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        profile.dialectical_notes.append(note)
        profile.updated_at = datetime.now().isoformat()
        
        logger.info("添加辩证式笔记", customer_id=customer_id, note_type=note_type)
        
    def extract_preferences(self, customer_id: str, conversation_history: List[Dict[str, Any]]):
        """从对话历史中提取客户偏好"""
        if customer_id not in self.profiles:
            raise ValueError(f"客户画像不存在: {customer_id}")
            
        profile = self.profiles[customer_id]
        
        # 分析对话历史，提取偏好
        # TODO: 实现更复杂的偏好提取逻辑
        
        # 简单示例：统计咨询频率
        profile.total_consultations += len(conversation_history)
        profile.consultation_frequency = profile.total_consultations
        
        # 更新活跃度
        if profile.total_consultations > 50:
            profile.activity_level = "high"
        elif profile.total_consultations > 20:
            profile.activity_level = "medium"
        else:
            profile.activity_level = "low"
            
        profile.updated_at = datetime.now().isoformat()
        
        logger.info("提取客户偏好", customer_id=customer_id)
        
    def get_cross_session_memory(self, customer_id: str) -> Dict[str, Any]:
        """获取跨会话记忆"""
        if customer_id not in self.profiles:
            return {}
            
        profile = self.profiles[customer_id]
        
        # 构建跨会话记忆摘要
        memory = {
            "customer_info": {
                "name": profile.name,
                "company": profile.company,
                "products": profile.products,
                "subscription_level": profile.subscription_level
            },
            "preferences": {
                "response_style": profile.response_style,
                "language_preference": profile.language_preference,
                "preferred_features": profile.preferred_features
            },
            "history": {
                "total_consultations": profile.total_consultations,
                "satisfaction_score": profile.satisfaction_score,
                "complaint_count": profile.complaint_count
            },
            "recent_notes": profile.dialectical_notes[-5:] if profile.dialectical_notes else []
        }
        
        return memory
    
    def calculate_satisfaction(self, customer_id: str, ratings: List[float]) -> float:
        """计算客户满意度"""
        if not ratings:
            return 0.0
            
        avg_rating = sum(ratings) / len(ratings)
        
        if customer_id in self.profiles:
            profile = self.profiles[customer_id]
            # 使用移动平均更新满意度
            if profile.satisfaction_score == 0:
                profile.satisfaction_score = avg_rating
            else:
                profile.satisfaction_score = 0.7 * profile.satisfaction_score + 0.3 * avg_rating
            profile.updated_at = datetime.now().isoformat()
            
        return avg_rating
