"""
技能管理器
实现技能的自动生成、优化和审核
"""

import json
import re
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from pathlib import Path
from collections import Counter

from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger()


class Skill(BaseModel):
    """技能模型"""
    skill_id: str
    name: str
    description: str
    pattern: str  # 触发模式（正则表达式）
    template: str  # 回复模板
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 统计信息
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    
    # 优化信息
    last_optimized: Optional[str] = None
    optimization_count: int = 0
    
    # 审核信息
    review_status: str = "pending"  # pending, approved, rejected
    reviewer: Optional[str] = None
    review_notes: Optional[str] = None
    
    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    auto_generated: bool = False


class SkillManager:
    """技能管理器"""
    
    def __init__(
        self,
        skills_path: str = "./workspace/customer_service/skills",
        generation_trigger: int = 15,
        min_occurrences: int = 3,
        similarity_threshold: float = 0.8
    ):
        self.skills_path = Path(skills_path)
        self.skills_path.mkdir(parents=True, exist_ok=True)
        
        self.generation_trigger = generation_trigger
        self.min_occurrences = min_occurrences
        self.similarity_threshold = similarity_threshold
        
        self.skills: Dict[str, Skill] = {}
        self.task_count = 0
        self.pattern_cache: Dict[str, int] = {}  # pattern -> count
        
    def load_skills(self):
        """加载所有技能"""
        skills_file = self.skills_path / "skills.json"
        
        if skills_file.exists():
            with open(skills_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for skill_id, skill_data in data.items():
                    self.skills[skill_id] = Skill(**skill_data)
                    
        logger.info("加载技能", count=len(self.skills))
        
    def save_skills(self):
        """保存所有技能"""
        skills_file = self.skills_path / "skills.json"
        
        data = {
            skill_id: skill.model_dump()
            for skill_id, skill in self.skills.items()
        }
        
        with open(skills_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info("保存技能", count=len(self.skills))
        
    def create_skill(
        self,
        name: str,
        description: str,
        pattern: str,
        template: str,
        parameters: Optional[Dict[str, Any]] = None,
        auto_generated: bool = False
    ) -> Skill:
        """创建技能"""
        # 生成skill_id
        skill_id = self._generate_skill_id(name)
        
        # 创建技能
        skill = Skill(
            skill_id=skill_id,
            name=name,
            description=description,
            pattern=pattern,
            template=template,
            parameters=parameters or {},
            auto_generated=auto_generated
        )
        
        # 保存技能
        self.skills[skill_id] = skill
        self.save_skills()
        
        logger.info("创建技能", skill_id=skill_id, name=name, auto_generated=auto_generated)
        return skill
    
    def _generate_skill_id(self, name: str) -> str:
        """生成技能ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"skill_{name.lower().replace(' ', '_')}_{timestamp}"
    
    def record_task(self, task_pattern: str):
        """记录任务模式"""
        self.task_count += 1
        self.pattern_cache[task_pattern] = self.pattern_cache.get(task_pattern, 0) + 1
        
        # 检查是否触发技能生成
        if self.task_count % self.generation_trigger == 0:
            self._evaluate_skill_generation()
            
    def _evaluate_skill_generation(self):
        """评估是否需要生成新技能"""
        logger.info("评估技能生成", task_count=self.task_count)
        
        # 找出高频模式
        frequent_patterns = {
            pattern: count
            for pattern, count in self.pattern_cache.items()
            if count >= self.min_occurrences
        }
        
        # 检查是否已有对应技能
        for pattern, count in frequent_patterns.items():
            if not self._has_skill_for_pattern(pattern):
                # 生成新技能
                self._generate_skill_from_pattern(pattern, count)
                
    def _has_skill_for_pattern(self, pattern: str) -> bool:
        """检查是否已有对应模式的技能"""
        for skill in self.skills.values():
            try:
                if re.search(skill.pattern, pattern):
                    return True
            except re.error:
                continue
        return False
    
    def _generate_skill_from_pattern(self, pattern: str, count: int):
        """从模式生成技能"""
        # 简单的技能生成逻辑
        # TODO: 实现更复杂的技能生成算法
        
        # 提取关键词
        keywords = self._extract_keywords(pattern)
        
        # 生成技能名称
        name = f"处理{keywords[0] if keywords else '问题'}"
        
        # 生成描述
        description = f"自动生成的技能，用于处理: {pattern}"
        
        # 生成正则模式
        regex_pattern = self._generate_regex_pattern(pattern)
        
        # 生成回复模板
        template = self._generate_template(pattern, keywords)
        
        # 创建技能
        skill = self.create_skill(
            name=name,
            description=description,
            pattern=regex_pattern,
            template=template,
            auto_generated=True
        )
        
        logger.info(
            "自动生成技能",
            skill_id=skill.skill_id,
            pattern=pattern,
            count=count
        )
        
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        # TODO: 使用NLP技术提取关键词
        words = re.findall(r'\w+', text)
        return list(set(words))[:5]
    
    def _generate_regex_pattern(self, text: str) -> str:
        """生成正则表达式模式"""
        # 简单的模式生成
        keywords = self._extract_keywords(text)
        if keywords:
            return '|'.join(keywords)
        return text
    
    def _generate_template(self, pattern: str, keywords: List[str]) -> str:
        """生成回复模板"""
        # 简单的模板生成
        if keywords:
            return f"关于{keywords[0]}的问题，我来为您解答..."
        return "我来为您处理这个问题..."
    
    def match_skill(self, text: str) -> Optional[Skill]:
        """匹配技能"""
        for skill in self.skills.values():
            if skill.review_status != "approved":
                continue
                
            try:
                if re.search(skill.pattern, text):
                    return skill
            except re.error:
                continue
                
        return None
    
    def execute_skill(self, skill: Skill, context: Dict[str, Any]) -> str:
        """执行技能"""
        try:
            # 更新使用统计
            skill.usage_count += 1
            
            # 执行技能模板
            # TODO: 实现更复杂的模板渲染
            result = skill.template
            
            # 更新成功统计
            skill.success_count += 1
            skill.success_rate = skill.success_count / skill.usage_count
            skill.updated_at = datetime.now().isoformat()
            
            self.save_skills()
            
            logger.info("执行技能成功", skill_id=skill.skill_id)
            return result
            
        except Exception as e:
            # 更新失败统计
            skill.failure_count += 1
            skill.success_rate = skill.success_count / skill.usage_count
            skill.updated_at = datetime.now().isoformat()
            
            self.save_skills()
            
            logger.error("执行技能失败", skill_id=skill.skill_id, error=str(e))
            raise
    
    def optimize_skill(self, skill_id: str) -> Skill:
        """优化技能"""
        if skill_id not in self.skills:
            raise ValueError(f"技能不存在: {skill_id}")
            
        skill = self.skills[skill_id]
        
        # 检查是否需要优化
        if skill.success_rate >= 0.8:
            logger.info("技能表现良好，无需优化", skill_id=skill_id)
            return skill
            
        # 优化逻辑
        # TODO: 实现更复杂的优化算法
        
        # 更新优化信息
        skill.last_optimized = datetime.now().isoformat()
        skill.optimization_count += 1
        skill.updated_at = datetime.now().isoformat()
        
        self.save_skills()
        
        logger.info("优化技能", skill_id=skill_id, optimization_count=skill.optimization_count)
        return skill
    
    def review_skill(
        self,
        skill_id: str,
        status: str,
        reviewer: str,
        notes: Optional[str] = None
    ):
        """审核技能"""
        if skill_id not in self.skills:
            raise ValueError(f"技能不存在: {skill_id}")
            
        skill = self.skills[skill_id]
        
        skill.review_status = status
        skill.reviewer = reviewer
        skill.review_notes = notes
        skill.updated_at = datetime.now().isoformat()
        
        self.save_skills()
        
        logger.info("审核技能", skill_id=skill_id, status=status, reviewer=reviewer)
    
    def delete_skill(self, skill_id: str):
        """删除技能"""
        if skill_id not in self.skills:
            return
            
        del self.skills[skill_id]
        self.save_skills()
        
        logger.info("删除技能", skill_id=skill_id)
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(skill_id)
    
    def list_skills(self, status: Optional[str] = None) -> List[Skill]:
        """列出技能"""
        skills = list(self.skills.values())
        
        if status:
            skills = [s for s in skills if s.review_status == status]
            
        return skills
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.skills)
        approved = len([s for s in self.skills.values() if s.review_status == "approved"])
        pending = len([s for s in self.skills.values() if s.review_status == "pending"])
        auto_generated = len([s for s in self.skills.values() if s.auto_generated])
        
        return {
            "total_skills": total,
            "approved_skills": approved,
            "pending_skills": pending,
            "auto_generated_skills": auto_generated,
            "task_count": self.task_count
        }
