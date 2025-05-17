from typing import List, Optional, Dict
from datetime import datetime, timedelta
import os
import json

LOG_FILE_PATH = os.getenv("NEONHUB_LOG_FILE", "logs/neonhub.log")

class LogViewer:
    """View and filter structured logs for agents."""
    def __init__(self, log_file: str = LOG_FILE_PATH):
        self.log_file = log_file

    def get_logs(
        self,
        agent_id: Optional[str] = None,
        level: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        logs = []
        try:
            with open(self.log_file, "r") as f:
                for line in reversed(list(f)):
                    try:
                        log = json.loads(line)
                        if agent_id and log.get("agent_id") != agent_id:
                            continue
                        if level and log.get("level") != level:
                            continue
                        if since:
                            log_time = datetime.fromisoformat(log.get("timestamp"))
                            if log_time < since:
                                continue
                        logs.append(log)
                        if len(logs) >= limit:
                            break
                    except Exception:
                        continue
        except FileNotFoundError:
            return []
        return logs[::-1]  # Return in chronological order 