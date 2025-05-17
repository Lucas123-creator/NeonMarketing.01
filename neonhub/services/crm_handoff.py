import requests
import logging
from neonhub.schemas.lead_state import LeadState
from neonhub.config.settings import get_settings

def push_lead_to_crm(lead: LeadState, webhook_url: str) -> bool:
    """Push enriched lead data to external CRM via webhook."""
    payload = lead.dict()
    # Optionally, filter or map fields for CRM schema
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logging.info(f"CRM handoff success for lead {lead.lead_id}", extra={"crm_status": resp.status_code})
        return True
    except Exception as e:
        logging.error(f"CRM handoff failed for lead {lead.lead_id}: {e}")
        return False 