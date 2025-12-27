"""
Connector Manager

Orchestration des connecteurs interchangeables.

Responsabilités:
  - Enregistrer et gérer les connecteurs disponibles
  - Charger/sauvegarder config
  - Lancer syncs
  - Tracker l'état et l'historique
  - Expose API REST pour UI
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from .base_connector import BaseConnector, ConnectorType, ConnectorStatus, SyncResult
from .odoo_connector import OdooConnector
from .isavigne_connector import iSaVigneConnector

logger = logging.getLogger(__name__)


class ConnectorManager:
    """
    Gestionnaire centralisé des connecteurs.

    Permet:
    - Créer/détruire connecteurs
    - Lancer syncs
    - Tracker état
    - Gérer config et secrets
    """

    def __init__(self, config_file: str = ".env"):
        """
        Initialiser le gestionnaire.

        Args:
            config_file: Chemin fichier config (JSON) ou .env
        """
        self.config_file = config_file
        self.connectors: Dict[str, BaseConnector] = {}
        self.sync_history: List[Dict[str, Any]] = []
        self.config = {}

        logger.info("ConnectorManager initialized")

    def load_config(self) -> Dict[str, Any]:
        """
        Charger la configuration depuis fichier.

        Supporte:
        - .env (KEY=VALUE)
        - .json (JSON object)

        Returns:
            Config dict
        """
        try:
            path = Path(self.config_file)

            if self.config_file.endswith(".json"):
                with open(path, "r") as f:
                    self.config = json.load(f)
            else:
                # Parse .env
                self.config = {}
                with open(path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            key, value = line.split("=", 1)
                            self.config[key.strip()] = value.strip()

            logger.info(f"Config loaded from {self.config_file}")
            return self.config

        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_file}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            return {}

    def save_config(self, config: Dict[str, Any]):
        """
        Sauvegarder la configuration.

        Args:
            config: Config dict à sauvegarder
        """
        try:
            path = Path(self.config_file)

            if self.config_file.endswith(".json"):
                with open(path, "w") as f:
                    json.dump(config, f, indent=2)
            else:
                # Sauvegarder comme .env
                with open(path, "w") as f:
                    for key, value in config.items():
                        f.write(f"{key}={value}\n")

            logger.info(f"Config saved to {self.config_file}")
            self.config = config

        except Exception as e:
            logger.error(f"Failed to save config: {str(e)}")

    def register_connector(
        self,
        connector_name: str,
        connector_type: ConnectorType,
        config: Dict[str, Any],
    ) -> bool:
        """
        Enregistrer un nouveau connecteur.

        Args:
            connector_name: Nom du connecteur (ex: "isavigne_prod")
            connector_type: Type (ODOO, ISAVIGNE)
            config: Configuration du connecteur

        Returns:
            True si OK
        """
        try:
            # Créer l'instance appropriée
            if connector_type == ConnectorType.ODOO:
                connector = OdooConnector(config)
            elif connector_type == ConnectorType.ISAVIGNE:
                connector = iSaVigneConnector(config)
            else:
                raise ValueError(f"Unknown connector type: {connector_type}")

            # Enregistrer
            self.connectors[connector_name] = connector
            logger.info(f"Connector registered: {connector_name} ({connector_type.value})")

            return True

        except Exception as e:
            logger.error(f"Failed to register connector: {str(e)}")
            return False

    def get_connector(self, connector_name: str) -> Optional[BaseConnector]:
        """
        Récupérer un connecteur enregistré.

        Args:
            connector_name: Nom du connecteur

        Returns:
            Instance du connecteur ou None
        """
        return self.connectors.get(connector_name)

    def list_connectors(self) -> Dict[str, Dict[str, Any]]:
        """
        Lister tous les connecteurs avec leur statut.

        Returns:
            Dict {name: {type, status, last_sync, ...}}
        """
        return {
            name: connector.get_status()
            for name, connector in self.connectors.items()
        }

    def test_connector(self, connector_name: str) -> bool:
        """
        Tester la connexion d'un connecteur.

        Args:
            connector_name: Nom du connecteur

        Returns:
            True si test OK
        """
        try:
            connector = self.get_connector(connector_name)
            if not connector:
                logger.error(f"Connector not found: {connector_name}")
                return False

            return connector.test_connection()

        except Exception as e:
            logger.error(f"Test failed for {connector_name}: {str(e)}")
            return False

    def sync_connector(
        self,
        connector_name: str,
        **kwargs
    ) -> SyncResult:
        """
        Lancer une synchronisation complète (extract → transform → load).

        Args:
            connector_name: Nom du connecteur
            **kwargs: Paramètres pour la sync

        Returns:
            SyncResult avec stats et erreurs
        """
        try:
            connector = self.get_connector(connector_name)
            if not connector:
                logger.error(f"Connector not found: {connector_name}")
                return SyncResult(
                    success=False,
                    connector_type=None,
                    timestamp=datetime.now(),
                    records_processed={},
                    errors=[f"Connector not found: {connector_name}"],
                )

            logger.info(f"Starting sync for {connector_name}")
            result = connector.sync(**kwargs)

            # Enregistrer dans l'historique
            self.sync_history.append({
                "connector_name": connector_name,
                "connector_type": result.connector_type.value,
                "timestamp": result.timestamp.isoformat(),
                "success": result.success,
                "records_processed": result.records_processed,
                "duration_seconds": result.duration_seconds,
                "errors": result.errors,
                "warnings": result.warnings,
            })

            return result

        except Exception as e:
            logger.error(f"Sync failed for {connector_name}: {str(e)}")
            return SyncResult(
                success=False,
                connector_type=None,
                timestamp=datetime.now(),
                records_processed={},
                errors=[str(e)],
            )

    def get_sync_history(
        self,
        connector_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Récupérer l'historique des syncs.

        Args:
            connector_name: Filtrer par connecteur (optionnel)
            limit: Nombre max de records

        Returns:
            Liste d'entrées d'historique
        """
        history = self.sync_history

        if connector_name:
            history = [h for h in history if h["connector_name"] == connector_name]

        return history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """
        Obtenir le statut global du système.

        Returns:
            Dict avec stats générales
        """
        total_syncs = len(self.sync_history)
        successful_syncs = sum(1 for h in self.sync_history if h["success"])
        failed_syncs = total_syncs - successful_syncs

        avg_duration = 0.0
        if self.sync_history:
            avg_duration = sum(
                h.get("duration_seconds", 0) for h in self.sync_history
            ) / len(self.sync_history)

        return {
            "connectors_registered": len(self.connectors),
            "connectors_by_status": self._group_by_status(),
            "total_syncs": total_syncs,
            "successful_syncs": successful_syncs,
            "failed_syncs": failed_syncs,
            "avg_sync_duration_seconds": round(avg_duration, 2),
            "last_sync_time": (
                self.sync_history[-1]["timestamp"] if self.sync_history else None
            ),
        }

    def _group_by_status(self) -> Dict[str, int]:
        """
        Grouper connecteurs par statut.

        Returns:
            {status: count}
        """
        from collections import Counter

        statuses = [c.status.value for c in self.connectors.values()]
        return dict(Counter(statuses))

    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtenir les métriques d'exécution.

        Returns:
            Dict avec métriques détaillées
        """
        total_records = 0
        records_by_type = {}

        for sync in self.sync_history:
            for table, count in sync.get("records_processed", {}).items():
                total_records += count
                records_by_type[table] = records_by_type.get(table, 0) + count

        return {
            "total_records_synced": total_records,
            "records_by_table": records_by_type,
            "total_errors": sum(
                len(h.get("errors", [])) for h in self.sync_history
            ),
            "total_warnings": sum(
                len(h.get("warnings", [])) for h in self.sync_history
            ),
        }

    def export_status_json(self, filepath: str):
        """
        Exporter le statut en JSON.

        Args:
            filepath: Chemin fichier
        """
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "overview": self.get_status(),
                "metrics": self.get_metrics(),
                "connectors": self.list_connectors(),
                "recent_syncs": self.get_sync_history(limit=10),
            }

            with open(filepath, "w") as f:
                json.dump(status, f, indent=2, default=str)

            logger.info(f"Status exported to {filepath}")

        except Exception as e:
            logger.error(f"Failed to export status: {str(e)}")


print("✓ ConnectorManager loaded")
