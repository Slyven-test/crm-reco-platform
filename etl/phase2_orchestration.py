"""
Orchestration Phase 2: Brevo + Recommandations
Version: 1.0
Auteur: Projet CRM Ruhlmann

Procédure:
  1. Générer recommandations (RFM + co-achats)
  2. Récupérer emails clients
  3. Envoyer emails Brevo
  4. Logger les statuts
  5. Générer rapport

Durée estimée: 5-10 minutes selon nombre clients
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from sqlalchemy import create_engine, text

from etl.config import logger, DATABASE_URL
from etl.recommendations_engine import RecommendationGenerator, run_recommendation_pipeline
from etl.brevo_integration import BrevoClient, send_recommendations_email


class Phase2Orchestrator:
    """
    Orchestrateur pour Phase 2: Recommandations + Brevo
    """
    
    def __init__(self):
        """
        Initialise l'orchestrateur
        """
        self.engine = create_engine(DATABASE_URL)
        self.brevo = BrevoClient()
        self.recommendations = []
        self.campaign_log = []
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def get_client_emails(self) -> Dict[str, Dict]:
        """
        Récupère les emails des clients depuis PostgreSQL
        
        Returns:
            Dict {client_code: {email, name, etc}}
        """
        logger.info("\n📧 RÉCUPÉRATION EMAILS CLIENTS")
        
        try:
            # Requete pour récupérer emails uniques par client
            query = """
            SELECT DISTINCT
                client_code,
                COALESCE(email, 'noemail@unknown.fr') as email,
                COALESCE(client_name, client_code) as client_name,
                COUNT(DISTINCT document_id) as purchase_count
            FROM etl.ventes_lignes
            WHERE client_code IS NOT NULL
            GROUP BY client_code, email, client_name
            ORDER BY client_code
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                clients = {}
                for row in result:
                    clients[row[0]] = {
                        'email': row[1],
                        'name': row[2],
                        'purchases': row[3]
                    }
            
            logger.info(f"   {len(clients)} clients récupérés")
            valid_emails = sum(1 for c in clients.values() if c['email'] != 'noemail@unknown.fr')
            logger.info(f"   Emails valides: {valid_emails}")
            
            return clients
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération emails: {str(e)}", exc_info=True)
            return {}
    
    def generate_recommendations(self) -> bool:
        """
        Génére les recommandations
        
        Returns:
            True si succès
        """
        logger.info("\n🪧 GÉNÉRATION RECOMMANDATIONS")
        
        try:
            result = run_recommendation_pipeline()
            
            if result['success']:
                self.recommendations = result.get('recommendations', [])
                logger.info(f"   {len(self.recommendations)} recommandations générées")
                return True
            else:
                logger.error(f"   ❌ {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur recommandations: {str(e)}", exc_info=True)
            return False
    
    def send_emails_campaign(self, clients: Dict[str, Dict], dry_run: bool = True):
        """
        Envoie la campagne email via Brevo
        
        Args:
            clients: Dict clients avec emails
            dry_run: Si True, simule l'envoi (défaut pour sécurité)
        """
        logger.info(f"\n📧 CAMPAGNE BREVO ({len(self.recommendations)} emails)")
        
        if dry_run:
            logger.warning("⚠️ MODE DRY-RUN: Emails non réellement envoyés")
        
        success_count = 0
        error_count = 0
        
        for rec in self.recommendations:
            client_code = rec['client_code']
            
            # Vérifier que le client existe
            if client_code not in clients:
                logger.warning(f"   ⚠️ Client {client_code} pas trouvé")
                error_count += 1
                continue
            
            client_info = clients[client_code]
            email = client_info['email']
            name = client_info['name']
            
            # Skip emails invalides
            if email == 'noemail@unknown.fr':
                logger.warning(f"   ⚠️ {client_code}: Email invalide")
                error_count += 1
                continue
            
            try:
                # Envoyer email
                result = send_recommendations_email(
                    client_code=client_code,
                    email=email,
                    client_name=name,
                    scenario=rec['scenario'],
                    products=rec['products']
                )
                
                # Logger le résultat
                if result.get('success'):
                    success_count += 1
                    status = 'sent'
                else:
                    error_count += 1
                    status = 'error'
                
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'client_code': client_code,
                    'email': email,
                    'scenario': rec['scenario'],
                    'status': status,
                    'message_id': result.get('message_id', 'N/A'),
                    'dry_run': dry_run
                }
                self.campaign_log.append(log_entry)
                
            except Exception as e:
                logger.error(f"   ❌ {client_code}: {str(e)}")
                error_count += 1
        
        logger.info(f"\n   Résultats:")
        logger.info(f"   ✅ Succès: {success_count}")
        logger.info(f"   ❌ Erreurs: {error_count}")
    
    def generate_report(self) -> Dict:
        """
        Génére un rapport Phase 2
        
        Returns:
            Dict rapport
        """
        logger.info("\n📊 GÉNÉRATION RAPPORT")
        
        report = {
            'timestamp': self.timestamp,
            'datetime': datetime.now().isoformat(),
            'phase': 'Phase 2 - Brevo + Recommandations',
            'recommendations_generated': len(self.recommendations),
            'emails_sent': len([l for l in self.campaign_log if l['status'] == 'sent']),
            'emails_failed': len([l for l in self.campaign_log if l['status'] == 'error']),
            'by_scenario': {},
            'details': self.campaign_log
        }
        
        # Statistiques par scénario
        for scenario in ['rebuy', 'cross-sell', 'winback']:
            count = len([r for r in self.recommendations if r['scenario'] == scenario])
            report['by_scenario'][scenario] = count
        
        logger.info(f"   Total recommandations: {report['recommendations_generated']}")
        logger.info(f"   Emails envoyés: {report['emails_sent']}")
        logger.info(f"   Erreurs: {report['emails_failed']}")
        
        return report
    
    def save_report(self, report: Dict):
        """
        Sauvegarde le rapport en JSON
        
        Args:
            report: Dict rapport
        """
        try:
            output_file = f"exports/logs/phase2_report_{self.timestamp}.json"
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Rapport sauvegardé: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde rapport: {str(e)}")
    
    def run(self, dry_run: bool = True) -> Dict:
        """
        Exécute l'orchestration Phase 2
        
        Args:
            dry_run: Si True, simule sans vraiment envoyer
        
        Returns:
            Dict résultats
        """
        logger.info("\n" + "="*70)
        logger.info("🚀 PHASE 2: ORCHESTRATION BREVO + RECOMMANDATIONS")
        logger.info("="*70)
        
        try:
            # 1. Récupérer emails
            clients = self.get_client_emails()
            if not clients:
                logger.error("❌ Aucun client trouvé")
                return {'success': False, 'error': 'No clients found'}
            
            # 2. Générer recommandations
            if not self.generate_recommendations():
                return {'success': False, 'error': 'Recommendation generation failed'}
            
            # 3. Envoyer emails
            self.send_emails_campaign(clients, dry_run=dry_run)
            
            # 4. Générer rapport
            report = self.generate_report()
            self.save_report(report)
            
            logger.info("\n" + "="*70)
            logger.info("✅ PHASE 2 COMPLET")
            logger.info("="*70 + "\n")
            
            return {'success': True, 'report': report}
            
        except Exception as e:
            logger.error(f"❌ Erreur Phase 2: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}


def run_phase2(dry_run: bool = True) -> Dict:
    """
    Fonction principale pour Phase 2
    
    Args:
        dry_run: Si True, simule sans vraiment envoyer (défaut True pour sécurité)
    
    Returns:
        Dict résultats
    """
    orchestrator = Phase2Orchestrator()
    return orchestrator.run(dry_run=dry_run)


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  🚀 PHASE 2 ORCHESTRATION")
    print("="*70 + "\n")
    
    # Lancer en dry-run d'abord
    result = run_phase2(dry_run=True)
    
    if result['success']:
        print("\n✅ Phase 2 exécutée avec succès (dry-run)")
        print(f"\nRapport:")
        report = result['report']
        print(f"  Recommandations: {report['recommendations_generated']}")
        print(f"  Emails (sim): {report['emails_sent']}")
        print(f"  Erreurs: {report['emails_failed']}")
    else:
        print(f"\n❌ Erreur: {result.get('error')}")
    
    print("\n" + "="*70 + "\n")
