"""
Atropos RL训练环境客户端
实现强化学习训练和轨迹数据收集
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import random

from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger()


class Trajectory(BaseModel):
    """对话轨迹模型"""
    trajectory_id: str
    session_id: str
    customer_id: str
    
    # 交互序列
    interactions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 结果标签
    outcome: str = "unknown"  # success, failure, escalation
    satisfaction_score: Optional[float] = None
    resolution_time: Optional[float] = None  # 秒
    
    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    anonymized: bool = False


class RLState(BaseModel):
    """强化学习状态"""
    customer_sentiment: float = 0.5  # 0-1
    issue_complexity: float = 0.5  # 0-1
    conversation_length: int = 0
    previous_success_rate: float = 0.5


class RLAction(BaseModel):
    """强化学习动作"""
    action_type: str  # reply, escalate, ask_clarification
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AtroposClient:
    """Atropos RL训练环境客户端"""
    
    def __init__(
        self,
        export_path: str = "./data/trajectories",
        anonymize: bool = True
    ):
        self.export_path = Path(export_path)
        self.export_path.mkdir(parents=True, exist_ok=True)
        
        self.anonymize = anonymize
        self.trajectories: Dict[str, Trajectory] = {}
        self.current_trajectory: Optional[Trajectory] = None
        
        # RL参数
        self.learning_rate = 0.001
        self.discount_factor = 0.95
        self.exploration_rate = 0.1
        
        # Q表（简化版）
        self.q_table: Dict[str, Dict[str, float]] = {}
        
    def start_trajectory(self, session_id: str, customer_id: str) -> Trajectory:
        """开始新的轨迹"""
        trajectory_id = self._generate_trajectory_id(session_id)
        
        trajectory = Trajectory(
            trajectory_id=trajectory_id,
            session_id=session_id,
            customer_id=customer_id
        )
        
        self.trajectories[trajectory_id] = trajectory
        self.current_trajectory = trajectory
        
        logger.info("开始新轨迹", trajectory_id=trajectory_id, session_id=session_id)
        return trajectory
    
    def _generate_trajectory_id(self, session_id: str) -> str:
        """生成轨迹ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"traj_{session_id}_{timestamp}"
    
    def add_interaction(
        self,
        user_message: str,
        agent_response: str,
        action: str,
        reward: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """添加交互"""
        if not self.current_trajectory:
            raise ValueError("没有活动的轨迹")
            
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "agent_response": agent_response,
            "action": action,
            "reward": reward,
            "metadata": metadata or {}
        }
        
        self.current_trajectory.interactions.append(interaction)
        
        logger.info("添加交互", trajectory_id=self.current_trajectory.trajectory_id)
    
    def end_trajectory(
        self,
        outcome: str,
        satisfaction_score: Optional[float] = None
    ):
        """结束轨迹"""
        if not self.current_trajectory:
            return
            
        # 计算解决时间
        if self.current_trajectory.interactions:
            start_time = datetime.fromisoformat(self.current_trajectory.interactions[0]["timestamp"])
            end_time = datetime.now()
            resolution_time = (end_time - start_time).total_seconds()
            self.current_trajectory.resolution_time = resolution_time
            
        # 设置结果
        self.current_trajectory.outcome = outcome
        self.current_trajectory.satisfaction_score = satisfaction_score
        
        # 导出轨迹
        self._export_trajectory(self.current_trajectory)
        
        logger.info(
            "结束轨迹",
            trajectory_id=self.current_trajectory.trajectory_id,
            outcome=outcome,
            satisfaction_score=satisfaction_score
        )
        
        self.current_trajectory = None
    
    def _export_trajectory(self, trajectory: Trajectory):
        """导出轨迹"""
        # 数据脱敏
        if self.anonymize:
            trajectory = self._anonymize_trajectory(trajectory)
            
        # 保存到文件
        export_file = self.export_path / f"{trajectory.trajectory_id}.json"
        
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(trajectory.model_dump(), f, ensure_ascii=False, indent=2)
            
        logger.info("导出轨迹", file=str(export_file))
    
    def _anonymize_trajectory(self, trajectory: Trajectory) -> Trajectory:
        """脱敏轨迹数据"""
        # 简单的脱敏逻辑
        # TODO: 实现更完善的脱敏算法
        
        anonymized_interactions = []
        for interaction in trajectory.interactions:
            anonymized_interaction = interaction.copy()
            
            # 脱敏用户消息
            anonymized_interaction["user_message"] = self._anonymize_text(
                interaction["user_message"]
            )
            
            anonymized_interactions.append(anonymized_interaction)
            
        trajectory.interactions = anonymized_interactions
        trajectory.anonymized = True
        
        return trajectory
    
    def _anonymize_text(self, text: str) -> str:
        """脱敏文本"""
        import re
        
        # 脱敏邮箱
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL]',
            text
        )
        
        # 脱敏手机号
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        
        # 脱敏姓名（简单规则）
        text = re.sub(r'我叫(\w+)', r'我叫[NAME]', text)
        
        return text
    
    def get_state(self, context: Dict[str, Any]) -> RLState:
        """获取当前状态"""
        state = RLState(
            customer_sentiment=context.get("sentiment", 0.5),
            issue_complexity=context.get("complexity", 0.5),
            conversation_length=context.get("conversation_length", 0),
            previous_success_rate=context.get("success_rate", 0.5)
        )
        
        return state
    
    def select_action(self, state: RLState) -> RLAction:
        """选择动作（ε-贪婪策略）"""
        state_key = self._state_to_key(state)
        
        # 探索
        if random.random() < self.exploration_rate:
            action_type = random.choice(["reply", "escalate", "ask_clarification"])
            logger.info("探索动作", action=action_type)
        else:
            # 利用
            if state_key in self.q_table:
                # 选择Q值最大的动作
                action_type = max(self.q_table[state_key], key=self.q_table[state_key].get)
            else:
                action_type = "reply"
                
        return RLAction(action_type=action_type)
    
    def _state_to_key(self, state: RLState) -> str:
        """状态转换为键"""
        return f"{state.customer_sentiment:.2f}_{state.issue_complexity:.2f}_{state.conversation_length}"
    
    def update_q_value(
        self,
        state: RLState,
        action: RLAction,
        reward: float,
        next_state: RLState
    ):
        """更新Q值"""
        state_key = self._state_to_key(state)
        action_key = action.action_type
        next_state_key = self._state_to_key(next_state)
        
        # 初始化Q表
        if state_key not in self.q_table:
            self.q_table[state_key] = {
                "reply": 0.0,
                "escalate": 0.0,
                "ask_clarification": 0.0
            }
            
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = {
                "reply": 0.0,
                "escalate": 0.0,
                "ask_clarification": 0.0
            }
            
        # Q-learning更新
        current_q = self.q_table[state_key][action_key]
        max_next_q = max(self.q_table[next_state_key].values())
        
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[state_key][action_key] = new_q
        
        logger.info(
            "更新Q值",
            state=state_key,
            action=action_key,
            old_q=current_q,
            new_q=new_q
        )
    
    def calculate_reward(
        self,
        outcome: str,
        satisfaction_score: Optional[float] = None,
        resolution_time: Optional[float] = None
    ) -> float:
        """计算奖励"""
        reward = 0.0
        
        # 基于结果的奖励
        if outcome == "success":
            reward += 1.0
        elif outcome == "escalation":
            reward += 0.5
        elif outcome == "failure":
            reward -= 1.0
            
        # 基于满意度的奖励
        if satisfaction_score is not None:
            reward += (satisfaction_score - 3.0) / 2.0  # 归一化到[-1, 1]
            
        # 基于解决时间的奖励
        if resolution_time is not None:
            # 时间越短奖励越高
            if resolution_time < 60:  # 1分钟内
                reward += 0.5
            elif resolution_time < 300:  # 5分钟内
                reward += 0.2
            elif resolution_time > 600:  # 超过10分钟
                reward -= 0.3
                
        return reward
    
    def export_training_data(self) -> str:
        """导出训练数据"""
        export_file = self.export_path / f"training_data_{datetime.now().strftime('%Y%m%d%H%M%S')}.jsonl"
        
        with open(export_file, 'w', encoding='utf-8') as f:
            for trajectory in self.trajectories.values():
                f.write(json.dumps(trajectory.model_dump(), ensure_ascii=False) + "\n")
                
        logger.info("导出训练数据", file=str(export_file), count=len(self.trajectories))
        return str(export_file)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.trajectories)
        success = len([t for t in self.trajectories.values() if t.outcome == "success"])
        failure = len([t for t in self.trajectories.values() if t.outcome == "failure"])
        escalation = len([t for t in self.trajectories.values() if t.outcome == "escalation"])
        
        avg_satisfaction = 0.0
        satisfaction_scores = [t.satisfaction_score for t in self.trajectories.values() if t.satisfaction_score]
        if satisfaction_scores:
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)
            
        return {
            "total_trajectories": total,
            "success_count": success,
            "failure_count": failure,
            "escalation_count": escalation,
            "success_rate": success / total if total > 0 else 0,
            "average_satisfaction": avg_satisfaction
        }
