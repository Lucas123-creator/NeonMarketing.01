from typing import Dict, Any, Optional
import openai
from datetime import datetime

class AIPersonalizer:
    """Handles AI-powered personalization of email content."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
            
    async def personalize(
        self,
        template_name: str,
        recipient_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Personalize email content using AI."""
        try:
            # Prepare the prompt for the AI
            prompt = self._create_personalization_prompt(
                template_name,
                recipient_data,
                context
            )
            
            # Get AI response
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert email personalization assistant. Your task is to personalize email content while maintaining professionalism and relevance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse the AI response
            personalized_content = self._parse_ai_response(
                response.choices[0].message.content,
                template_name
            )
            
            return personalized_content
            
        except Exception as e:
            # Fallback to basic personalization if AI fails
            return self._fallback_personalization(
                template_name,
                recipient_data,
                context
            )
            
    def _create_personalization_prompt(
        self,
        template_name: str,
        recipient_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Create a prompt for the AI to personalize the email."""
        return f"""
        Please personalize the following email template for a B2B outreach campaign.
        
        Template Name: {template_name}
        
        Recipient Information:
        - Company: {recipient_data.get('company_name', 'N/A')}
        - Industry: {recipient_data.get('industry', 'N/A')}
        - Location: {recipient_data.get('location', {}).get('city', 'N/A')}, {recipient_data.get('location', {}).get('country', 'N/A')}
        - Contact Name: {recipient_data.get('contact_name', 'N/A')}
        
        Context:
        - Campaign Goal: {context.get('campaign_goal', 'N/A')}
        - Previous Interactions: {context.get('previous_interactions', 'None')}
        - Special Notes: {context.get('special_notes', 'None')}
        
        Please provide:
        1. A personalized subject line
        2. A personalized email body that maintains the core message while adding relevant personal touches
        3. Keep the HTML formatting intact
        4. Ensure the tone is professional but conversational
        
        Format your response as:
        SUBJECT: [personalized subject]
        BODY: [personalized body]
        """
        
    def _parse_ai_response(
        self,
        ai_response: str,
        template_name: str
    ) -> Dict[str, str]:
        """Parse the AI response into subject and body."""
        try:
            # Split the response into subject and body
            parts = ai_response.split("BODY:", 1)
            subject = parts[0].replace("SUBJECT:", "").strip()
            body = parts[1].strip() if len(parts) > 1 else ""
            
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            # If parsing fails, return the original template
            return self._fallback_personalization(template_name, {}, {})
            
    def _fallback_personalization(
        self,
        template_name: str,
        recipient_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Fallback method for basic personalization without AI."""
        # Basic template-based personalization
        subject = f"NeonHub Partnership Opportunity - {recipient_data.get('company_name', '')}"
        body = f"""
        <html>
        <body>
            <p>Dear {recipient_data.get('contact_name', 'there')},</p>
            
            <p>I hope this email finds you well. I'm reaching out from NeonHub regarding potential partnership opportunities.</p>
            
            <p>Best regards,<br>
            NeonHub Team</p>
        </body>
        </html>
        """
        
        return {
            "subject": subject,
            "body": body
        } 