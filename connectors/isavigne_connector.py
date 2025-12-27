"""
Connecteur iSaVigne

Intégration avec iSaVigne par exports CSV/Excel.
Lit les fichiers d'export automatisés et normalise vers schéma canonique.

Configuration requise:
  - isavigne_export_path: Chemin dossier contenant les exports
                         (ex: "/mnt/shared/isavigne_exports")
  - isavigne_file_pattern: Pattern de noms fichiers (ex: "*.csv")
  - encoding: Encodage des fichiers (default: "utf-8")
  - normalize_accents: Si True, supprime accents (default: True)
"""

import os
import glob
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import re
import unicodedata

from .base_connector import BaseConnector, ConnectorType, ConnectorStatus, SyncResult
from .canonical_schema import (
    CanonicalSchema,
    ProductCatalog,
    Customer,
    SalesLine,
    StockLevel,
    ProductCategory,
    PriceSegment,
    CustomerSegment,
)

logger = logging.getLogger(__name__)


class iSaVigneConnector(BaseConnector):
    """
    Connecteur iSaVigne utilisant des exports CSV/Excel.

    Méthodes:
    - test_connection(): Vérifie que dossier export existe
    - extract(): Lit les fichiers CSV
    - transform(): Map vers schéma canonique
    - load(): Sauvegarde en base
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialiser le connecteur iSaVigne.

        Args:
            config: Dict avec isavigne_export_path, file_pattern, encoding, etc
        """
        super().__init__(ConnectorType.ISAVIGNE, config)
        self.validate_config()

        self.export_path = config["isavigne_export_path"]
        self.file_pattern = config.get("isavigne_file_pattern", "*.csv")
        self.encoding = config.get("encoding", "utf-8")
        self.normalize_accents = config.get("normalize_accents", True)

        logger.info(f"iSaVigne Connector configured for {self.export_path}")

    def get_required_config_keys(self) -> List[str]:
        """Clés requises"""
        return ["isavigne_export_path"]

    def test_connection(self) -> bool:
        """
        Tester que le dossier d'export existe et est accessible.

        Returns:
            True si dossier OK

        Raises:
            ConnectionError si dossier n'existe pas
        """
        try:
            path = Path(self.export_path)

            if not path.exists():
                raise FileNotFoundError(f"Export path does not exist: {self.export_path}")

            if not path.is_dir():
                raise NotADirectoryError(f"Export path is not a directory: {self.export_path}")

            # Vérifier qu'on peut lister les fichiers
            files = list(glob.glob(os.path.join(self.export_path, self.file_pattern)))

            logger.info(f"✓ iSaVigne export path accessible ({len(files)} files)")
            self.status = ConnectorStatus.HEALTHY
            return True

        except Exception as e:
            error_msg = f"iSaVigne connection failed: {str(e)}"
            logger.error(error_msg)
            self.last_error = error_msg
            self.status = ConnectorStatus.ERROR
            raise ConnectionError(error_msg)

    def extract(self, source: str = None, **kwargs) -> Dict[str, List[Dict]]:
        """
        Extraire les données des fichiers iSaVigne CSV.

        Fichiers attendus:
        - clients.csv (ou similaire)
        - produits.csv (ou similaire)
        - ventes.csv (ou similaire)
        - stock.csv (ou similaire)

        Args:
            source: Type spécifique à extraire
            **kwargs: Params additionnels

        Returns:
            Dict avec données brutes
        """
        raw_data = {}

        # 1. Clients
        if not source or source == "customers":
            logger.info("Extracting iSaVigne customers")
            raw_data["customers"] = self._extract_csv_file(
                pattern="*client*", source_name="customers"
            )

        # 2. Produits
        if not source or source == "products":
            logger.info("Extracting iSaVigne products")
            raw_data["products"] = self._extract_csv_file(
                pattern="*produit*", source_name="products"
            )

        # 3. Ventes
        if not source or source == "sales_lines":
            logger.info("Extracting iSaVigne sales lines")
            raw_data["sales_lines"] = self._extract_csv_file(
                pattern="*vente*", source_name="sales_lines"
            )

        # 4. Stock
        if not source or source == "stock_levels":
            logger.info("Extracting iSaVigne stock levels")
            raw_data["stock_levels"] = self._extract_csv_file(
                pattern="*stock*", source_name="stock_levels"
            )

        return raw_data

    def _extract_csv_file(
        self, pattern: str, source_name: str
    ) -> List[Dict]:
        """
        Extraire et lire un fichier CSV.

        Args:
            pattern: Pattern pour glob (ex: "*client*")
            source_name: Nom du source pour logs

        Returns:
            Liste de dicts (rows de CSV)
        """
        try:
            # Trouver les fichiers correspondant au pattern
            search_path = os.path.join(self.export_path, pattern + "*")
            files = glob.glob(search_path)

            if not files:
                logger.warning(f"No {source_name} files found matching pattern: {search_path}")
                return []

            # Prendre le plus récent
            latest_file = max(files, key=os.path.getctime)
            logger.info(f"Reading {source_name} from {os.path.basename(latest_file)}")

            # Lire le CSV
            if latest_file.endswith(".xlsx"):
                df = pd.read_excel(latest_file, dtype=str)
            else:
                df = pd.read_csv(latest_file, encoding=self.encoding, dtype=str)

            # Normaliser les colonnes (lowercase, remove accents, replace spaces)
            df.columns = [
                self._normalize_string(col) for col in df.columns
            ]

            # Convertir en liste de dicts
            records = df.fillna("").to_dict("records")

            logger.info(f"Extracted {len(records)} {source_name} records")
            return records

        except Exception as e:
            logger.error(f"Failed to extract {source_name}: {str(e)}")
            return []

    def _normalize_string(
        self, s: str, remove_accents: Optional[bool] = None
    ) -> str:
        """
        Normaliser une chaîne: lowercase, trim, remove accents (optionnel).

        Args:
            s: String à normaliser
            remove_accents: Si True, supprime accents (default: config value)

        Returns:
            String normalisé
        """
        if remove_accents is None:
            remove_accents = self.normalize_accents

        # Lowercase et trim
        s = s.strip().lower()

        # Remplacer espaces par underscores
        s = s.replace(" ", "_")
        s = s.replace("-", "_")

        # Optionnel: supprimer accents
        if remove_accents:
            s = unicodedata.normalize("NFD", s)
            s = "".join(c for c in s if unicodedata.category(c) != "Mn")

        return s

    def transform(self, raw_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Transformer données iSaVigne vers schéma canonique.

        Args:
            raw_data: Données brutes des CSVs

        Returns:
            Dict avec tables canoniques
        """
        canonical = {}

        # 1. Transformer clients
        if "customers" in raw_data:
            canonical["CUSTOMERS"] = [
                self._transform_customer(c) for c in raw_data["customers"]
                if self._validate_customer(c)
            ]

        # 2. Transformer produits
        if "products" in raw_data:
            canonical["PRODUCT_CATALOG"] = [
                self._transform_product(p) for p in raw_data["products"]
                if self._validate_product(p)
            ]

        # 3. Transformer ventes
        if "sales_lines" in raw_data:
            canonical["SALES_LINES"] = [
                self._transform_sale_line(s) for s in raw_data["sales_lines"]
                if self._validate_sale_line(s)
            ]

        # 4. Transformer stock
        if "stock_levels" in raw_data:
            canonical["STOCK_LEVELS"] = [
                self._transform_stock(st) for st in raw_data["stock_levels"]
                if self._validate_stock(st)
            ]

        return canonical

    def _validate_customer(self, row: Dict) -> bool:
        """Valider qu'une ligne client a les champs obligatoires"""
        required = ["code_client", "email"]
        return all(row.get(f) for f in required)

    def _validate_product(self, row: Dict) -> bool:
        """Valider qu'une ligne produit a les champs obligatoires"""
        required = ["produit_key", "nom"]
        return all(row.get(f) for f in required)

    def _validate_sale_line(self, row: Dict) -> bool:
        """Valider qu'une ligne de vente a les champs obligatoires"""
        required = ["code_client", "produit_key", "date", "quantite"]
        return all(row.get(f) for f in required)

    def _validate_stock(self, row: Dict) -> bool:
        """Valider qu'une ligne de stock a les champs obligatoires"""
        required = ["produit_key", "entrepot", "quantite"]
        return all(row.get(f) for f in required)

    def _transform_customer(self, row: Dict) -> Customer:
        """Transformer ligne CSV client vers Customer canonique"""
        code_client = row.get("code_client", "")
        customer_key = f"isavigne-{code_client}"

        name_parts = row.get("nom", "").split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        return Customer(
            customer_key=customer_key,
            first_name=first_name,
            last_name=last_name,
            email=row.get("email", ""),
            phone=row.get("telephone"),
            mobile=row.get("mobile"),
            zip_code=row.get("code_postal"),
            city=row.get("ville"),
            country=row.get("pays", "France"),
        )

    def _transform_product(self, row: Dict) -> ProductCatalog:
        """Transformer ligne CSV produit vers ProductCatalog canonique"""
        product_key = row.get("produit_key", "")
        list_price = float(row.get("prix", 0) or 0)

        # Déterminer segment de prix
        if list_price < 15:
            price_segment = PriceSegment.ENTRY
        elif list_price < 30:
            price_segment = PriceSegment.STANDARD
        elif list_price < 75:
            price_segment = PriceSegment.PREMIUM
        else:
            price_segment = PriceSegment.LUXURY

        # Déterminer catégorie vin
        cat_raw = row.get("couleur", "").lower()
        if "rouge" in cat_raw:
            category = ProductCategory.ROUGE
        elif "blanc" in cat_raw:
            category = ProductCategory.BLANC
        elif "ros" in cat_raw:
            category = ProductCategory.ROSE
        elif "mousseux" in cat_raw or "champagne" in cat_raw:
            category = ProductCategory.MOUSSEUX
        else:
            category = ProductCategory.AUTRE

        # Parserraisins
        grape_varieties = []
        if cepage_raw := row.get("cepages"):
            grape_varieties = [g.strip() for g in cepage_raw.split(",")]

        return ProductCatalog(
            product_key=product_key,
            name=row.get("nom", ""),
            category=category,
            price_segment=price_segment,
            list_price_eur=list_price,
            cost_price_eur=float(row.get("cout", 0) or 0) or None,
            grape_varieties=grape_varieties,
            vintage=int(row.get("millesime", 0)) if row.get("millesime") else None,
            region=row.get("region"),
        )

    def _transform_sale_line(self, row: Dict) -> SalesLine:
        """Transformer ligne CSV vente vers SalesLine canonique"""
        customer_key = f"isavigne-{row.get('code_client', '')}"
        product_key = row.get("produit_key", "")

        # Parser date
        try:
            date_sale = pd.to_datetime(row.get("date", datetime.now()))
        except:
            date_sale = datetime.now()

        quantity = float(row.get("quantite", 0) or 0)
        price_unit = float(row.get("prix_unitaire", 0) or 0)

        return SalesLine(
            sale_line_key=f"isavigne-{row.get('num_ligne', '')}",
            customer_key=customer_key,
            product_key=product_key,
            date_sale=date_sale,
            quantity_units=quantity,
            quantity_bottles_75cl_eq=self._normalize_quantity(quantity, row.get("unite")),
            price_unit_eur=price_unit,
            price_total_eur=quantity * price_unit,
        )

    def _transform_stock(self, row: Dict) -> StockLevel:
        """Transformer ligne CSV stock vers StockLevel canonique"""
        product_key = row.get("produit_key", "")
        warehouse = row.get("entrepot", "Principal")

        return StockLevel(
            stock_key=f"isavigne-{product_key}-{warehouse}",
            product_key=product_key,
            warehouse=warehouse,
            quantity_units=float(row.get("quantite", 0) or 0),
            quantity_bottles_75cl_eq=self._normalize_quantity(
                float(row.get("quantite", 0) or 0),
                row.get("unite")
            ),
            last_count_date=datetime.now(),
        )

    def _normalize_quantity(
        self, quantity: float, unit: Optional[str] = None
    ) -> float:
        """
        Normaliser quantité vers équivalent 75cl.

        Par défaut suppose bouteilles 75cl.
        Si unit = "magnum" (150cl): multiplier par 2
        Si unit = "caisse" (12x75cl): multiplier par 12

        Args:
            quantity: Quantité
            unit: Unité (optionnel)

        Returns:
            Quantité en équivalent 75cl
        """
        if not unit or "75" in unit or "bouteille" in unit.lower():
            return quantity
        elif "150" in unit or "magnum" in unit.lower():
            return quantity * 2
        elif "caisse" in unit.lower() or "case" in unit.lower():
            return quantity * 12
        else:
            return quantity  # Default

    def load(self, canonical_data: Dict[str, List[Dict]], **kwargs) -> SyncResult:
        """
        Charger les données canoniques en base.

        Args:
            canonical_data: Données canoniques
            **kwargs: Params

        Returns:
            SyncResult
        """
        records_processed = {}

        # Pour maintenant, juste compter
        # En production: upsert en PostgreSQL
        for table_name, records in canonical_data.items():
            records_processed[table_name] = len(records)
            logger.info(f"Would load {len(records)} records into {table_name}")

        return SyncResult(
            success=True,
            connector_type=ConnectorType.ISAVIGNE,
            timestamp=datetime.now(),
            records_processed=records_processed,
        )


print("✓ iSaVigneConnector loaded")
