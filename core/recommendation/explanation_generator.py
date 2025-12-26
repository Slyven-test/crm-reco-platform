"""Generate human-readable explanations for recommendations."""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class Explanation:
    """Explanation for a recommendation."""
    title: str  # Short title
    reason: str  # Why recommended
    components: List[str]  # List of reasons
    
    def to_dict(self) -> Dict:
        """Convert to dict."""
        return {
            'title': self.title,
            'reason': self.reason,
            'components': self.components,
        }


class ExplanationGenerator:
    """Generate explanations for recommendations."""

    def __init__(self, db: Session):
        """Initialize with database session.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def get_product_info(
        self,
        product_key: str,
    ) -> Dict:
        """Fetch product information.
        
        Args:
            product_key: Product key
            
        Returns:
            Dict with product details
        """
        try:
            result = self.db.execute(text("""
                SELECT 
                    product_key, product_name, family, 
                    aroma_axes, premium_tier, vintage
                FROM product
                WHERE product_key = :pk
            """), {'pk': product_key})
            
            row = result.fetchone()
            if not row:
                return {}
            
            return {
                'product_key': row[0],
                'product_name': row[1],
                'family': row[2],
                'aroma_axes': row[3],
                'premium_tier': row[4],
                'vintage': row[5],
            }
        
        except Exception as e:
            logger.warning(f"Failed to get product info: {str(e)}")
            return {}

    def generate_rebuy_explanation(
        self,
        customer_code: str,
        product_key: str,
    ) -> Explanation:
        """Generate explanation for REBUY scenario.
        
        Args:
            customer_code: Customer code
            product_key: Product key
            
        Returns:
            Explanation object
        """
        product = self.get_product_info(product_key)
        components = []
        
        try:
            # Check last purchase of this product
            result = self.db.execute(text("""
                SELECT MAX(order_date), COUNT(*)
                FROM order_line
                WHERE customer_code = :customer_code
                AND product_key = :product_key
            """), {'customer_code': customer_code, 'product_key': product_key})
            
            last_date, count = result.fetchone()
            if last_date:
                components.append(f"You previously bought {product.get('product_name', product_key)}")
                components.append(f"Last purchase was {(pd.Timestamp.now() - pd.Timestamp(last_date)).days} days ago")
        
        except Exception as e:
            logger.debug(f"Failed to get purchase history: {str(e)}")
        
        if not components:
            components.append("You loved this wine before")
        
        return Explanation(
            title=f"Get your favorite {product.get('family', 'wine')} again",
            reason=f"You've purchased {product.get('product_name', 'this wine')} before and it's time for more!",
            components=components,
        )

    def generate_cross_sell_explanation(
        self,
        customer_code: str,
        product_key: str,
    ) -> Explanation:
        """Generate explanation for CROSS_SELL scenario.
        
        Args:
            customer_code: Customer code
            product_key: Product key
            
        Returns:
            Explanation object
        """
        product = self.get_product_info(product_key)
        components = []
        
        try:
            # Get customer's favorite family
            result = self.db.execute(text("""
                SELECT p.family
                FROM order_line ol
                JOIN product p ON ol.product_key = p.product_key
                WHERE ol.customer_code = :customer_code
                GROUP BY p.family
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """), {'customer_code': customer_code})
            
            fav_family = result.fetchone()
            if fav_family:
                components.append(f"Expand from {fav_family[0]} to explore {product.get('family', 'new varieties')}")
        
        except Exception as e:
            logger.debug(f"Failed to get customer families: {str(e)}")
        
        if not components:
            components.append(f"Discover {product.get('family', 'a new style')}")
        
        components.append("Perfect complement to your collection")
        
        return Explanation(
            title=f"Explore a new style: {product.get('family', 'wine')}",
            reason=f"Based on your preferences, you might enjoy {product.get('product_name', 'this wine')}.",
            components=components,
        )

    def generate_upsell_explanation(
        self,
        customer_code: str,
        product_key: str,
    ) -> Explanation:
        """Generate explanation for UPSELL scenario.
        
        Args:
            customer_code: Customer code
            product_key: Product key
            
        Returns:
            Explanation object
        """
        product = self.get_product_info(product_key)
        components = []
        
        premium = product.get('premium_tier', 'Premium')
        components.append(f"Experience {premium} quality")
        components.append("Enhanced flavors and complexity")
        
        return Explanation(
            title=f"Upgrade to {product.get('product_name', 'our premium selection')}",
            reason=f"As a valued customer, we'd like to offer you {product.get('product_name', 'something special')} - our premium selection.",
            components=components,
        )

    def generate_winback_explanation(
        self,
        customer_code: str,
        product_key: str,
    ) -> Explanation:
        """Generate explanation for WINBACK scenario.
        
        Args:
            customer_code: Customer code
            product_key: Product key
            
        Returns:
            Explanation object
        """
        product = self.get_product_info(product_key)
        components = [
            "We've missed you!",
            f"Try {product.get('product_name', 'this wine')} - a customer favorite",
        ]
        
        return Explanation(
            title="Come back and discover what's new",
            reason=f"We'd love to welcome you back with {product.get('product_name', 'something special')}.",
            components=components,
        )

    def generate_nurture_explanation(
        self,
        customer_code: str,
        product_key: str,
    ) -> Explanation:
        """Generate explanation for NURTURE scenario.
        
        Args:
            customer_code: Customer code
            product_key: Product key
            
        Returns:
            Explanation object
        """
        product = self.get_product_info(product_key)
        components = [
            f"Perfect entry point to {product.get('family', 'wines')}",
            "Great value and quality",
            "Recommended for enthusiasts",
        ]
        
        return Explanation(
            title=f"Expand your palate with {product.get('product_name', 'this wine')}",
            reason=f"Discover {product.get('product_name', 'this wine')} - a great way to explore new flavors.",
            components=components,
        )

    def generate_explanation(
        self,
        customer_code: str,
        product_key: str,
        scenario: str,
    ) -> Explanation:
        """Generate appropriate explanation for scenario.
        
        Args:
            customer_code: Customer code
            product_key: Product key
            scenario: Recommendation scenario
            
        Returns:
            Explanation object
        """
        if scenario == "REBUY":
            return self.generate_rebuy_explanation(customer_code, product_key)
        elif scenario == "CROSS_SELL":
            return self.generate_cross_sell_explanation(customer_code, product_key)
        elif scenario == "UPSELL":
            return self.generate_upsell_explanation(customer_code, product_key)
        elif scenario == "WINBACK":
            return self.generate_winback_explanation(customer_code, product_key)
        elif scenario == "NURTURE":
            return self.generate_nurture_explanation(customer_code, product_key)
        else:
            return Explanation(
                title="Recommended for you",
                reason="Based on your preferences",
                components=["Carefully selected"],
            )
