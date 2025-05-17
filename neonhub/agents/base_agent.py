from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic
from datetime import datetime
import uuid
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from ..utils.logging import get_logger
from ..config.settings import get_settings

T = TypeVar('T')

class AgentError(Exception):
    """Base exception for agent errors."""
    pass

class AgentConfigError(AgentError):
    """Configuration error in agent."""
    pass

class AgentExecutionError(AgentError):
    """Error during agent execution."""
    pass

class BaseAgent(ABC, Generic[T]):
    """Base class for all NeonHub agents with improved error handling and retry logic."""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.config = config or {}
        self.settings = get_settings()
        self.trace_id = str(uuid.uuid4())
        self.logger = get_logger(self.trace_id)
        self.last_run: Optional[datetime] = None
        self.status = "initialized"
        self.metrics = {}
        
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent and its resources."""
        pass
        
    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> T:
        """Execute the agent's main task."""
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources used by the agent."""
        pass
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(AgentExecutionError)
    )
    async def run(self, *args: Any, **kwargs: Any) -> T:
        """Main execution method with logging, error handling, and retry logic."""
        try:
            self.status = "running"
            self.last_run = datetime.utcnow()
            self.logger.info(
                f"Starting execution of {self.agent_id}",
                agent_id=self.agent_id,
                args=args,
                kwargs=kwargs
            )
            
            result = await self.execute(*args, **kwargs)
            
            self.status = "completed"
            self.logger.info(
                f"Successfully completed execution of {self.agent_id}",
                agent_id=self.agent_id,
                result=result
            )
            
            return result
            
        except Exception as e:
            self.status = "failed"
            self.logger.exception(
                f"Error in {self.agent_id}",
                agent_id=self.agent_id,
                error=str(e)
            )
            raise AgentExecutionError(f"Agent execution failed: {str(e)}") from e
            
    async def retry(self, *args: Any, **kwargs: Any) -> T:
        """Retry the agent's execution with exponential backoff."""
        try:
            return await self.run(*args, **kwargs)
        except AgentExecutionError as e:
            self.logger.warning(
                f"Retrying {self.agent_id} after failure",
                agent_id=self.agent_id,
                error=str(e)
            )
            return await self.run(*args, **kwargs)
            
    async def fail_safe(self, *args: Any, **kwargs: Any) -> Optional[T]:
        """Execute with fail-safe mechanism."""
        try:
            return await self.run(*args, **kwargs)
        except Exception as e:
            self.logger.error(
                f"Fail-safe triggered for {self.agent_id}",
                agent_id=self.agent_id,
                error=str(e)
            )
            return None
            
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "trace_id": self.trace_id,
            "metrics": self.metrics
        }
        
    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update agent metrics."""
        self.metrics.update(metrics)
        
    def reset_metrics(self) -> None:
        """Reset agent metrics."""
        self.metrics = {} 