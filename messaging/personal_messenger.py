from typing import Optional, Dict
from datetime import datetime, timedelta
import time
import threading
import uuid
import logging

try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None

from neonhub.schemas.message_event import MessageEvent, MessageChannel, MessageType, MessageStatus
from neonhub.utils.logging import get_logger
from neonhub.config.settings import get_settings

class RateLimiter:
    def __init__(self, max_per_minute: int = 30):
        self.max_per_minute = max_per_minute
        self.timestamps = []
        self.lock = threading.Lock()

    def allow(self) -> bool:
        with self.lock:
            now = time.time()
            self.timestamps = [t for t in self.timestamps if now - t < 60]
            if len(self.timestamps) < self.max_per_minute:
                self.timestamps.append(now)
                return True
            return False

class OptOutManager:
    def __init__(self):
        self.opted_out_leads = set()
        self.lock = threading.Lock()

    def is_opted_out(self, lead_id: str) -> bool:
        with self.lock:
            return lead_id in self.opted_out_leads

    def opt_out(self, lead_id: str):
        with self.lock:
            self.opted_out_leads.add(lead_id)

class PersonalMessenger:
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.twilio_client = None
        if TwilioClient and hasattr(self.settings, "TWILIO_ACCOUNT_SID"):
            self.twilio_client = TwilioClient(
                self.settings.TWILIO_ACCOUNT_SID,
                self.settings.TWILIO_AUTH_TOKEN
            )
        self.sms_rate_limiter = RateLimiter(max_per_minute=30)
        self.whatsapp_rate_limiter = RateLimiter(max_per_minute=20)
        self.opt_out_manager = OptOutManager()

    def send_sms(self, lead_id: str, to_number: str, content: str) -> MessageEvent:
        if self.opt_out_manager.is_opted_out(lead_id):
            return MessageEvent(
                message_id=str(uuid.uuid4()),
                lead_id=lead_id,
                channel=MessageChannel.SMS,
                type=MessageType.OUTBOUND,
                status=MessageStatus.OPTED_OUT,
                content=content,
                sent_at=datetime.utcnow(),
                metadata={"reason": "opted_out"}
            )
        if not self.sms_rate_limiter.allow():
            return MessageEvent(
                message_id=str(uuid.uuid4()),
                lead_id=lead_id,
                channel=MessageChannel.SMS,
                type=MessageType.OUTBOUND,
                status=MessageStatus.FAILED,
                content=content,
                sent_at=datetime.utcnow(),
                metadata={"reason": "rate_limited"}
            )
        try:
            if self.twilio_client:
                msg = self.twilio_client.messages.create(
                    body=content,
                    from_=self.settings.TWILIO_SMS_FROM,
                    to=to_number
                )
                status = MessageStatus.SENT
                message_id = msg.sid
            else:
                # Mock send
                status = MessageStatus.SENT
                message_id = str(uuid.uuid4())
            event = MessageEvent(
                message_id=message_id,
                lead_id=lead_id,
                channel=MessageChannel.SMS,
                type=MessageType.OUTBOUND,
                status=status,
                content=content,
                sent_at=datetime.utcnow()
            )
            self.logger.info("SMS sent", lead_id=lead_id, message_id=message_id)
            return event
        except Exception as e:
            self.logger.error("SMS send failed", lead_id=lead_id, error=str(e))
            return MessageEvent(
                message_id=str(uuid.uuid4()),
                lead_id=lead_id,
                channel=MessageChannel.SMS,
                type=MessageType.OUTBOUND,
                status=MessageStatus.FAILED,
                content=content,
                sent_at=datetime.utcnow(),
                metadata={"error": str(e)}
            )

    def send_whatsapp(self, lead_id: str, to_number: str, content: str) -> MessageEvent:
        if self.opt_out_manager.is_opted_out(lead_id):
            return MessageEvent(
                message_id=str(uuid.uuid4()),
                lead_id=lead_id,
                channel=MessageChannel.WHATSAPP,
                type=MessageType.OUTBOUND,
                status=MessageStatus.OPTED_OUT,
                content=content,
                sent_at=datetime.utcnow(),
                metadata={"reason": "opted_out"}
            )
        if not self.whatsapp_rate_limiter.allow():
            return MessageEvent(
                message_id=str(uuid.uuid4()),
                lead_id=lead_id,
                channel=MessageChannel.WHATSAPP,
                type=MessageType.OUTBOUND,
                status=MessageStatus.FAILED,
                content=content,
                sent_at=datetime.utcnow(),
                metadata={"reason": "rate_limited"}
            )
        try:
            if self.twilio_client:
                msg = self.twilio_client.messages.create(
                    body=content,
                    from_=self.settings.TWILIO_WHATSAPP_FROM,
                    to=f"whatsapp:{to_number}"
                )
                status = MessageStatus.SENT
                message_id = msg.sid
            else:
                # Mock send
                status = MessageStatus.SENT
                message_id = str(uuid.uuid4())
            event = MessageEvent(
                message_id=message_id,
                lead_id=lead_id,
                channel=MessageChannel.WHATSAPP,
                type=MessageType.OUTBOUND,
                status=status,
                content=content,
                sent_at=datetime.utcnow()
            )
            self.logger.info("WhatsApp sent", lead_id=lead_id, message_id=message_id)
            return event
        except Exception as e:
            self.logger.error("WhatsApp send failed", lead_id=lead_id, error=str(e))
            return MessageEvent(
                message_id=str(uuid.uuid4()),
                lead_id=lead_id,
                channel=MessageChannel.WHATSAPP,
                type=MessageType.OUTBOUND,
                status=MessageStatus.FAILED,
                content=content,
                sent_at=datetime.utcnow(),
                metadata={"error": str(e)}
            )

    def opt_out(self, lead_id: str):
        self.opt_out_manager.opt_out(lead_id)
        self.logger.info("Lead opted out", lead_id=lead_id)

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        self.logger.info("Email sent", to_email=to_email, subject=subject)
        return True 