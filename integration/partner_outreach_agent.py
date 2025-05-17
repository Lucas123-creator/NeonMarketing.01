import logging
from neonhub.services.content_personalizer import ContentPersonalizer
from neonhub.config.settings import get_settings
from messaging.personal_messenger import PersonalMessenger
from typing import Dict, Any

class PartnerOutreachAgent:
    def __init__(self):
        self.settings = get_settings()
        self.personalizer = ContentPersonalizer()
        self.messenger = PersonalMessenger()
        self.logger = logging.getLogger("PartnerOutreachAgent")

    async def contact_partner(self, partner: Dict[str, Any], channel: str = "email", lang: str = "en"):
        # partner: {"name": str, "email": str, "region": str, ...}
        content = self.personalizer.generate_content(
            template_id="partner_onboarding",
            personalization={"partner_name": partner["name"]},
            channel=channel,
            lang=lang
        )
        if channel == "email":
            result = self.messenger.send_email(partner["email"], content["subject"], content["body"])
        elif channel == "whatsapp":
            result = self.messenger.send_whatsapp(partner["name"], partner["phone"], content["body"])
        else:
            result = None
        self.logger.info(f"Contacted partner {partner['name']} via {channel}", extra={"result": result})
        return result 