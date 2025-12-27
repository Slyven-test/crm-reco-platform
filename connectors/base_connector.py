"""
Base Abstract Connector

Classe mère pour tous les connecteurs.
Définit l'interface commune et les méthodes obligatoires.
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConnectorType(Enum):
    """Types de connecteurs supportés"""
    ODOO = "odoo"
    ISAVIGNE = "isavigne"
    BREVO = "brevo"
    MANUAL = "manual"


class ConnectorStatus(Enum):
    """Status d'un connecteur"""
    HEALTHY = "healthy"
    ERROR = "error"
    SYNCING = "syncing"
    IDLE = "idle"
    CONFIGURING = "configuring"


@dataclass
class SyncResult:
    """Résultat d'une synchronisation"""
    success: bool
    connector_type: ConnectorType
    timestamp: datetime
    records_processed: Dict[str, int]  # {"customers": 150, "products": 45, ...}
    errors: List[str] = None
    warnings: List[str] = None
    last_sync_cursor: Optional[Dict[str, Any]] = None  # pour incrémental
    duration_seconds: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BaseConnector(ABC):
    """
    Classe de base abstraite pour tous les connecteurs.

    Un connecteur doit pouvoir:
    1. Se configurer (credentials, endpoints, etc)
    2. Tester la connexion
    3. Extraire les données (extract)
    4. Les transformer vers le schéma canonique (transform)
    5. Les charger en base (load)
    6. Gérer les états de synchronisation
    """

    def __init__(self, connector_type: ConnectorType, config: Dict[str, Any]):
        """
        Initialiser un connecteur.

        Args:
            connector_type: Type du connecteur (ODOO, ISAVIGNE, etc)
            config: Configuration (credentials, endpoints, etc)
        """
        self.connector_type = connector_type
        self.config = config
        self.status = ConnectorStatus.CONFIGURING
        self.last_sync: Optional[datetime] = None
        self.last_error: Optional[str] = None
        logger.info(f"Initializing {connector_type.value} connector")

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Tester la connexion au système source.

        Returns:
            True si connexion OK, False sinon
        """
        pass

    @abstractmethod
    def extract(self, source: str = None, **kwargs) -> Dict[str, List[Dict]]:
        """
        Extraire les données brutes du système source.

        Args:
            source: Type de données (à extraire ("customers", "products", "sales_lines", etc)
            **kwargs: Paramètres additionnels (filters, date_from, etc)

        Returns:
            Dict avec clés = source names, valeurs = listes de records bruts
            Ex: {"customers": [...], "products": [...], "sales_lines": [...]}
        """
        pass

    @abstractmethod
    def transform(self, raw_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Transformer les données brutes vers le schéma canonique.

        Args:
            raw_data: Données brutes de extract()

        Returns:
            Dict avec clés = tables canoniques (CUSTOMERS, PRODUCTS, etc)
            valeurs = listes de records normalisés
        """
        pass

    @abstractmethod
    def load(self, canonical_data: Dict[str, List[Dict]], **kwargs) -> SyncResult:
        """
        Charger les données canoniques en base de données.

        Args:
            canonical_data: Données canoniques de transform()
            **kwargs: Paramètres (upsert=True, truncate=False, etc)

        Returns:
            SyncResult avec stats et erreurs
        """
        pass

    def sync(self, **kwargs) -> SyncResult:
        """
        Cycle complet: extract → transform → load.

        Args:
            **kwargs: Paramètres pour extract et load

        Returns:
            SyncResult avec stats complètes
        """
        start_time = datetime.now()
        self.status = ConnectorStatus.SYNCING

        try:
            # Step 1: Extract
            logger.info(f"Extracting data from {self.connector_type.value}")
            raw_data = self.extract(**kwargs)

            # Step 2: Transform
            logger.info("Transforming to canonical schema")
            canonical_data = self.transform(raw_data)

            # Step 3: Load
            logger.info("Loading to database")
            result = self.load(canonical_data, **kwargs)

            # Set success
            result.success = True
            result.connector_type = self.connector_type
            result.timestamp = datetime.now()
            result.duration_seconds = (datetime.now() - start_time).total_seconds()

            # Update state
            self.last_sync = result.timestamp
            self.status = ConnectorStatus.HEALTHY

            logger.info(
                f"Sync completed successfully in {result.duration_seconds:.1f}s. "
                f"Records: {result.records_processed}"
            )

            return result

        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.last_error = error_msg
            self.status = ConnectorStatus.ERROR

            return SyncResult(
                success=False,
                connector_type=self.connector_type,
                timestamp=datetime.now(),
                records_processed={},
                errors=[error_msg],
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

    def get_status(self) -> Dict[str, Any]:
        """
        Obtenir le statut actuel du connecteur.

        Returns:
            Dict avec status, last_sync, last_error, etc
        """
        return {
            "connector_type": self.connector_type.value,
            "status": self.status.value,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_error": self.last_error,
        }

    def validate_config(self) -> bool:
        """
        Valider la configuration.

        Returns:
            True si config valide

        Raises:
            ValueError si config invalide
        """
        required_keys = self.get_required_config_keys()
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                raise ValueError(f"Missing required config key: {key}")
        return True

    @abstractmethod
    def get_required_config_keys(self) -> List[str]:
        """
        Retourner les clés de config obligatoires pour ce connecteur.

        Returns:
            Liste de clés (ex: ["odoo_url", "odoo_db", "odoo_user"])
        """
        pass


print("✅ BaseConnector loaded")
