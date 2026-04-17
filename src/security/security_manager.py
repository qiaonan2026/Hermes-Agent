"""
安全防护管理器
实现提示注入检测、敏感信息过滤和命令审批
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel
from structlog import get_logger

logger = get_logger()


class SecurityAction(str, Enum):
    """安全动作"""
    ALLOW = "allow"
    REJECT = "reject"
    SANITIZE = "sanitize"
    WARN = "warn"


class SecurityCheckResult(BaseModel):
    """安全检查结果"""
    action: SecurityAction
    reason: str
    details: Optional[Dict[str, Any]] = None


class PromptInjectionScanner:
    """提示注入扫描器"""
    
    def __init__(self):
        # 常见的提示注入模式
        self.injection_patterns = [
            r"ignore\s+(previous|all|above)\s+(instructions?|rules?|prompts?)",
            r"disregard\s+(all|above|previous)",
            r"system\s+override",
            r"forget\s+(everything|all|previous)",
            r"new\s+instructions?:",
            r"you\s+are\s+now",
            r"act\s+as\s+if",
            r"pretend\s+(that|to)",
            r"simulate\s+being",
            r"jailbreak",
            r"developer\s+mode",
            r"debug\s+mode"
        ]
        
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.injection_patterns
        ]
        
    def scan(self, text: str) -> SecurityCheckResult:
        """扫描文本"""
        for pattern in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                logger.warning(
                    "检测到提示注入",
                    pattern=pattern.pattern,
                    matched=match.group()
                )
                return SecurityCheckResult(
                    action=SecurityAction.REJECT,
                    reason="检测到提示注入尝试",
                    details={
                        "pattern": pattern.pattern,
                        "matched": match.group(),
                        "position": match.span()
                    }
                )
                
        return SecurityCheckResult(
            action=SecurityAction.ALLOW,
            reason="未检测到提示注入"
        )


class SensitiveDataFilter:
    """敏感数据过滤器"""
    
    def __init__(self):
        # 敏感数据模式
        self.patterns = {
            "email": {
                "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "replacement": "[EMAIL]"
            },
            "phone": {
                "pattern": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                "replacement": "[PHONE]"
            },
            "credit_card": {
                "pattern": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                "replacement": "[CARD]"
            },
            "id_card": {
                "pattern": r'\b\d{17}[\dXx]\b',
                "replacement": "[ID]"
            },
            "api_key": {
                "pattern": r'\b(?:sk-|api[_-]?key[_-]?)[A-Za-z0-9]{20,}\b',
                "replacement": "[API_KEY]"
            },
            "password": {
                "pattern": r'\b(?:password|passwd|pwd)[\s:=]+[^\s]+',
                "replacement": "[PASSWORD]"
            }
        }
        
        self.compiled_patterns = {
            key: re.compile(value["pattern"], re.IGNORECASE)
            for key, value in self.patterns.items()
        }
        
    def filter(self, text: str) -> Tuple[str, Dict[str, int]]:
        """过滤敏感数据"""
        filtered_text = text
        filter_stats = {}
        
        for key, pattern in self.compiled_patterns.items():
            matches = pattern.findall(text)
            if matches:
                filtered_text = pattern.sub(
                    self.patterns[key]["replacement"],
                    filtered_text
                )
                filter_stats[key] = len(matches)
                
        if filter_stats:
            logger.info("过滤敏感数据", stats=filter_stats)
            
        return filtered_text, filter_stats
    
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """检测敏感数据（不过滤）"""
        detections = []
        
        for key, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                detections.append({
                    "type": key,
                    "value": match.group(),
                    "position": match.span()
                })
                
        return detections


class CommandApprovalManager:
    """命令审批管理器"""
    
    def __init__(self):
        # 白名单模式（允许的命令）
        self.whitelist_patterns = [
            r"^query_.*",
            r"^get_.*",
            r"^list_.*",
            r"^search_.*",
            r"^read_.*"
        ]
        
        # 黑名单模式（禁止的命令）
        self.blacklist_patterns = [
            r"^delete_.*",
            r"^remove_.*",
            r"^drop_.*",
            r"^exec_.*",
            r"^eval_.*",
            r"^system_.*",
            r"^shell_.*",
            r"^rm\s+",
            r"^sudo\s+",
            r"^chmod\s+",
            r"^chown\s+"
        ]
        
        self.compiled_whitelist = [
            re.compile(pattern)
            for pattern in self.whitelist_patterns
        ]
        
        self.compiled_blacklist = [
            re.compile(pattern)
            for pattern in self.blacklist_patterns
        ]
        
    def check(self, command: str) -> SecurityCheckResult:
        """检查命令"""
        # 检查黑名单
        for pattern in self.compiled_blacklist:
            if pattern.match(command):
                logger.warning(
                    "命令在黑名单中",
                    command=command,
                    pattern=pattern.pattern
                )
                return SecurityCheckResult(
                    action=SecurityAction.REJECT,
                    reason="命令在黑名单中",
                    details={
                        "pattern": pattern.pattern
                    }
                )
                
        # 检查白名单
        for pattern in self.compiled_whitelist:
            if pattern.match(command):
                return SecurityCheckResult(
                    action=SecurityAction.ALLOW,
                    reason="命令在白名单中"
                )
                
        # 不在白名单也不在黑名单，需要审批
        return SecurityCheckResult(
            action=SecurityAction.WARN,
            reason="命令需要人工审批",
            details={
                "command": command
            }
        )


class SecurityManager:
    """安全防护管理器"""
    
    def __init__(
        self,
        enable_injection_scan: bool = True,
        enable_sensitive_filter: bool = True,
        enable_command_approval: bool = True
    ):
        self.enable_injection_scan = enable_injection_scan
        self.enable_sensitive_filter = enable_sensitive_filter
        self.enable_command_approval = enable_command_approval
        
        self.injection_scanner = PromptInjectionScanner()
        self.sensitive_filter = SensitiveDataFilter()
        self.command_approval = CommandApprovalManager()
        
    def check_input(self, text: str) -> SecurityCheckResult:
        """检查输入"""
        # 提示注入检测
        if self.enable_injection_scan:
            result = self.injection_scanner.scan(text)
            if result.action == SecurityAction.REJECT:
                return result
                
        # 敏感数据检测
        if self.enable_sensitive_filter:
            detections = self.sensitive_filter.detect(text)
            if detections:
                logger.warning("输入包含敏感数据", detections=len(detections))
                # 可以选择拒绝或警告
                return SecurityCheckResult(
                    action=SecurityAction.WARN,
                    reason="输入包含敏感数据",
                    details={
                        "detections": detections
                    }
                )
                
        return SecurityCheckResult(
            action=SecurityAction.ALLOW,
            reason="输入安全"
        )
    
    def sanitize_output(self, text: str) -> str:
        """清理输出"""
        if self.enable_sensitive_filter:
            filtered_text, stats = self.sensitive_filter.filter(text)
            return filtered_text
        return text
    
    def check_command(self, command: str) -> SecurityCheckResult:
        """检查命令"""
        if self.enable_command_approval:
            return self.command_approval.check(command)
        return SecurityCheckResult(
            action=SecurityAction.ALLOW,
            reason="命令审批未启用"
        )
    
    def validate_request(self, request: Dict[str, Any]) -> SecurityCheckResult:
        """验证请求"""
        # 检查所有文本字段
        for key, value in request.items():
            if isinstance(value, str):
                result = self.check_input(value)
                if result.action == SecurityAction.REJECT:
                    return result
                    
        return SecurityCheckResult(
            action=SecurityAction.ALLOW,
            reason="请求安全"
        )
