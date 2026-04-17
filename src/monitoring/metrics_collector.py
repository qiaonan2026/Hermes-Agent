"""
监控指标收集器
实现Prometheus指标导出和监控
"""

import time
from typing import Dict, Any, Optional
from collections import defaultdict
from datetime import datetime

from prometheus_client import Counter, Histogram, Gauge, Info
from structlog import get_logger

logger = get_logger()


class MetricsCollector:
    """监控指标收集器"""
    
    def __init__(self, port: int = 9090):
        self.port = port
        
        # 定义指标
        self._setup_metrics()
        
        # 统计数据
        self.stats = defaultdict(int)
        self.start_time = time.time()
        
    def _setup_metrics(self):
        """设置Prometheus指标"""
        # 计数器
        self.message_total = Counter(
            'hermes_message_total',
            'Total number of messages processed',
            ['gateway', 'status']
        )
        
        self.skill_execution_total = Counter(
            'hermes_skill_execution_total',
            'Total number of skill executions',
            ['skill_id', 'status']
        )
        
        self.customer_interaction_total = Counter(
            'hermes_customer_interaction_total',
            'Total number of customer interactions',
            ['customer_id', 'outcome']
        )
        
        # 直方图
        self.response_time = Histogram(
            'hermes_response_time_seconds',
            'Response time in seconds',
            ['gateway'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.skill_execution_time = Histogram(
            'hermes_skill_execution_time_seconds',
            'Skill execution time in seconds',
            ['skill_id'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        # 仪表盘
        self.active_sessions = Gauge(
            'hermes_active_sessions',
            'Number of active sessions'
        )
        
        self.skill_success_rate = Gauge(
            'hermes_skill_success_rate',
            'Skill success rate',
            ['skill_id']
        )
        
        self.customer_satisfaction = Gauge(
            'hermes_customer_satisfaction',
            'Customer satisfaction score',
            ['customer_id']
        )
        
        # 信息
        self.system_info = Info(
            'hermes_system',
            'System information'
        )
        self.system_info.info({
            'version': '0.1.0',
            'profile': 'customer_service'
        })
        
    def record_message(self, gateway: str, status: str = "success"):
        """记录消息"""
        self.message_total.labels(gateway=gateway, status=status).inc()
        self.stats['total_messages'] += 1
        
    def record_response_time(self, gateway: str, duration: float):
        """记录响应时间"""
        self.response_time.labels(gateway=gateway).observe(duration)
        
    def record_skill_execution(
        self,
        skill_id: str,
        status: str = "success",
        duration: Optional[float] = None
    ):
        """记录技能执行"""
        self.skill_execution_total.labels(skill_id=skill_id, status=status).inc()
        
        if duration:
            self.skill_execution_time.labels(skill_id=skill_id).observe(duration)
            
        self.stats['total_skill_executions'] += 1
        
    def update_skill_success_rate(self, skill_id: str, rate: float):
        """更新技能成功率"""
        self.skill_success_rate.labels(skill_id=skill_id).set(rate)
        
    def record_customer_interaction(
        self,
        customer_id: str,
        outcome: str = "success"
    ):
        """记录客户交互"""
        self.customer_interaction_total.labels(
            customer_id=customer_id,
            outcome=outcome
        ).inc()
        self.stats['total_interactions'] += 1
        
    def update_customer_satisfaction(self, customer_id: str, score: float):
        """更新客户满意度"""
        self.customer_satisfaction.labels(customer_id=customer_id).set(score)
        
    def set_active_sessions(self, count: int):
        """设置活动会话数"""
        self.active_sessions.set(count)
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "uptime_hours": uptime / 3600,
            "total_messages": self.stats['total_messages'],
            "total_skill_executions": self.stats['total_skill_executions'],
            "total_interactions": self.stats['total_interactions'],
            "messages_per_hour": self.stats['total_messages'] / (uptime / 3600) if uptime > 0 else 0
        }
    
    def start_server(self):
        """启动Prometheus服务器"""
        from prometheus_client import start_http_server
        start_http_server(self.port)
        logger.info("Prometheus指标服务器启动", port=self.port)


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alert_rules = []
        self.active_alerts = {}
        
    def add_rule(
        self,
        name: str,
        metric: str,
        threshold: float,
        severity: str = "warning",
        comparison: str = "greater"
    ):
        """添加告警规则"""
        rule = {
            "name": name,
            "metric": metric,
            "threshold": threshold,
            "severity": severity,
            "comparison": comparison
        }
        self.alert_rules.append(rule)
        logger.info("添加告警规则", name=name, metric=metric)
        
    def check_alerts(self, metrics: Dict[str, float]):
        """检查告警"""
        for rule in self.alert_rules:
            metric_value = metrics.get(rule["metric"])
            
            if metric_value is None:
                continue
                
            # 检查是否触发告警
            triggered = False
            if rule["comparison"] == "greater":
                triggered = metric_value > rule["threshold"]
            elif rule["comparison"] == "less":
                triggered = metric_value < rule["threshold"]
                
            if triggered:
                alert_id = f"{rule['name']}_{rule['metric']}"
                
                if alert_id not in self.active_alerts:
                    self.active_alerts[alert_id] = {
                        "rule": rule,
                        "value": metric_value,
                        "triggered_at": datetime.now().isoformat()
                    }
                    
                    logger.warning(
                        "告警触发",
                        name=rule["name"],
                        metric=rule["metric"],
                        value=metric_value,
                        threshold=rule["threshold"],
                        severity=rule["severity"]
                    )
            else:
                # 清除告警
                alert_id = f"{rule['name']}_{rule['metric']}"
                if alert_id in self.active_alerts:
                    del self.active_alerts[alert_id]
                    logger.info("告警清除", name=rule["name"])
                    
    def get_active_alerts(self) -> Dict[str, Any]:
        """获取活动告警"""
        return self.active_alerts
