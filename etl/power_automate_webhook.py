"""
Power Automate Webhook Handler
Version: 1.0
Auteur: Projet CRM Ruhlmann

Rôle: Gérer webhooks depuis Power Automate Desktop
  - Email events (sent, opened, clicked)
  - Brevo event tracking
  - Client behavior logging
  - Automation triggers

Integration:
  - Brevo webhooks → Power Automate
  - Power Automate → This webhook handler
  - Handler → PostgreSQL
  - Trigger automation rules
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

try:
    from flask import Flask, request, jsonify
except ImportError:
    Flask = None

from etl.config import logger


class WebhookHandler:
    """
    Gérateur de webhooks pour Power Automate
    """
    
    def __init__(self, app_name: str = "crm_webhook"):
        """
        Initialise le gestionnaire webhook
        
        Args:
            app_name: Nom application Flask
        """
        self.app_name = app_name
        self.events_log = []
        
        if Flask:
            self.app = Flask(app_name)
            self._setup_routes()
            logger.info("✅ Flask app initialized")
        else:
            self.app = None
            logger.warning("⚠️ Flask not installed. Webhook mode disabled.")
    
    def _setup_routes(self):
        """
        Configure les routes Flask
        """
        if not self.app:
            return
        
        @self.app.route('/webhook/email', methods=['POST'])
        def handle_email_event():
            """
            Webhook pour événements email Brevo
            """
            try:
                data = request.get_json()
                
                # Parser l'événement
                event = self._parse_email_event(data)
                
                if event:
                    # Logger
                    self.events_log.append(event)
                    logger.info(f"📧 Email event: {event['event_type']} for {event['email']}")
                    
                    # Trigger automation
                    self._trigger_automation(event)
                    
                    return jsonify({'status': 'received'}), 200
                else:
                    return jsonify({'status': 'invalid'}), 400
                    
            except Exception as e:
                logger.error(f"❌ Webhook error: {str(e)}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/webhook/behavior', methods=['POST'])
        def handle_behavior_event():
            """
            Webhook pour événements comportement client
            """
            try:
                data = request.get_json()
                
                # Parser l'événement
                event = self._parse_behavior_event(data)
                
                if event:
                    self.events_log.append(event)
                    logger.info(f"🤍 Behavior event: {event['action']} by {event['client_code']}")
                    
                    # Trigger automation
                    self._trigger_automation(event)
                    
                    return jsonify({'status': 'received'}), 200
                else:
                    return jsonify({'status': 'invalid'}), 400
                    
            except Exception as e:
                logger.error(f"❌ Webhook error: {str(e)}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/webhook/health', methods=['GET'])
        def health_check():
            """
            Health check endpoint
            """
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200
    
    def _parse_email_event(self, data: Dict) -> Optional[Dict]:
        """
        Parse un événement email Brevo
        
        Format Brevo webhook:
        {
            "event": "sent" | "opened" | "clicked" | "bounce" | "unsubscribed",
            "email": "user@example.com",
            "message-id": "123",
            "ts_event": 1234567890,
            "link": "https://..."
        }
        
        Args:
            data: JSON webhook data
        
        Returns:
            Dict event ou None
        """
        try:
            event_type = data.get('event')
            email = data.get('email')
            message_id = data.get('message-id')
            
            if not all([event_type, email]):
                return None
            
            # Valider event type
            valid_events = ['sent', 'opened', 'clicked', 'bounce', 'unsubscribed', 'complaint']
            if event_type not in valid_events:
                return None
            
            return {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'email': email,
                'message_id': message_id,
                'link': data.get('link'),
                'source': 'brevo',
                'brevo_timestamp': data.get('ts_event')
            }
            
        except Exception as e:
            logger.error(f"❌ Email event parsing error: {str(e)}")
            return None
    
    def _parse_behavior_event(self, data: Dict) -> Optional[Dict]:
        """
        Parse un événement comportement client
        
        Format expected:
        {
            "client_code": "CL001",
            "action": "click" | "open" | "purchase" | "form_submit",
            "metadata": { "product_id": "...", "page": "...", etc }
        }
        
        Args:
            data: JSON webhook data
        
        Returns:
            Dict event ou None
        """
        try:
            client_code = data.get('client_code')
            action = data.get('action')
            
            if not all([client_code, action]):
                return None
            
            return {
                'timestamp': datetime.now().isoformat(),
                'client_code': client_code,
                'action': action,
                'metadata': data.get('metadata', {}),
                'source': 'tracking'
            }
            
        except Exception as e:
            logger.error(f"❌ Behavior event parsing error: {str(e)}")
            return None
    
    def _trigger_automation(self, event: Dict):
        """
        Trigger automation rules basées sur l'événement
        
        Args:
            event: Dict événement
        """
        try:
            # Rules: événement → action
            rules = {
                'email': {
                    'opened': self._handle_email_opened,
                    'clicked': self._handle_email_clicked,
                    'bounce': self._handle_email_bounce,
                    'unsubscribed': self._handle_email_unsubscribe
                },
                'tracking': {
                    'click': self._handle_click,
                    'purchase': self._handle_purchase,
                    'form_submit': self._handle_form_submit
                }
            }
            
            source = event.get('source')
            if source in rules:
                action_key = event.get('event_type') or event.get('action')
                
                if action_key in rules[source]:
                    handler = rules[source][action_key]
                    handler(event)
        
        except Exception as e:
            logger.error(f"❌ Automation trigger error: {str(e)}")
    
    def _handle_email_opened(self, event: Dict):
        """
        Action: Email ouvert
        """
        logger.info(f"📨 Email opened: {event['email']}")
        
        # Automation: Increment engagement score
        # TODO: Update PostgreSQL client_engagement
    
    def _handle_email_clicked(self, event: Dict):
        """
        Action: Lien cliqué dans email
        """
        logger.info(f"🔗 Link clicked: {event['email']} -> {event.get('link')}")
        
        # Automation: High engagement, prepare upsell
        # TODO: Mark client for follow-up
    
    def _handle_email_bounce(self, event: Dict):
        """
        Action: Email bounce
        """
        logger.warning(f"⚠️ Email bounce: {event['email']}")
        
        # Automation: Mark email invalid, update contact
        # TODO: Flag email in PostgreSQL
    
    def _handle_email_unsubscribe(self, event: Dict):
        """
        Action: Unsubscribe
        """
        logger.info(f"🛡 Unsubscribe: {event['email']}")
        
        # Automation: Respect opt-out
        # TODO: Update contact preferences
    
    def _handle_click(self, event: Dict):
        """
        Action: Click on website
        """
        logger.info(f"🔗 Click by {event.get('client_code')}: {event.get('metadata', {}).get('page')}")
        
        # Automation: Track engagement
    
    def _handle_purchase(self, event: Dict):
        """
        Action: Purchase completed
        """
        logger.info(f"🛍 Purchase by {event.get('client_code')}")
        
        # Automation: Update lead score, trigger thank-you email
    
    def _handle_form_submit(self, event: Dict):
        """
        Action: Form submitted
        """
        logger.info(f"📄 Form submitted by {event.get('client_code')}")
        
        # Automation: Follow-up sequence
    
    def save_events(self, output_file: Optional[str] = None):
        """
        Sauvegarde les événements en JSON
        
        Args:
            output_file: Fichier de sortie
        """
        if not self.events_log:
            logger.info("ℹ️ Aucun événement à enregistrer")
            return
        
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"exports/logs/webhook_events_{timestamp}.json"
        
        try:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.events_log, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Events sauvegardés: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde: {str(e)}")
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """
        Démarre le serveur webhook Flask
        
        Args:
            host: Host à bind
            port: Port à bind
            debug: Mode debug
        """
        if not self.app:
            logger.error("❌ Flask not available")
            return
        
        logger.info(f"\n🚀 Démarrage webhook server")
        logger.info(f"   Host: {host}")
        logger.info(f"   Port: {port}")
        logger.info(f"   Endpoints:")
        logger.info(f"     - POST /webhook/email   (Brevo events)")
        logger.info(f"     - POST /webhook/behavior (Behavior tracking)")
        logger.info(f"     - GET /webhook/health    (Health check)")
        
        try:
            self.app.run(host=host, port=port, debug=debug)
        except Exception as e:
            logger.error(f"❌ Server error: {str(e)}")


def create_webhook_handler() -> WebhookHandler:
    """
    Factory function pour créer handler webhook
    
    Returns:
        WebhookHandler instance
    """
    return WebhookHandler()


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  🚀 POWER AUTOMATE WEBHOOK HANDLER")
    print("="*70 + "\n")
    
    handler = create_webhook_handler()
    
    print("\n1️⃣ Webhook Handler created")
    print(f"   Status: {'Ready' if handler.app else 'Flask not available'}")
    
    print("\n2️⃣ Available endpoints:")
    print("   - POST /webhook/email")
    print("   - POST /webhook/behavior")
    print("   - GET /webhook/health")
    
    print("\n3️⃣ To run server:")
    print("   handler.run(host='0.0.0.0', port=5000)")
    
    print("\n4️⃣ In production:")
    print("   - Use gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 app:handler.app")
    print("   - Or use Docker")
    
    print("\n" + "="*70 + "\n")
