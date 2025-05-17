from typing import Dict, Any, Optional
from datetime import datetime
from prometheus_client import Counter
import logging
import requests
from neonhub.schemas.crm_lead_payload import CRMLeadPayload

CRM_HANDOFF_TOTAL = Counter(
    'crm_handoff_total',
    'Number of leads handed off to CRM',
    ['destination']
)
CRM_RESPONSE_SUCCESS_TOTAL = Counter(
    'crm_response_success_total',
    'Number of successful CRM responses',
    ['destination']
)
HANDOFF_ERRORS_TOTAL = Counter(
    'handoff_errors_total',
    'Number of CRM handoff errors',
    ['destination']
)

class CRMHandoff:
    def __init__(self, crm_url: str, api_key: Optional[str] = None, destination: str = "hubspot"):
        self.logger = logging.getLogger("CRMHandoff")
        self.crm_url = crm_url
        self.api_key = api_key
        self.destination = destination

    def should_handoff(self, lead: Dict[str, Any]) -> bool:
        # Trigger: engagement score > threshold or positive reply
        score = lead.get("engagement_score", 0)
        replies = [e for e in lead.get("engagement_history", []) if e.get("event_type") in ("email_reply", "whatsapp_reply")]
        positive_reply = any("yes" in (e.get("metadata", {}).get("text", "").lower()) for e in replies)
        return score > 7 or positive_reply

    def handoff(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        payload = CRMLeadPayload(**lead, crm_destination=self.destination, handoff_status="pending").dict()
        CRM_HANDOFF_TOTAL.labels(destination=self.destination).inc()
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            response = requests.post(self.crm_url, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                payload["handoff_status"] = "handed_off"
                CRM_RESPONSE_SUCCESS_TOTAL.labels(destination=self.destination).inc()
                self.logger.info(f"CRM handoff success for {payload['lead_id']} to {self.destination}")
            else:
                payload["handoff_status"] = "error"
                HANDOFF_ERRORS_TOTAL.labels(destination=self.destination).inc()
                self.logger.error(f"CRM handoff failed for {payload['lead_id']} to {self.destination}: {response.text}")
        except Exception as e:
            payload["handoff_status"] = "error"
            HANDOFF_ERRORS_TOTAL.labels(destination=self.destination).inc()
            self.logger.error(f"CRM handoff exception for {payload['lead_id']} to {self.destination}: {str(e)}")
        payload["handoff_time"] = datetime.utcnow().isoformat()
        return payload 