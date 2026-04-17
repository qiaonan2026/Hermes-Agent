"""
Memory Fence隔离管理器
实现客户数据隔离和访问控制
"""

import hashlib
from typing import Dict, Any, Optional, Set
from datetime import datetime

from pydantic import BaseModel
from structlog import get_logger

logger = get_logger()


class MemoryFence(BaseModel):
    """Memory Fence模型"""
    fence_id: str
    tags: Set[str]
    owner_id: str
    created_at: str = datetime.now().isoformat()


class MemoryFenceManager:
    """Memory Fence隔离管理器"""
    
    def __init__(self):
        self.fences: Dict[str, MemoryFence] = {}  # fence_id -> MemoryFence
        self.tag_index: Dict[str, Set[str]] = {}  # tag -> set of fence_ids
        self.owner_index: Dict[str, Set[str]] = {}  # owner_id -> set of fence_ids
        
    def create_fence(
        self,
        owner_id: str,
        tags: Set[str],
        fence_id: Optional[str] = None
    ) -> MemoryFence:
        """创建Memory Fence"""
        # 生成fence_id
        if not fence_id:
            fence_id = self._generate_fence_id(owner_id, tags)
            
        # 创建fence
        fence = MemoryFence(
            fence_id=fence_id,
            tags=tags,
            owner_id=owner_id
        )
        
        # 保存fence
        self.fences[fence_id] = fence
        
        # 更新索引
        for tag in tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(fence_id)
            
        if owner_id not in self.owner_index:
            self.owner_index[owner_id] = set()
        self.owner_index[owner_id].add(fence_id)
        
        logger.info("创建Memory Fence", fence_id=fence_id, owner_id=owner_id, tags=tags)
        return fence
    
    def _generate_fence_id(self, owner_id: str, tags: Set[str]) -> str:
        """生成fence_id"""
        content = f"{owner_id}:{':'.join(sorted(tags))}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_fence(self, fence_id: str) -> Optional[MemoryFence]:
        """获取Memory Fence"""
        return self.fences.get(fence_id)
    
    def get_fences_by_owner(self, owner_id: str) -> Set[str]:
        """获取所有者的所有fence"""
        return self.owner_index.get(owner_id, set())
    
    def get_fences_by_tag(self, tag: str) -> Set[str]:
        """获取包含特定标签的所有fence"""
        return self.tag_index.get(tag, set())
    
    def check_access(
        self,
        fence_id: str,
        accessor_id: str,
        required_tags: Optional[Set[str]] = None
    ) -> bool:
        """检查访问权限"""
        fence = self.fences.get(fence_id)
        
        if not fence:
            logger.warning("Fence不存在", fence_id=fence_id)
            return False
            
        # 检查所有者权限
        if fence.owner_id == accessor_id:
            return True
            
        # 检查标签权限
        if required_tags:
            if not required_tags.issubset(fence.tags):
                logger.warning(
                    "标签权限不足",
                    fence_id=fence_id,
                    required=required_tags,
                    actual=fence.tags
                )
                return False
                
        # 默认拒绝访问
        logger.warning(
            "访问被拒绝",
            fence_id=fence_id,
            accessor_id=accessor_id
        )
        return False
    
    def validate_isolation(
        self,
        source_fence_id: str,
        target_fence_id: str
    ) -> bool:
        """验证隔离性"""
        source_fence = self.fences.get(source_fence_id)
        target_fence = self.fences.get(target_fence_id)
        
        if not source_fence or not target_fence:
            return False
            
        # 检查是否为同一所有者
        if source_fence.owner_id != target_fence.owner_id:
            logger.warning(
                "跨所有者访问被阻止",
                source_owner=source_fence.owner_id,
                target_owner=target_fence.owner_id
            )
            return False
            
        # 检查标签交集
        tag_intersection = source_fence.tags & target_fence.tags
        if not tag_intersection:
            logger.warning(
                "无共同标签，访问被阻止",
                source_tags=source_fence.tags,
                target_tags=target_fence.tags
            )
            return False
            
        return True
    
    def add_tags(self, fence_id: str, new_tags: Set[str]):
        """添加标签"""
        fence = self.fences.get(fence_id)
        
        if not fence:
            raise ValueError(f"Fence不存在: {fence_id}")
            
        # 添加标签
        fence.tags.update(new_tags)
        
        # 更新索引
        for tag in new_tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(fence_id)
            
        logger.info("添加标签", fence_id=fence_id, new_tags=new_tags)
    
    def remove_tags(self, fence_id: str, tags_to_remove: Set[str]):
        """移除标签"""
        fence = self.fences.get(fence_id)
        
        if not fence:
            raise ValueError(f"Fence不存在: {fence_id}")
            
        # 移除标签
        fence.tags -= tags_to_remove
        
        # 更新索引
        for tag in tags_to_remove:
            if tag in self.tag_index:
                self.tag_index[tag].discard(fence_id)
                
        logger.info("移除标签", fence_id=fence_id, tags_to_remove=tags_to_remove)
    
    def delete_fence(self, fence_id: str):
        """删除Memory Fence"""
        fence = self.fences.get(fence_id)
        
        if not fence:
            return
            
        # 从索引中移除
        for tag in fence.tags:
            if tag in self.tag_index:
                self.tag_index[tag].discard(fence_id)
                
        if fence.owner_id in self.owner_index:
            self.owner_index[fence.owner_id].discard(fence_id)
            
        # 删除fence
        del self.fences[fence_id]
        
        logger.info("删除Memory Fence", fence_id=fence_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_fences": len(self.fences),
            "total_tags": len(self.tag_index),
            "total_owners": len(self.owner_index)
        }
    
    def list_fences(self) -> Dict[str, Dict[str, Any]]:
        """列出所有fence"""
        return {
            fence_id: {
                "owner_id": fence.owner_id,
                "tags": list(fence.tags),
                "created_at": fence.created_at
            }
            for fence_id, fence in self.fences.items()
        }
