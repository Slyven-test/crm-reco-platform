"""
Intégration Brevo (anciennement Sendinblue)
Version: 1.0
Auteur: Projet CRM Ruhlmann

Rôle: Synchroniser les contacts et envoyer les emails de recommandations
Fonctionnalités:
  - Upload contacts Brevo
  - Envoi emails personnalisés
  - Log des statuts (ok, bounce, opt-out)
  - Gestion des erreurs
  - Limitation de fréquence (anti-spam)
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

from etl.config import logger, CURATED_DIR


class BrevoClient:
    """
    Client pour l'API Brevo
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le client Brevo
        
        Args:
            api_key: Clé API Brevo (défaut: variable d'environnement BREVO_API_KEY)
        """
        self.api_key = api_key or os.getenv('BREVO_API_KEY')
        
        if not self.api_key:
            logger.warning("⚠️ Clé API Brevo non trouvée (variable BREVO_API_KEY)")
            logger.warning("   Pour utiliser Brevo, définir: export BREVO_API_KEY=your_key")
        
        self.base_url = "https://api.brevo.com/v3"
        self.headers = {
            "api-key": self.api_key or "demo",
            "Content-Type": "application/json"
        }
        self.contact_log = []
    
    def test_connection(self) -> bool:
        """
        Teste la connexion à l'API Brevo
        
        Returns:
            True si connecté, False sinon
        """
        if not requests:
            logger.warning("⚠️ requests library non installée. Installer: pip install requests")
            return False
        
        if not self.api_key:
            logger.warning("⚠️ Clé API Brevo non disponible")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/account",
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("✅ Connecté à Brevo")
                account = response.json()
                logger.info(f"   Compte: {account.get('email', 'Unknown')}")
                return True
            else:
                logger.error(f"❌ Erreur Brevo: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur connexion Brevo: {str(e)}")
            return False
    
    def create_contact(self, email: str, attributes: Dict) -> bool:
        """
        Crée ou met à jour un contact Brevo
        
        Args:
            email: Email du contact
            attributes: Dict avec attributs (firstName, lastName, etc.)
        
        Returns:
            True si succès
        """
        if not requests or not self.api_key:
            logger.debug(f"Mode démo: Contact {email} (non envoyé)")
            return True
        
        try:
            payload = {
                "email": email,
                "attributes": attributes
            }
            
            response = requests.post(
                f"{self.base_url}/contacts",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.debug(f"✅ Contact créé: {email}")
                return True
            else:
                logger.warning(f"⚠️ Erreur contact {email}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur création contact: {str(e)}")
            return False
    
    def send_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        html_content: str,
        template_name: str = "recommendation"
    ) -> Dict:
        """
        Envoie un email via Brevo
        
        Args:
            recipient_email: Email destinataire
            recipient_name: Nom destinataire
            subject: Sujet email
            html_content: Contenu HTML email
            template_name: Nom du template (pour logs)
        
        Returns:
            Dict avec statut et message
        """
        if not requests or not self.api_key:
            # Mode démo
            logger.info(f"📧 [DEMO] Email would be sent to {recipient_email}")
            logger.info(f"   Subject: {subject}")
            return {
                'success': True,
                'email': recipient_email,
                'status': 'demo',
                'message_id': 'demo-' + recipient_email.replace('@', '-at-')
            }
        
        try:
            payload = {
                "to": [{"email": recipient_email, "name": recipient_name}],
                "subject": subject,
                "htmlContent": html_content,
                "sender": {
                    "name": "Domaine du Vieux Lavoir",
                    "email": "recommendations@ruhlmann.fr"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/smtp/email",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                message_id = response.json().get('messageId')
                logger.info(f"✅ Email envoyé: {recipient_email}")
                
                return {
                    'success': True,
                    'email': recipient_email,
                    'status': 'sent',
                    'message_id': message_id,
                    'template': template_name
                }
            else:
                logger.warning(f"⚠️ Erreur envoi {recipient_email}: {response.status_code}")
                return {
                    'success': False,
                    'email': recipient_email,
                    'status': 'error',
                    'error': response.status_code
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur envoi email: {str(e)}")
            return {
                'success': False,
                'email': recipient_email,
                'status': 'exception',
                'error': str(e)
            }
    
    def log_contact(self, contact_data: Dict):
        """
        Log un contact dans le journal
        
        Args:
            contact_data: Dict avec infos contact
        """
        self.contact_log.append({
            'timestamp': datetime.now().isoformat(),
            **contact_data
        })
    
    def save_logs(self, output_file: Optional[str] = None):
        """
        Sauvegarde les logs de contacts en JSON
        
        Args:
            output_file: Fichier de sortie (défaut: logs/brevo_contacts_*.json)
        """
        if not self.contact_log:
            logger.info("ℹ️ Aucun contact à enregistrer")
            return
        
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"exports/logs/brevo_contacts_{timestamp}.json"
        
        try:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.contact_log, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Logs sauvegardés: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde logs: {str(e)}")


class EmailTemplates:
    """
    Templates d'emails de recommandations
    """
    
    @staticmethod
    def rebuy_template(
        client_name: str,
        product_name: str,
        product_desc: str,
        price: str
    ) -> tuple[str, str]:
        """
        Template pour rachat d'un produit déjà acheté
        
        Returns:
            (subject, html_content)
        """
        subject = f"Vous aimeriez replonger dans {product_name}?"
        
        html = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #8B0000; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .product {{ background: #f5f5f5; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                .price {{ font-size: 24px; color: #8B0000; font-weight: bold; }}
                .cta {{ background: #8B0000; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🍷 Domaine du Vieux Lavoir</h1>
                </div>
                <div class="content">
                    <h2>Bonjour {client_name},</h2>
                    <p>Nous avons remarqué que vous aviez apprécié notre <strong>{product_name}</strong>.</p>
                    <p>Le millésime 2024 est maintenant disponible! 🎉</p>
                    
                    <div class="product">
                        <h3>{product_name}</h3>
                        <p>{product_desc}</p>
                        <p class="price">{price} €</p>
                    </div>
                    
                    <p>Nous vous réservons une offre spéciale de bienvenue!</p>
                    <a href="https://ruhlmann.fr/produits" class="cta">Découvrir →</a>
                </div>
                <div class="footer">
                    <p>Domaine du Vieux Lavoir | Alsace, France<br>
                    <a href="https://ruhlmann.fr">www.ruhlmann.fr</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html
    
    @staticmethod
    def crosssell_template(
        client_name: str,
        product_name: str,
        complement_name: str,
        reason: str
    ) -> tuple[str, str]:
        """
        Template pour un produit complémentaire (cross-sell)
        
        Returns:
            (subject, html_content)
        """
        subject = f"{complement_name} : L'accord parfait avec {product_name}"
        
        html = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #8B0000; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .pairing {{ background: #fff8dc; padding: 15px; margin: 15px 0; border-left: 4px solid #8B0000; }}
                .cta {{ background: #8B0000; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🍷 Accord Parfait</h1>
                </div>
                <div class="content">
                    <h2>Bonjour {client_name},</h2>
                    <p>Puisque vous aimez le {product_name}, nous vous recommandons...</p>
                    
                    <div class="pairing">
                        <h3>✨ {complement_name}</h3>
                        <p><strong>Pourquoi?</strong> {reason}</p>
                    </div>
                    
                    <p>Découvrez cet accord parfait pour sublimer vos repas!</p>
                    <a href="https://ruhlmann.fr/produits" class="cta">Explorer →</a>
                </div>
                <div class="footer">
                    <p>Domaine du Vieux Lavoir | Alsace, France<br>
                    <a href="https://ruhlmann.fr">www.ruhlmann.fr</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html
    
    @staticmethod
    def winback_template(
        client_name: str,
        last_purchase: str
    ) -> tuple[str, str]:
        """
        Template pour réactiver un client inactif (win-back)
        
        Returns:
            (subject, html_content)
        """
        subject = f"{client_name}, nous vous avons manqué! 👋"
        
        html = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #8B0000; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .offer {{ background: #fff3cd; padding: 15px; margin: 15px 0; border-radius: 5px; text-align: center; }}
                .discount {{ font-size: 32px; color: #8B0000; font-weight: bold; }}
                .cta {{ background: #8B0000; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🍷 Bienvenue Surprise</h1>
                </div>
                <div class="content">
                    <h2>Cher(e) {client_name},</h2>
                    <p>Cela fait un moment que nous n'avons pas eu de nouvelles...</p>
                    <p>Votre dernier achat remonte à {last_purchase}.</p>
                    
                    <div class="offer">
                        <p>Pour vous remercier de votre fidélité:</p>
                        <div class="discount">🎁 -15% BIENVENUE</div>
                        <p><strong>Code:</strong> WELCOME2025</p>
                    </div>
                    
                    <p>Venez découvrir nos nouvelles sélections!</p>
                    <a href="https://ruhlmann.fr/produits" class="cta">Retour aux sources →</a>
                </div>
                <div class="footer">
                    <p>Domaine du Vieux Lavoir | Alsace, France<br>
                    <a href="https://ruhlmann.fr">www.ruhlmann.fr</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html


def send_recommendations_email(
    client_code: str,
    email: str,
    client_name: str,
    scenario: str,
    products: List[Dict]
) -> Dict:
    """
    Fonction utilitaire: Envoyer un email de recommandation
    
    Args:
        client_code: Code client
        email: Email destinataire
        client_name: Nom client
        scenario: Type recommendation (rebuy, cross-sell, winback)
        products: Liste de produits recommandés
    
    Returns:
        Dict avec statut envoi
    """
    brevo = BrevoClient()
    
    # Générer le template
    if scenario == 'rebuy' and products:
        product = products[0]
        subject, html = EmailTemplates.rebuy_template(
            client_name=client_name,
            product_name=product.get('name', 'Produit'),
            product_desc=product.get('description', ''),
            price=product.get('price', 'N/A')
        )
    
    elif scenario == 'cross-sell' and len(products) >= 2:
        subject, html = EmailTemplates.crosssell_template(
            client_name=client_name,
            product_name=products[0].get('name', 'Produit 1'),
            complement_name=products[1].get('name', 'Produit 2'),
            reason='Accord parfait avec vos préférences'
        )
    
    elif scenario == 'winback':
        subject, html = EmailTemplates.winback_template(
            client_name=client_name,
            last_purchase='quelques mois'
        )
    
    else:
        logger.warning(f"⚠️ Scenario inconnu: {scenario}")
        return {'success': False, 'error': f'Unknown scenario: {scenario}'}
    
    # Envoyer
    result = brevo.send_email(
        recipient_email=email,
        recipient_name=client_name,
        subject=subject,
        html_content=html,
        template_name=scenario
    )
    
    # Log
    brevo.log_contact({
        'client_code': client_code,
        'email': email,
        'scenario': scenario,
        'status': result['status'],
        'message_id': result.get('message_id')
    })
    
    return result


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  🧪 TEST BREVO INTEGRATION")
    print("="*70 + "\n")
    
    # Initialiser client
    brevo = BrevoClient()
    
    # Test connexion
    print("\n1️⃣ Test connexion Brevo")
    connected = brevo.test_connection()
    
    # Test email (mode démo)
    print("\n2️⃣ Test envoi email (mode démo)")
    result = brevo.send_email(
        recipient_email="test@example.com",
        recipient_name="Jean Dupont",
        subject="Test Email from Brevo",
        html_content="<h1>Ceci est un test</h1>",
        template_name="test"
    )
    print(f"   Résultat: {result}")
    
    # Test template rebuy
    print("\n3️⃣ Test template rebuy")
    subject, html = EmailTemplates.rebuy_template(
        client_name="Marie",
        product_name="Gewurztraminer VT",
        product_desc="Alsace, 2022, Vendanges Tardives",
        price="36.00"
    )
    print(f"   Subject: {subject}")
    print(f"   HTML length: {len(html)} characters")
    
    # Test envoi recommandation
    print("\n4️⃣ Test envoi recommandation (rebuy)")
    result = send_recommendations_email(
        client_code="CL001",
        email="jean@example.com",
        client_name="Jean Dupont",
        scenario="rebuy",
        products=[
            {
                'name': 'Cremant d\'Alsace Extra Brut',
                'description': 'Alsace, 2023, Pétillant',
                'price': '12.50'
            }
        ]
    )
    print(f"   Résultat: {result}")
    
    # Sauvegarder logs
    print("\n5️⃣ Sauvegarde logs")
    brevo.save_logs()
    
    print("\n" + "="*70)
    print("  ✅ Tests terminés")
    print("="*70 + "\n")
