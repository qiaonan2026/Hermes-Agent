"""
Docker沙箱管理器
实现安全隔离的命令执行环境
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger()


class SandboxExecution(BaseModel):
    """沙箱执行模型"""
    execution_id: str
    command: str
    status: str = "pending"  # pending, running, completed, failed, timeout
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class SandboxManager:
    """Docker沙箱管理器"""
    
    def __init__(
        self,
        image: str = "python:3.11-slim",
        cpu_limit: float = 1.0,
        memory_limit: int = 512,  # MB
        network_enabled: bool = False,
        timeout: int = 30
    ):
        self.image = image
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.network_enabled = network_enabled
        self.timeout = timeout
        
        self.active_executions: Dict[str, SandboxExecution] = {}
        
    async def execute(
        self,
        command: str,
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, str]] = None
    ) -> SandboxExecution:
        """在沙箱中执行命令"""
        # 生成执行ID
        execution_id = self._generate_execution_id()
        
        # 创建执行记录
        execution = SandboxExecution(
            execution_id=execution_id,
            command=command
        )
        
        self.active_executions[execution_id] = execution
        execution.status = "running"
        execution.started_at = datetime.now().isoformat()
        
        try:
            # 构建Docker命令
            docker_cmd = self._build_docker_command(command, environment, volumes)
            
            # 执行命令
            result = await self._run_command(docker_cmd)
            
            execution.stdout = result["stdout"]
            execution.stderr = result["stderr"]
            execution.exit_code = result["exit_code"]
            execution.execution_time = result["execution_time"]
            
            if result["exit_code"] == 0:
                execution.status = "completed"
            else:
                execution.status = "failed"
                
            execution.completed_at = datetime.now().isoformat()
            
            logger.info(
                "沙箱执行完成",
                execution_id=execution_id,
                status=execution.status,
                exit_code=execution.exit_code
            )
            
        except asyncio.TimeoutError:
            execution.status = "timeout"
            execution.completed_at = datetime.now().isoformat()
            logger.error("沙箱执行超时", execution_id=execution_id)
            
        except Exception as e:
            execution.status = "failed"
            execution.stderr = str(e)
            execution.completed_at = datetime.now().isoformat()
            logger.error("沙箱执行失败", execution_id=execution_id, error=str(e))
            
        finally:
            del self.active_executions[execution_id]
            
        return execution
    
    def _generate_execution_id(self) -> str:
        """生成执行ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"exec_{timestamp}"
    
    def _build_docker_command(
        self,
        command: str,
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """构建Docker命令"""
        docker_cmd = [
            "docker", "run",
            "--rm",  # 自动删除容器
            f"--cpus={self.cpu_limit}",
            f"--memory={self.memory_limit}m",
            "--timeout=" + str(self.timeout)
        ]
        
        # 网络设置
        if not self.network_enabled:
            docker_cmd.append("--network=none")
            
        # 环境变量
        if environment:
            for key, value in environment.items():
                docker_cmd.extend(["-e", f"{key}={value}"])
                
        # 卷挂载
        if volumes:
            for host_path, container_path in volumes.items():
                docker_cmd.extend(["-v", f"{host_path}:{container_path}"])
                
        # 镜像和命令
        docker_cmd.append(self.image)
        docker_cmd.extend(["sh", "-c", command])
        
        return docker_cmd
    
    async def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """运行命令"""
        start_time = datetime.now()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8'),
                "exit_code": process.returncode,
                "execution_time": execution_time
            }
            
        except asyncio.TimeoutError:
            # 杀死进程
            try:
                process.kill()
            except:
                pass
            raise
    
    async def execute_python(
        self,
        code: str,
        environment: Optional[Dict[str, str]] = None
    ) -> SandboxExecution:
        """执行Python代码"""
        # 转义代码
        escaped_code = code.replace('"', '\\"').replace('$', '\\$')
        
        command = f'python3 -c "{escaped_code}"'
        
        return await self.execute(command, environment)
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            execution = await self.execute("echo 'health_check'")
            return execution.status == "completed" and execution.exit_code == 0
        except Exception as e:
            logger.error("沙箱健康检查失败", error=str(e))
            return False
    
    def get_active_executions(self) -> List[SandboxExecution]:
        """获取活动执行"""
        return list(self.active_executions.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "image": self.image,
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
            "network_enabled": self.network_enabled,
            "timeout": self.timeout,
            "active_executions": len(self.active_executions)
        }
