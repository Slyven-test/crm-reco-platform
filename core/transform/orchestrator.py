"""Orchestrate the complete transform pipeline."""

import logging
import uuid
from typing import Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from core.transform.product_resolver import ProductResolver
from core.transform.customer_deduplicator import CustomerDeduplicator
from core.transform.transform_loaders import TransformLoader, ClientMasterProfileLoader

logger = logging.getLogger(__name__)


class TransformPipelineStatus:
    """Status tracking for transform pipeline."""

    def __init__(self):
        self.customers_deduped = 0
        self.customers_loaded = 0
        self.order_lines_loaded = 0
        self.contact_events_loaded = 0
        self.master_profiles_created = 0
        self.errors: list = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def duration(self) -> Optional[float]:
        """Get pipeline duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> Dict:
        """Convert status to dict."""
        return {
            'customers_deduped': self.customers_deduped,
            'customers_loaded': self.customers_loaded,
            'order_lines_loaded': self.order_lines_loaded,
            'contact_events_loaded': self.contact_events_loaded,
            'master_profiles_created': self.master_profiles_created,
            'errors': len(self.errors),
            'duration_seconds': self.duration(),
        }


class TransformOrchestrator:
    """Orchestrate transformation from raw to clean tables."""

    def __init__(self, db: Session):
        """Initialize orchestrator.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
        self.batch_id = str(uuid.uuid4())
        self.status = TransformPipelineStatus()

    def run_full_pipeline(
        self,
        ingestion_batch_id: str,
        skip_master_profiles: bool = False,
    ) -> Tuple[TransformPipelineStatus, bool]:
        """Run complete transform pipeline.
        
        Steps:
        1. Deduplicate customers
        2. Load customers into clean table
        3. Load order lines with product resolution
        4. Load contact events
        5. Build client master profiles
        
        Args:
            ingestion_batch_id: Batch ID from ingestion step
            skip_master_profiles: Skip master profile computation (for speed)
            
        Returns:
            Tuple of (status, success)
        """
        self.status.start_time = datetime.utcnow()
        logger.info(f"Starting transform pipeline for ingestion batch {ingestion_batch_id}")
        
        try:
            # Step 1: Deduplicate customers
            logger.info("Step 1: Deduplicating customers...")
            deduplicator = CustomerDeduplicator(self.db)
            dedup_customers, duplicates_map = deduplicator.deduplicate_batch(
                ingestion_batch_id
            )
            self.status.customers_deduped = len(dedup_customers)
            logger.info(f"Deduplicated: {self.status.customers_deduped} unique customers")
            
            if not dedup_customers:
                logger.warning("No customers to deduplicate")
                self.status.end_time = datetime.utcnow()
                return self.status, False
            
            # Step 2: Load customers
            logger.info("Step 2: Loading customers...")
            loader = TransformLoader(self.db)
            self.status.customers_loaded = loader.load_customers(dedup_customers)
            
            # Step 3: Load order lines
            logger.info("Step 3: Loading order lines...")
            try:
                # Fetch raw order lines
                from sqlalchemy import text
                result = self.db.execute(text("""
                    SELECT row_data
                    FROM raw_sales_lines
                    WHERE batch_id = :batch_id
                """), {'batch_id': ingestion_batch_id})
                
                order_lines = [row[0] for row in result]
                
                # Resolve products
                product_resolver = ProductResolver(self.db)
                product_resolver.load_aliases()
                
                self.status.order_lines_loaded = loader.load_order_lines(
                    order_lines,
                    product_resolver
                )
                
            except Exception as e:
                logger.error(f"Failed to load order lines: {str(e)}")
                self.status.errors.append(f"Order lines: {str(e)}")
            
            # Step 4: Load contact events
            logger.info("Step 4: Loading contact events...")
            try:
                from sqlalchemy import text
                result = self.db.execute(text("""
                    SELECT row_data
                    FROM raw_contacts
                    WHERE batch_id = :batch_id
                """), {'batch_id': ingestion_batch_id})
                
                contacts = [row[0] for row in result]
                self.status.contact_events_loaded = loader.load_contact_events(contacts)
                
            except Exception as e:
                logger.error(f"Failed to load contact events: {str(e)}")
                self.status.errors.append(f"Contact events: {str(e)}")
            
            # Step 5: Build client master profiles
            if not skip_master_profiles:
                logger.info("Step 5: Building client master profiles...")
                try:
                    profile_loader = ClientMasterProfileLoader(self.db)
                    self.status.master_profiles_created = profile_loader.build_profiles()
                except Exception as e:
                    logger.error(f"Failed to build profiles: {str(e)}")
                    self.status.errors.append(f"Master profiles: {str(e)}")
            
            self.status.end_time = datetime.utcnow()
            success = len(self.status.errors) == 0
            
            logger.info(
                f"Transform pipeline completed in {self.status.duration():.2f}s: "
                f"{self.status.customers_loaded} customers, "
                f"{self.status.order_lines_loaded} order lines, "
                f"{self.status.contact_events_loaded} contacts"
            )
            
            return self.status, success
            
        except Exception as e:
            logger.error(f"Transform pipeline failed: {str(e)}")
            self.status.errors.append(f"Pipeline: {str(e)}")
            self.status.end_time = datetime.utcnow()
            return self.status, False

    def get_status(self) -> TransformPipelineStatus:
        """Get current pipeline status."""
        return self.status
