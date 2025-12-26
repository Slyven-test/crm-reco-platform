"""Product alias resolution and product key mapping."""

import logging
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ProductResolver:
    """Resolve product labels to product keys using alias mapping."""

    def __init__(self, db: Session):
        """Initialize with database session.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
        self._cache: Dict[str, str] = {}  # Cache {label_norm: product_key}
        self._loaded = False

    def load_aliases(self) -> Dict[str, str]:
        """Load product aliases from database.
        
        Returns:
            Dict of {label_norm: product_key}
        """
        if self._loaded:
            return self._cache
        
        try:
            result = self.db.execute(text("""
                SELECT label_norm, product_key
                FROM product_alias
                WHERE is_active = TRUE
            """))
            
            for row in result:
                label_norm = row[0]
                product_key = row[1]
                self._cache[label_norm] = product_key
            
            self._loaded = True
            logger.info(f"Loaded {len(self._cache)} product aliases")
            return self._cache
            
        except Exception as e:
            logger.error(f"Failed to load product aliases: {str(e)}")
            return {}

    def resolve(
        self,
        label_norm: str,
        product_label_original: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolve normalized product label to product key.
        
        Args:
            label_norm: Normalized product label (lowercase, spaces collapsed)
            product_label_original: Original product label for error context
            
        Returns:
            Tuple of (product_key, error_message)
            - If resolved: (product_key, None)
            - If not found: (None, error_message)
        """
        if not self._loaded:
            self.load_aliases()
        
        product_key = self._cache.get(label_norm)
        if product_key:
            return product_key, None
        
        error_msg = f"Product not found in alias mapping: {label_norm}"
        logger.debug(f"Product resolution failed: {error_msg}")
        return None, error_msg

    def resolve_batch(
        self,
        labels: Dict[str, str],  # {label_norm: product_label_original}
    ) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
        """Resolve batch of product labels.
        
        Args:
            labels: Dict of {normalized_label: original_label}
            
        Returns:
            Dict of {normalized_label: (product_key, error)}
        """
        if not self._loaded:
            self.load_aliases()
        
        results = {}
        for label_norm, label_orig in labels.items():
            results[label_norm] = self.resolve(label_norm, label_orig)
        
        return results

    def clear_cache(self):
        """Clear the alias cache."""
        self._cache.clear()
        self._loaded = False
