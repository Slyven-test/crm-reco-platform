"""Match customers to recommendation scenarios."""

import logging
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class RecoScenario(str, Enum):
    """Recommendation scenarios."""
    REBUY = "REBUY"  # Buy again same product
    CROSS_SELL = "CROSS_SELL"  # Buy related product
    UPSELL = "UPSELL"  # Buy premium version
    WINBACK = "WINBACK"  # Reactivate inactive customer
    NURTURE = "NURTURE"  # Build relationship


class ScenarioMatcher:
    """Match customers to recommendation scenarios."""

    def __init__(self, db: Session):
        """Initialize with database session.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
        self.config = {
            'rebuy_days': 90,  # Rebuy if purchased 90+ days ago
            'winback_days': 365,  # Winback if inactive 1+ year
            'cross_sell_spent_threshold': 100,  # Suggest cross-sell if spent $100+
            'upsell_spent_threshold': 500,  # Suggest upsell if spent $500+
        }

    def match_rebuy(
        self,
        customer_code: str,
    ) -> Optional[List[str]]:
        """Match customer for REBUY scenario.
        
        Criteria:
        - Has purchased before
        - Last purchase 90+ days ago
        - Recent product with good rating
        
        Args:
            customer_code: Customer code
            
        Returns:
            List of product_keys to recommend, or None
        """
        try:
            result = self.db.execute(text("""
                SELECT DISTINCT p.product_key
                FROM order_line ol
                JOIN product p ON ol.product_key = p.product_key
                WHERE ol.customer_code = :customer_code
                AND ol.order_date <= CURRENT_DATE - INTERVAL '90 days'
                AND p.popularity_score >= 0.5
                ORDER BY ol.order_date DESC
                LIMIT 3
            """), {'customer_code': customer_code})
            
            products = [row[0] for row in result]
            return products if products else None
        
        except Exception as e:
            logger.warning(f"Failed to match REBUY for {customer_code}: {str(e)}")
            return None

    def match_cross_sell(
        self,
        customer_code: str,
        exclude_products: Optional[List[str]] = None,
    ) -> Optional[List[str]]:
        """Match customer for CROSS_SELL scenario.
        
        Criteria:
        - Has spent $100+
        - Products from different families
        - High diversity potential
        
        Args:
            customer_code: Customer code
            exclude_products: Products to exclude from recommendations
            
        Returns:
            List of product_keys to recommend, or None
        """
        try:
            # Get customer's top families
            result = self.db.execute(text("""
                SELECT DISTINCT p.family
                FROM order_line ol
                JOIN product p ON ol.product_key = p.product_key
                WHERE ol.customer_code = :customer_code
                LIMIT 2
            """), {'customer_code': customer_code})
            
            customer_families = [row[0] for row in result]
            if not customer_families:
                return None
            
            # Find products from different families
            query = """
                SELECT DISTINCT p.product_key
                FROM product p
                WHERE p.family NOT IN ({families})
                AND p.popularity_score >= 0.4
                {exclude_clause}
                ORDER BY p.popularity_score DESC
                LIMIT 3
            """
            
            families_str = ','.join([f"'{f}'" for f in customer_families])
            exclude_clause = ""
            if exclude_products:
                exclude_str = ','.join([f"'{p}'" for p in exclude_products])
                exclude_clause = f"AND p.product_key NOT IN ({exclude_str})"
            
            query = query.format(families=families_str, exclude_clause=exclude_clause)
            result = self.db.execute(text(query))
            
            products = [row[0] for row in result]
            return products if products else None
        
        except Exception as e:
            logger.warning(f"Failed to match CROSS_SELL for {customer_code}: {str(e)}")
            return None

    def match_upsell(
        self,
        customer_code: str,
    ) -> Optional[List[str]]:
        """Match customer for UPSELL scenario.
        
        Criteria:
        - Has spent $500+
        - Premium products available
        - Different wine profiles
        
        Args:
            customer_code: Customer code
            
        Returns:
            List of product_keys to recommend, or None
        """
        try:
            # Check if customer meets spending threshold
            result = self.db.execute(text("""
                SELECT SUM(amount_ht)
                FROM order_line
                WHERE customer_code = :customer_code
            """), {'customer_code': customer_code})
            
            total_spent = result.fetchone()[0]
            if not total_spent or total_spent < self.config['upsell_spent_threshold']:
                return None
            
            # Find premium products
            result = self.db.execute(text("""
                SELECT p.product_key
                FROM product p
                WHERE p.is_premium = TRUE
                AND p.popularity_score >= 0.6
                ORDER BY p.popularity_score DESC
                LIMIT 3
            """))
            
            products = [row[0] for row in result]
            return products if products else None
        
        except Exception as e:
            logger.warning(f"Failed to match UPSELL for {customer_code}: {str(e)}")
            return None

    def match_winback(
        self,
        customer_code: str,
    ) -> Optional[List[str]]:
        """Match customer for WINBACK scenario.
        
        Criteria:
        - Had historical purchases
        - Inactive 1+ year
        - Global popularity products
        
        Args:
            customer_code: Customer code
            
        Returns:
            List of product_keys to recommend, or None
        """
        try:
            # Check if customer is inactive
            result = self.db.execute(text("""
                SELECT MAX(order_date)
                FROM order_line
                WHERE customer_code = :customer_code
            """), {'customer_code': customer_code})
            
            last_purchase = result.fetchone()[0]
            if not last_purchase:
                return None
            
            days_inactive = (datetime.now().date() - last_purchase).days
            if days_inactive < self.config['winback_days']:
                return None
            
            # Find globally popular products
            result = self.db.execute(text("""
                SELECT p.product_key
                FROM product p
                WHERE p.popularity_score >= 0.7
                ORDER BY p.popularity_score DESC
                LIMIT 3
            """))
            
            products = [row[0] for row in result]
            return products if products else None
        
        except Exception as e:
            logger.warning(f"Failed to match WINBACK for {customer_code}: {str(e)}")
            return None

    def match_nurture(
        self,
        customer_code: str,
    ) -> Optional[List[str]]:
        """Match customer for NURTURE scenario.
        
        Criteria:
        - New or occasional customer
        - Low total spending
        - Diverse products to explore
        
        Args:
            customer_code: Customer code
            
        Returns:
            List of product_keys to recommend, or None
        """
        try:
            result = self.db.execute(text("""
                SELECT COUNT(*), SUM(amount_ht)
                FROM order_line
                WHERE customer_code = :customer_code
            """), {'customer_code': customer_code})
            
            count, total_spent = result.fetchone()
            if not count or count > 3:  # Too established
                return None
            
            # Find products with diverse profiles
            result = self.db.execute(text("""
                SELECT p.product_key
                FROM product p
                WHERE p.popularity_score >= 0.3
                AND p.family IS NOT NULL
                ORDER BY RANDOM()
                LIMIT 3
            """))
            
            products = [row[0] for row in result]
            return products if products else None
        
        except Exception as e:
            logger.warning(f"Failed to match NURTURE for {customer_code}: {str(e)}")
            return None

    def match_scenarios(
        self,
        customer_code: str,
    ) -> Dict[RecoScenario, Optional[List[str]]]:
        """Match customer to all applicable scenarios.
        
        Args:
            customer_code: Customer code
            
        Returns:
            Dict of {scenario: products}
        """
        results = {
            RecoScenario.REBUY: self.match_rebuy(customer_code),
            RecoScenario.CROSS_SELL: self.match_cross_sell(customer_code),
            RecoScenario.UPSELL: self.match_upsell(customer_code),
            RecoScenario.WINBACK: self.match_winback(customer_code),
            RecoScenario.NURTURE: self.match_nurture(customer_code),
        }
        
        # Remove empty results
        return {k: v for k, v in results.items() if v}
