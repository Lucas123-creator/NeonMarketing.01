from typing import Dict, Optional
from datetime import datetime
import threading

class AgentStatus:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.last_heartbeat = datetime.utcnow()
        self.last_error: Optional[str] = None
        self.active = False
        self.last_action: Optional[str] = None
        self.last_action_time: Optional[datetime] = None
        self.error_count = 0
        self.lock = threading.Lock()

    def heartbeat(self, action: Optional[str] = None):
        with self.lock:
            self.last_heartbeat = datetime.utcnow()
            self.active = True
            if action:
                self.last_action = action
                self.last_action_time = self.last_heartbeat

    def report_error(self, error: str):
        with self.lock:
            self.last_error = error
            self.error_count += 1
            self.active = False
            self.last_action_time = datetime.utcnow()

    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "last_error": self.last_error,
            "active": self.active,
            "last_action": self.last_action,
            "last_action_time": self.last_action_time.isoformat() if self.last_action_time else None,
            "error_count": self.error_count
        }

class AgentStatusTracker:
    def __init__(self):
        self.statuses: Dict[str, AgentStatus] = {}
        self.lock = threading.Lock()

    def heartbeat(self, agent_id: str, action: Optional[str] = None):
        with self.lock:
            if agent_id not in self.statuses:
                self.statuses[agent_id] = AgentStatus(agent_id)
            self.statuses[agent_id].heartbeat(action)

    def report_error(self, agent_id: str, error: str):
        with self.lock:
            if agent_id not in self.statuses:
                self.statuses[agent_id] = AgentStatus(agent_id)
            self.statuses[agent_id].report_error(error)

    def get_status(self, agent_id: str) -> Optional[Dict]:
        with self.lock:
            if agent_id in self.statuses:
                return self.statuses[agent_id].to_dict()
            return None

    def get_all_statuses(self) -> Dict[str, Dict]:
        with self.lock:
            return {aid: status.to_dict() for aid, status in self.statuses.items()}

    def get_high_error_agents(self, threshold: int = 3) -> Dict[str, Dict]:
        with self.lock:
            return {aid: status.to_dict() for aid, status in self.statuses.items() if status.error_count >= threshold} 