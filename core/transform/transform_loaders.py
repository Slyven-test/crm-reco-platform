"""Load transformed data into clean tables."""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import insert, text
from core.db.models import (
    Customer, OrderLine, ContactEvent, Product, ProductAlias
)

logger = logging.getLogger(__name__)


class TransformLoader:
    """Load transformed data into clean tables."""

    def __init__(self, db: Session):
        """Initialize with database session.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def load_customers(
        self,
        customers: List[Dict],
    ) -> int:
        """Load deduplicated customers into customer table.
        
        Args:
            customers: List of deduplicated customer dicts
            
        Returns:
            Number of customers loaded
        """
        if not customers:
            return 0
        
        loaded = 0
        
        for customer_dict in customers:
            try:
                # Create Customer model instance
                customer = Customer(
                    customer_code=customer_dict.get('customer_code'),
                    first_name=customer_dict.get('first_name'),
                    last_name=customer_dict.get('last_name'),
                    email=customer_dict.get('email'),
                    phone=customer_dict.get('phone'),
                    address=customer_dict.get('address'),
                    postal_code=customer_dict.get('postal_code'),
                    city=customer_dict.get('city'),
                    country=customer_dict.get('country'),
                    bounced=False,
                    optout=False,
                    contactable=True,
                )
                
                self.db.add(customer)
                loaded += 1
                
            except Exception as e:
                logger.warning(f"Failed to load customer {customer_dict.get('customer_code')}: {str(e)}")
        
        self.db.commit()
        logger.info(f"Loaded {loaded} customers")
        return loaded

    def load_order_lines(
        self,
        order_lines: List[Dict],
        product_resolver,  # ProductResolver instance
    ) -> int:
        """Load order lines into order_line table.
        
        Args:
            order_lines: List of order line dicts from raw_sales_lines
            product_resolver: ProductResolver to resolve product keys
            
        Returns:
            Number of order lines loaded
        """
        if not order_lines:
            return 0
        
        loaded = 0
        
        for line_dict in order_lines:
            try:
                # Resolve product
                product_key, resolve_error = product_resolver.resolve(
                    line_dict.get('product_label_norm'),
                    line_dict.get('product_label')
                )
                
                if not product_key:
                    logger.warning(f"Cannot resolve product for line: {line_dict}")
                    continue
                
                # Parse date
                order_date_str = line_dict.get('order_date')
                order_date = datetime.fromisoformat(order_date_str).date() if order_date_str else None
                
                # Create OrderLine model instance
                order_line = OrderLine(
                    customer_code=line_dict.get('customer_code'),
                    order_date=order_date,
                    doc_ref=line_dict.get('doc_ref'),
                    doc_type=line_dict.get('doc_type'),
                    product_key=product_key,
                    qty=line_dict.get('qty'),
                    amount_ht=line_dict.get('amount_ht'),
                    amount_ttc=line_dict.get('amount_ttc'),
                    margin=line_dict.get('margin'),
                )
                
                self.db.add(order_line)
                loaded += 1
                
            except Exception as e:
                logger.warning(f"Failed to load order line: {str(e)}")
        
        self.db.commit()
        logger.info(f"Loaded {loaded} order lines")
        return loaded

    def load_contact_events(
        self,
        contacts: List[Dict],
    ) -> int:
        """Load contact events into contact_event table.
        
        Args:
            contacts: List of contact dicts from raw_contacts
            
        Returns:
            Number of contact events loaded
        """
        if not contacts:
            return 0
        
        loaded = 0
        
        for contact_dict in contacts:
            try:
                # Parse date
                contact_date_str = contact_dict.get('contact_date')
                contact_date = datetime.fromisoformat(contact_date_str).date() if contact_date_str else None
                
                # Create ContactEvent model instance
                contact_event = ContactEvent(
                    customer_code=contact_dict.get('customer_code'),
                    contact_date=contact_date,
                    channel=contact_dict.get('channel'),
                    status=contact_dict.get('status'),
                    campaign_id=contact_dict.get('campaign_id'),
                )
                
                self.db.add(contact_event)
                loaded += 1
                
            except Exception as e:
                logger.warning(f"Failed to load contact event: {str(e)}")
        
        self.db.commit()
        logger.info(f"Loaded {loaded} contact events")
        return loaded


class ClientMasterProfileLoader:
    """Create client master profiles from clean tables."""

    def __init__(self, db: Session):
        """Initialize with database session.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def compute_rfm_scores(
        self,
        customer_code: str,
    ) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """Compute RFM (Recency, Frequency, Monetary) scores.
        
        Args:
            customer_code: Customer code
            
        Returns:
            Tuple of (recency_score, frequency_score, monetary_score)
            - 1-5 scores (5=best)
        """
        try:
            # Get RFM data
            result = self.db.execute(text("""
                WITH rfm AS (
                    SELECT 
                        customer_code,
                        MAX(order_date) as last_order_date,
                        COUNT(*) as order_count,
                        SUM(amount_ht) as total_amount
                    FROM order_line
                    WHERE customer_code = :customer_code
                    GROUP BY customer_code
                )
                SELECT 
                    last_order_date,
                    order_count,
                    total_amount
                FROM rfm
            """), {'customer_code': customer_code})
            
            row = result.fetchone()
            if not row:
                return None, None, None
            
            # For now, return placeholder scores
            # In production, would use quartile binning
            recency = 3 if row[0] else None
            frequency = 3 if row[1] else None
            monetary = 3 if row[2] else None
            
            return recency, frequency, monetary
            
        except Exception as e:
            logger.warning(f"Failed to compute RFM for {customer_code}: {str(e)}")
            return None, None, None

    def build_profiles(
        self,
    ) -> int:
        """Build client master profiles for all customers.
        
        Returns:
            Number of profiles created
        """
        logger.info("Starting client master profile computation")
        
        try:
            # Get all customers
            result = self.db.execute(text("""
                SELECT customer_code
                FROM customer
            """))
            
            customer_codes = [row[0] for row in result]
            logger.info(f"Processing {len(customer_codes)} customers")
            
            created = 0
            
            for customer_code in customer_codes:
                try:
                    # Compute RFM
                    recency, frequency, monetary = self.compute_rfm_scores(customer_code)
                    
                    # Create profile (simplified for now)
                    # In production, would compute full feature set
                    self.db.execute(text("""
                        INSERT INTO client_master_profile
                        (customer_code, rfm_score, segment)
                        VALUES (:customer_code, :rfm_score, :segment)
                        ON CONFLICT (customer_code) DO UPDATE
                        SET rfm_score = :rfm_score, segment = :segment
                    """), {
                        'customer_code': customer_code,
                        'rfm_score': (recency or 0) + (frequency or 0) + (monetary or 0),
                        'segment': 'STANDARD',  # Placeholder
                    })
                    
                    created += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to create profile for {customer_code}: {str(e)}")
            
            self.db.commit()
            logger.info(f"Created {created} client master profiles")
            return created
            
        except Exception as e:
            logger.error(f"Failed to build profiles: {str(e)}")
            return 0
