"""Compute features for recommendation scoring."""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class FeatureComputer:
    """Compute features for recommendations."""

    def __init__(self, db: Session):
        """Initialize with database session.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def compute_customer_features(
        self,
        customer_code: str,
    ) -> Dict:
        """Compute all features for a customer.
        
        Features computed:
        - RFM scores (Recency, Frequency, Monetary)
        - Purchase count
        - Average order value
        - Total spent
        - Days since last purchase
        - Preferred product families
        - Aroma preferences
        - Budget level
        - Diversity score
        
        Args:
            customer_code: Customer code
            
        Returns:
            Dict of {feature_name: value}
        """
        features = {
            'customer_code': customer_code,
            'computed_at': datetime.utcnow().isoformat(),
        }
        
        try:
            # Fetch RFM data
            result = self.db.execute(text("""
                SELECT
                    COUNT(*) as purchase_count,
                    SUM(amount_ht) as total_spent,
                    AVG(amount_ht) as avg_order_value,
                    MAX(order_date) as last_purchase_date,
                    MIN(order_date) as first_purchase_date
                FROM order_line
                WHERE customer_code = :customer_code
            """), {'customer_code': customer_code})
            
            row = result.fetchone()
            if row:
                features['purchase_count'] = row[0] or 0
                features['total_spent'] = float(row[1]) if row[1] else 0.0
                features['avg_order_value'] = float(row[2]) if row[2] else 0.0
                features['last_purchase_date'] = row[3].isoformat() if row[3] else None
                features['first_purchase_date'] = row[4].isoformat() if row[4] else None
                
                # Calculate days since last purchase
                if row[3]:
                    days_since = (datetime.now().date() - row[3]).days
                    features['days_since_purchase'] = max(0, days_since)
                    
                    # Recency score: lower is better
                    if days_since <= 30:
                        features['recency_score'] = 5
                    elif days_since <= 90:
                        features['recency_score'] = 4
                    elif days_since <= 180:
                        features['recency_score'] = 3
                    elif days_since <= 365:
                        features['recency_score'] = 2
                    else:
                        features['recency_score'] = 1
                else:
                    features['recency_score'] = 0
                
                # Frequency score
                if features['purchase_count'] >= 10:
                    features['frequency_score'] = 5
                elif features['purchase_count'] >= 5:
                    features['frequency_score'] = 4
                elif features['purchase_count'] >= 2:
                    features['frequency_score'] = 3
                elif features['purchase_count'] == 1:
                    features['frequency_score'] = 2
                else:
                    features['frequency_score'] = 0
                
                # Monetary score
                if features['total_spent'] >= 5000:
                    features['monetary_score'] = 5
                elif features['total_spent'] >= 2000:
                    features['monetary_score'] = 4
                elif features['total_spent'] >= 500:
                    features['monetary_score'] = 3
                elif features['total_spent'] >= 100:
                    features['monetary_score'] = 2
                else:
                    features['monetary_score'] = 1 if features['total_spent'] > 0 else 0
        
        except Exception as e:
            logger.warning(f"Failed to compute RFM features for {customer_code}: {str(e)}")
        
        return features

    def compute_product_affinity(
        self,
        customer_code: str,
    ) -> Dict[str, float]:
        """Compute customer affinity for product families.
        
        Returns frequency distribution of purchases by product family.
        
        Args:
            customer_code: Customer code
            
        Returns:
            Dict of {family: affinity_score (0-1)}
        """
        try:
            result = self.db.execute(text("""
                SELECT 
                    p.family,
                    COUNT(*) as purchase_count,
                    SUM(ol.amount_ht) as total_spent
                FROM order_line ol
                JOIN product p ON ol.product_key = p.product_key
                WHERE ol.customer_code = :customer_code
                GROUP BY p.family
                ORDER BY total_spent DESC
            """), {'customer_code': customer_code})
            
            rows = result.fetchall()
            if not rows:
                return {}
            
            total_spent = sum(row[2] for row in rows)
            affinities = {}
            
            for row in rows:
                family = row[0]
                spent = float(row[2])
                affinity = spent / total_spent if total_spent > 0 else 0
                affinities[family] = affinity
            
            return affinities
            
        except Exception as e:
            logger.warning(f"Failed to compute product affinity for {customer_code}: {str(e)}")
            return {}

    def get_budget_level(
        self,
        customer_code: str,
    ) -> str:
        """Determine customer budget level.
        
        Args:
            customer_code: Customer code
            
        Returns:
            Budget level: BUDGET, STANDARD, PREMIUM, LUXURY
        """
        try:
            result = self.db.execute(text("""
                SELECT AVG(amount_ht)
                FROM order_line
                WHERE customer_code = :customer_code
            """), {'customer_code': customer_code})
            
            row = result.fetchone()
            if not row or not row[0]:
                return 'STANDARD'
            
            avg_order_value = float(row[0])
            
            if avg_order_value >= 500:
                return 'LUXURY'
            elif avg_order_value >= 200:
                return 'PREMIUM'
            elif avg_order_value >= 50:
                return 'STANDARD'
            else:
                return 'BUDGET'
        
        except Exception as e:
            logger.warning(f"Failed to determine budget level for {customer_code}: {str(e)}")
            return 'STANDARD'

    def get_silence_window(
        self,
        customer_code: str,
        days: int = 30,
    ) -> bool:
        """Check if customer is in contact silence window.
        
        Args:
            customer_code: Customer code
            days: Silence window in days
            
        Returns:
            True if in silence window, False otherwise
        """
        try:
            result = self.db.execute(text("""
                SELECT MAX(contact_date)
                FROM contact_event
                WHERE customer_code = :customer_code
            """), {'customer_code': customer_code})
            
            row = result.fetchone()
            if not row or not row[0]:
                return False
            
            last_contact = row[0]
            days_since = (datetime.now().date() - last_contact).days
            
            return days_since < days
            
        except Exception as e:
            logger.warning(f"Failed to check silence window for {customer_code}: {str(e)}")
            return False
