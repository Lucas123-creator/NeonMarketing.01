from typing import Dict, Any, Optional
import json
import os
from pathlib import Path

class EmailTemplate:
    """Manages email templates and their variations."""
    
    def __init__(self, templates_dir: str = "templates/email"):
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, Dict[str, Any]] = {}
        
    async def load_templates(self) -> None:
        """Load all email templates from the templates directory."""
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True)
            self._create_default_templates()
            
        for template_file in self.templates_dir.glob("*.json"):
            with open(template_file, "r", encoding="utf-8") as f:
                template_data = json.load(f)
                self.templates[template_data["name"]] = template_data
                
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by name."""
        return self.templates.get(name)
        
    def _create_default_templates(self) -> None:
        """Create default email templates if none exist."""
        default_templates = {
            "initial_outreach": {
                "name": "initial_outreach",
                "subject": "{{company_name}} - Let's Discuss Neon Sign Distribution",
                "body": """
                <html>
                <body>
                    <p>Dear {{contact_name}},</p>
                    
                    <p>I hope this email finds you well. I'm reaching out because I noticed {{company_name}}'s impressive presence in the {{industry}} industry, particularly in {{location}}.</p>
                    
                    <p>We're NeonHub, a leading manufacturer of premium neon signs and LED displays. We're currently expanding our distribution network and believe {{company_name}} would be an excellent partner.</p>
                    
                    <p>Our products include:</p>
                    <ul>
                        <li>Custom neon signs for businesses</li>
                        <li>LED video walls and displays</li>
                        <li>Architectural lighting solutions</li>
                    </ul>
                    
                    <p>Would you be interested in learning more about our distribution partnership opportunities? I'd be happy to schedule a brief call to discuss how we could work together.</p>
                    
                    <p>Best regards,<br>
                    {{sender_name}}<br>
                    NeonHub Partnership Team</p>
                </body>
                </html>
                """,
                "variables": [
                    "company_name",
                    "contact_name",
                    "industry",
                    "location",
                    "sender_name"
                ]
            },
            "follow_up": {
                "name": "follow_up",
                "subject": "Following up - NeonHub Distribution Opportunity",
                "body": """
                <html>
                <body>
                    <p>Hi {{contact_name}},</p>
                    
                    <p>I wanted to follow up on my previous email about potential distribution opportunities with NeonHub. I understand you're busy, so I'll keep this brief.</p>
                    
                    <p>We've recently launched some exciting new products that I think would be particularly relevant for {{company_name}}'s market in {{location}}.</p>
                    
                    <p>Would you have 15 minutes this week to discuss how we could help grow your business?</p>
                    
                    <p>Best regards,<br>
                    {{sender_name}}<br>
                    NeonHub Partnership Team</p>
                </body>
                </html>
                """,
                "variables": [
                    "contact_name",
                    "company_name",
                    "location",
                    "sender_name"
                ]
            }
        }
        
        for template_name, template_data in default_templates.items():
            template_path = self.templates_dir / f"{template_name}.json"
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump(template_data, f, indent=2)
                
    def create_template(
        self,
        name: str,
        subject: str,
        body: str,
        variables: list
    ) -> None:
        """Create a new email template."""
        template_data = {
            "name": name,
            "subject": subject,
            "body": body,
            "variables": variables
        }
        
        template_path = self.templates_dir / f"{name}.json"
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, indent=2)
            
        self.templates[name] = template_data 