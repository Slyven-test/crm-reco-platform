"""
Moteur de Recommandations
Version: 1.0
Auteur: Projet CRM Ruhlmann

Rôle: Générer des recommandations intelligentes basées sur:
  - Analyse RFM (Recency, Frequency, Monetary)
  - Scoring co-achats
  - Règles de garde-fous
  - Logique métier viticole
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text

from etl.config import DATABASE_URL, logger


class RFMAnalyzer:
    """
    Analyse RFM (Recency, Frequency, Monetary Value)
    """
    
    def __init__(self):
        """
        Initialise l'analyseur RFM
        """
        self.engine = create_engine(DATABASE_URL)
    
    def calculate_rfm(self) -> pd.DataFrame:
        """
        Calcule les scores RFM pour tous les clients
        
        Returns:
            DataFrame avec scores RFM
        """
        logger.info("\n📊 CALCUL RFM SCORES")
        
        try:
            query = """
            SELECT 
                client_code,
                COUNT(*) as frequency,
                SUM(mt_ttc) as monetary,
                MAX(date_livraison) as last_purchase_date
            FROM etl.ventes_lignes
            GROUP BY client_code
            """
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn)
            
            logger.info(f"   Clients analysés: {len(df)}")
            
            # Convertir date en datetime
            df['last_purchase_date'] = pd.to_datetime(df['last_purchase_date'])
            
            # Calculer Recency (jours depuis dernier achat)
            today = datetime.now()
            df['recency_days'] = (today - df['last_purchase_date']).dt.days
            
            # Quantiles pour scoring
            r_quantiles = df['recency_days'].quantile([0.25, 0.5, 0.75]).values
            f_quantiles = df['frequency'].quantile([0.25, 0.5, 0.75]).values
            m_quantiles = df['monetary'].quantile([0.25, 0.5, 0.75]).values
            
            # Scores RFM (1-4, moins = mieux pour Recency)
            df['r_score'] = pd.cut(df['recency_days'], bins=[-1] + list(r_quantiles) + [np.inf], labels=[4, 3, 2, 1])
            df['f_score'] = pd.cut(df['frequency'], bins=[-1] + list(f_quantiles) + [np.inf], labels=[1, 2, 3, 4])
            df['m_score'] = pd.cut(df['monetary'], bins=[-1] + list(m_quantiles) + [np.inf], labels=[1, 2, 3, 4])
            
            # Score RFM global
            df['rfm_score'] = (df['r_score'].astype(int) + df['f_score'].astype(int) + df['m_score'].astype(int)) / 3
            
            # Segment
            df['rfm_segment'] = 'Standard'
            df.loc[df['rfm_score'] >= 3.5, 'rfm_segment'] = 'VIP'
            df.loc[df['rfm_score'] <= 1.5, 'rfm_segment'] = 'At Risk'
            df.loc[(df['recency_days'] > 180) & (df['frequency'] == 1), 'rfm_segment'] = 'Churn'
            
            logger.info(f"   VIP: {len(df[df['rfm_segment'] == 'VIP'])}")
            logger.info(f"   Standard: {len(df[df['rfm_segment'] == 'Standard'])}")
            logger.info(f"   At Risk: {len(df[df['rfm_segment'] == 'At Risk'])}")
            logger.info(f"   Churn: {len(df[df['rfm_segment'] == 'Churn'])}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul RFM: {str(e)}", exc_info=True)
            return pd.DataFrame()


class CoSalesAnalyzer:
    """
    Analyse des co-achats (cross-sell)
    """
    
    def __init__(self):
        """
        Initialise l'analyseur de co-achats
        """
        self.engine = create_engine(DATABASE_URL)
    
    def calculate_coachats(self) -> pd.DataFrame:
        """
        Calcule les paires de produits achetés ensemble
        
        Returns:
            DataFrame avec scores de co-achats
        """
        logger.info("\n📊 ANALYSE CO-ACHATS")
        
        try:
            query = """
            SELECT 
                v1.produit_key as produit_1,
                v2.produit_key as produit_2,
                COUNT(*) as coachats_count,
                MAX(v1.mt_ttc + v2.mt_ttc) as avg_ticket
            FROM etl.ventes_lignes v1
            JOIN etl.ventes_lignes v2 
                ON v1.document_id = v2.document_id 
                AND v1.produit_key < v2.produit_key
            WHERE v1.document_id IS NOT NULL
            GROUP BY v1.produit_key, v2.produit_key
            HAVING COUNT(*) >= 2
            ORDER BY COUNT(*) DESC
            LIMIT 50
            """
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn)
            
            logger.info(f"   Paires produits analysées: {len(df)}")
            
            # Score de similarité (0-1)
            if len(df) > 0:
                df['similarity_score'] = df['coachats_count'] / df['coachats_count'].max()
                logger.info(f"   Co-achats max: {df['coachats_count'].max()}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Erreur co-achats: {str(e)}", exc_info=True)
            return pd.DataFrame()


class RecommendationGenerator:
    """
    Générateur de recommandations
    """
    
    def __init__(self):
        """
        Initialise le générateur
        """
        self.engine = create_engine(DATABASE_URL)
        self.rfm_analyzer = RFMAnalyzer()
        self.coachats_analyzer = CoSalesAnalyzer()
    
    def generate_recommendations(self) -> Dict:
        """
        Génére les recommandations pour tous les clients
        
        Returns:
            Dict avec résultats
        """
        logger.info("\n" + "="*60)
        logger.info("🪧 GÉNÉRATION RECOMMANDATIONS")
        logger.info("="*60)
        
        # Calculer RFM
        rfm_df = self.rfm_analyzer.calculate_rfm()
        if rfm_df.empty:
            return {'success': False, 'error': 'RFM calculation failed'}
        
        # Calculer co-achats
        coachats_df = self.coachats_analyzer.calculate_coachats()
        
        # Générer recommandations par client
        recommendations = []
        
        for _, client_row in rfm_df.iterrows():
            client_code = client_row['client_code']
            rfm_segment = client_row['rfm_segment']
            
            # Logique par segment
            if rfm_segment == 'VIP':
                scenario = 'cross-sell'  # Cross-sell pour VIP
            elif rfm_segment == 'At Risk':
                scenario = 'rebuy'  # Rebuy pour réactiver
            elif rfm_segment == 'Churn':
                scenario = 'winback'  # Win-back pour inactifs
            else:
                scenario = 'cross-sell'
            
            # Trouver les produits recommandés
            products = self._find_products_for_client(
                client_code,
                scenario,
                coachats_df
            )
            
            if products:
                rec = {
                    'client_code': client_code,
                    'scenario': scenario,
                    'products': products,
                    'rfm_score': client_row['rfm_score'],
                    'segment': rfm_segment,
                    'generated_at': datetime.now().isoformat()
                }
                recommendations.append(rec)
        
        logger.info(f"\n✅ {len(recommendations)} recommandations générées")
        
        return {
            'success': True,
            'recommendations_count': len(recommendations),
            'recommendations': recommendations
        }
    
    def _find_products_for_client(
        self,
        client_code: str,
        scenario: str,
        coachats_df: pd.DataFrame
    ) -> List[Dict]:
        """
        Trouve les produits à recommander pour un client
        
        Args:
            client_code: Code client
            scenario: Type recommandation (rebuy, cross-sell, winback)
            coachats_df: DataFrame co-achats
        
        Returns:
            Liste de produits recommandés
        """
        try:
            query = """
            SELECT DISTINCT ON (v.produit_key)
                v.produit_key,
                v.produit_label,
                MAX(v.pu_ht) as price,
                COUNT(*) as popularity
            FROM etl.ventes_lignes v
            WHERE v.client_code = %s
            GROUP BY v.produit_key, v.produit_label
            ORDER BY v.produit_key, COUNT(*) DESC
            LIMIT 3
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(query),
                    {'client_code': client_code}
                )
                products = [
                    {
                        'key': row[0],
                        'name': row[1],
                        'price': float(row[2]) if row[2] else 0,
                        'popularity': row[3]
                    }
                    for row in result
                ]
            
            return products[:3]  # Top 3
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur recherche produits: {str(e)}")
            return []
    
    def save_recommendations(self, recommendations: List[Dict], output_file: Optional[str] = None):
        """
        Sauvegarde les recommandations en JSON/CSV
        
        Args:
            recommendations: Liste recommandations
            output_file: Fichier de sortie
        """
        if not recommendations:
            logger.warning("⚠️ Aucune recommandation à sauvegarder")
            return
        
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"exports/recommendations_{timestamp}.json"
        
        try:
            import json
            from pathlib import Path
            
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(recommendations, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Recommandations sauvegardées: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde: {str(e)}")


def run_recommendation_pipeline() -> Dict:
    """
    Fonction principale pour exécuter le pipeline de recommandations
    
    Returns:
        Dict avec résultats
    """
    logger.info("\n" + "="*60)
    logger.info("🪧 PIPELINE RECOMMANDATIONS")
    logger.info("="*60)
    
    try:
        generator = RecommendationGenerator()
        result = generator.generate_recommendations()
        
        if result['success']:
            generator.save_recommendations(result['recommendations'])
        
        logger.info("\n✅ Pipeline recommandations terminé")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur pipeline: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  🪧 TEST MOTEUR RECOMMANDATIONS")
    print("="*70 + "\n")
    
    result = run_recommendation_pipeline()
    
    if result['success']:
        print(f"\n✅ {result['recommendations_count']} recommandations générées")
    else:
        print(f"\n❌ Erreur: {result.get('error')}")
    
    print("\n" + "="*70 + "\n")
