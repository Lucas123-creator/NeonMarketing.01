from typing import Optional, Dict
from datetime import datetime, timedelta
import threading
import logging
from prometheus_client import Counter

from neonhub.schemas.lead_state import LeadState
from neonhub.schemas.message_event import MessageChannel, MessageType, MessageStatus
from messaging.personal_messenger import PersonalMessenger
from neonhub.services.content_personalizer import ContentPersonalizer
from neonhub.utils.logging import get_logger
from neonhub.config.settings import get_settings

TRIGGERS_FIRED = Counter(
    'triggers_fired_total',
    'Number of triggers fired',
    ['type', 'channel']
)
TRIGGERS_SUPPRESSED = Counter(
    'triggers_suppressed_total',
    'Number of triggers suppressed',
    ['reason']
)

TRIGGER_LOG_PATH = "logs/trigger_events.log"

class TriggerManager:
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.messenger = PersonalMessenger()
        self.personalizer = ContentPersonalizer()
        self.cooldowns = {}  # lead_id -> {channel: last_trigger_time}
        self.lock = threading.Lock()
        self.trigger_log = TRIGGER_LOG_PATH

    def _log_trigger(self, lead_id: str, trigger_type: str, channel: str, status: str, details: Dict):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "lead_id": lead_id,
            "trigger_type": trigger_type,
            "channel": channel,
            "status": status,
            "details": details
        }
        try:
            with open(self.trigger_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            self.logger.error("Failed to log trigger event", error=str(e))

    def _can_trigger(self, lead_id: str, channel: str, cooldown_minutes: int = 60) -> bool:
        with self.lock:
            now = datetime.utcnow()
            last = self.cooldowns.get(lead_id, {}).get(channel)
            if last and (now - last) < timedelta(minutes=cooldown_minutes):
                return False
            self.cooldowns.setdefault(lead_id, {})[channel] = now
            return True

    def evaluate_and_trigger(self, lead_state: LeadState):
        lead_id = lead_state.lead_id
        persona = lead_state.metadata.get("persona")
        lang = lead_state.metadata.get("lang", "en")
        phone = lead_state.metadata.get("phone")
        whatsapp = lead_state.metadata.get("whatsapp")
        email = lead_state.metadata.get("email")
        score = lead_state.engagement_score
        status = lead_state.status
        events = lead_state.engagement_history
        now = datetime.utcnow()

        # Rule 1: Abandoned cart (metadata['cart_abandoned_at'])
        cart_abandoned_at = lead_state.metadata.get("cart_abandoned_at")
        if cart_abandoned_at:
            abandoned_time = datetime.fromisoformat(cart_abandoned_at)
            if (now - abandoned_time) > timedelta(minutes=60):
                if whatsapp and self._can_trigger(lead_id, "whatsapp", cooldown_minutes=120):
                    content = self.personalizer.generate_content(
                        template_id="mobile_demo_whatsapp",
                        personalization={"first_name": lead_state.metadata.get("first_name", "there"),
                                         "product": lead_state.metadata.get("cart_product", "our product"),
                                         "offer_code": lead_state.metadata.get("cart_offer_code", "WELCOME") ,
                                         "short_url": lead_state.metadata.get("cart_url", "bit.ly/offer")},
                        channel="whatsapp",
                        lang=lang,
                        persona=persona
                    )
                    msg_event = self.messenger.send_whatsapp(lead_id, whatsapp, content["body"])
                    TRIGGERS_FIRED.labels(type="cart_recovery", channel="whatsapp").inc()
                    self._log_trigger(lead_id, "cart_recovery", "whatsapp", getattr(msg_event.status, 'value', msg_event.status), {"content": content["body"]})
                    return msg_event
                else:
                    TRIGGERS_SUPPRESSED.labels(reason="cooldown_or_missing_whatsapp").inc()
                    self._log_trigger(lead_id, "cart_recovery", "whatsapp", "suppressed", {"reason": "cooldown or missing whatsapp"})

        # Rule 2: Low engagement after 2 emails
        email_sends = [e for e in events if e.event_type == "email_sent"]
        if score < 3 and len(email_sends) >= 2:
            if phone and self._can_trigger(lead_id, "sms", cooldown_minutes=180):
                content = self.personalizer.generate_content(
                    template_id="mobile_demo_sms",
                    personalization={"first_name": lead_state.metadata.get("first_name", "there"),
                                     "product": lead_state.metadata.get("product", "our product"),
                                     "offer_code": lead_state.metadata.get("offer_code", "WELCOME"),
                                     "short_url": lead_state.metadata.get("short_url", "bit.ly/offer")},
                    channel="sms",
                    lang=lang,
                    persona=persona
                )
                msg_event = self.messenger.send_sms(lead_id, phone, content["body"])
                TRIGGERS_FIRED.labels(type="cold_lead_nudge", channel="sms").inc()
                self._log_trigger(lead_id, "cold_lead_nudge", "sms", getattr(msg_event.status, 'value', msg_event.status), {"content": content["body"]})
                return msg_event
            else:
                TRIGGERS_SUPPRESSED.labels(reason="cooldown_or_missing_phone").inc()
                self._log_trigger(lead_id, "cold_lead_nudge", "sms", "suppressed", {"reason": "cooldown or missing phone"})

        # Rule 3: Reply received (pause triggers)
        reply_events = [e for e in events if e.event_type in ("email_reply", "linkedin_reply", "sms_reply", "whatsapp_reply")]
        if reply_events:
            TRIGGERS_SUPPRESSED.labels(reason="reply_received").inc()
            self._log_trigger(lead_id, "reply_ack", "all", "suppressed", {"reason": "reply received"})
            return None

        # Rule 4: Unsubscribe (pause triggers)
        unsubscribe_events = [e for e in events if e.event_type == "unsubscribe"]
        if unsubscribe_events:
            TRIGGERS_SUPPRESSED.labels(reason="unsubscribed").inc()
            self._log_trigger(lead_id, "unsubscribe", "all", "suppressed", {"reason": "unsubscribed"})
            return None

        # No trigger fired
        self._log_trigger(lead_id, "no_trigger", "none", "skipped", {})
        return None 