"""
Connecteur Odoo

Intégration avec Odoo via XML-RPC API (officielle et supportée).
Pull incrémental avec cursor temporel sur write_date.

Configuration requise:
  - odoo_url: URL Odoo (https://...)
  - odoo_db: Base de données Odoo
  - odoo_user: Utilisateur technique
  - odoo_api_key: API Key (recommandé) ou mot de passe
  - odoo_company_id: (optionnel) ID société si multi-company
"""

import xmlrpc.client
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
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


class OdooConnector(BaseConnector):
    """
    Connecteur Odoo utilisant l'API XML-RPC.

    Méthodes:
    - test_connection(): Valide les credentials
    - extract(): Pull incrémental des données
    - transform(): Map vers schéma canonique
    - load(): Sauvegarde en base
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialiser le connecteur Odoo.

        Args:
            config: Dict avec odoo_url, odoo_db, odoo_user, odoo_api_key
        """
        super().__init__(ConnectorType.ODOO, config)
        self.validate_config()

        # Extraire et stocker les params
        self.url = config["odoo_url"]
        self.db = config["odoo_db"]
        self.user = config["odoo_user"]
        self.api_key = config["odoo_api_key"]
        self.company_id = config.get("odoo_company_id", None)

        # Clients XML-RPC
        self.common = None
        self.models = None
        self.uid = None

        logger.info(f"Odoo Connector configured for {self.url}")

    def get_required_config_keys(self) -> List[str]:
        """Clés requises"""
        return ["odoo_url", "odoo_db", "odoo_user", "odoo_api_key"]

    def test_connection(self) -> bool:
        """
        Tester la connexion Odoo.

        Returns:
            True si connexion OK

        Raises:
            ConnectionError si échec
        """
        try:
            logger.info(f"Testing Odoo connection to {self.url}")

            # Connexion au endpoint common
            self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")

            # Authentifier
            self.uid = self.common.authenticate(
                self.db, self.user, self.api_key, {}
            )

            if not self.uid:
                raise ConnectionError("Authentication failed: Invalid credentials")

            # Connexion au endpoint models
            self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

            # Tester lecture simple
            result = self.models.execute_kw(
                self.db, self.uid, self.api_key,
                "res.partner", "search", [[]],
                {"limit": 1}
            )

            logger.info("✓ Odoo connection successful")
            self.status = ConnectorStatus.HEALTHY
            return True

        except Exception as e:
            error_msg = f"Odoo connection failed: {str(e)}"
            logger.error(error_msg)
            self.last_error = error_msg
            self.status = ConnectorStatus.ERROR
            raise ConnectionError(error_msg)

    def extract(self, source: str = None, last_sync: Optional[datetime] = None, **kwargs) -> Dict[str, List[Dict]]:
        """
        Extraire les données d'Odoo avec incrémental.

        Args:
            source: Type spécifique à extraire ("customers", "products", etc)
                    Si None: extrait tout
            last_sync: Datetime pour pull incrémental (ne prendre que records modifiés après)
            **kwargs: Params additionnels (limit, offset, etc)

        Returns:
            Dict avec clés = modèles Odoo (res.partner, product.product, etc)
        """
        if not self.uid:
            self.test_connection()

        raw_data = {}

        # 1. Clients (res.partner)
        if not source or source == "customers":
            logger.info("Extracting Odoo customers")
            raw_data["customers"] = self._extract_customers(last_sync, **kwargs)

        # 2. Produits (product.product)
        if not source or source == "products":
            logger.info("Extracting Odoo products")
            raw_data["products"] = self._extract_products(last_sync, **kwargs)

        # 3. Lignes de vente (sale.order.line)
        if not source or source == "sales_lines":
            logger.info("Extracting Odoo sales lines")
            raw_data["sales_lines"] = self._extract_sales_lines(last_sync, **kwargs)

        # 4. Stock (stock.quant)
        if not source or source == "stock_levels":
            logger.info("Extracting Odoo stock levels")
            raw_data["stock_levels"] = self._extract_stock_levels(**kwargs)

        return raw_data

    def _extract_customers(self, last_sync: Optional[datetime] = None, **kwargs) -> List[Dict]:
        """Extraire clients res.partner"""
        domain = [["customer_rank", ">", 0]]  # Clients uniquement

        if last_sync:
            domain.append(["write_date", ">", last_sync.isoformat()])

        fields = [
            "id", "name", "email", "phone", "mobile",
            "zip", "city", "country_id",
            "write_date"
        ]

        limit = kwargs.get("limit", 5000)
        ids = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "res.partner", "search", [domain],
            {"limit": limit}
        )

        if not ids:
            logger.info("No customers to extract")
            return []

        records = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "res.partner", "read", [ids],
            {"fields": fields}
        )

        logger.info(f"Extracted {len(records)} customers")
        return records

    def _extract_products(self, last_sync: Optional[datetime] = None, **kwargs) -> List[Dict]:
        """Extraire produits product.product"""
        domain = [["sale_ok", "=", True]]  # Produits actifs en vente

        if last_sync:
            domain.append(["write_date", ">", last_sync.isoformat()])

        fields = [
            "id", "default_code", "name", "list_price", "standard_price",
            "categ_id", "type",
            "write_date"
        ]

        limit = kwargs.get("limit", 5000)
        ids = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "product.product", "search", [domain],
            {"limit": limit}
        )

        if not ids:
            logger.info("No products to extract")
            return []

        records = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "product.product", "read", [ids],
            {"fields": fields}
        )

        logger.info(f"Extracted {len(records)} products")
        return records

    def _extract_sales_lines(self, last_sync: Optional[datetime] = None, **kwargs) -> List[Dict]:
        """Extraire lignes de vente sale.order.line"""
        domain = []

        if last_sync:
            domain.append(["write_date", ">", last_sync.isoformat()])

        fields = [
            "id", "order_id", "product_id", "product_uom_qty",
            "price_unit", "price_subtotal", "price_total",
            "write_date"
        ]

        limit = kwargs.get("limit", 10000)
        ids = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "sale.order.line", "search", [domain],
            {"limit": limit}
        )

        if not ids:
            logger.info("No sales lines to extract")
            return []

        records = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "sale.order.line", "read", [ids],
            {"fields": fields}
        )

        logger.info(f"Extracted {len(records)} sales lines")
        return records

    def _extract_stock_levels(self, **kwargs) -> List[Dict]:
        """Extraire niveaux de stock stock.quant"""
        domain = [["quantity", ">", 0]]

        fields = [
            "id", "product_id", "location_id", "quantity",
            "reserved_quantity",
        ]

        limit = kwargs.get("limit", 5000)
        ids = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "stock.quant", "search", [domain],
            {"limit": limit}
        )

        if not ids:
            logger.info("No stock levels to extract")
            return []

        records = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "stock.quant", "read", [ids],
            {"fields": fields}
        )

        logger.info(f"Extracted {len(records)} stock records")
        return records

    def transform(self, raw_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Transformer données Odoo vers schéma canonique.

        Args:
            raw_data: Données brutes d'Odoo

        Returns:
            Dict avec clés = tables canoniques (CUSTOMERS, PRODUCTS, etc)
        """
        canonical = {}

        # 1. Transformer clients
        if "customers" in raw_data:
            canonical["CUSTOMERS"] = [
                self._transform_customer(c) for c in raw_data["customers"]
            ]

        # 2. Transformer produits
        if "products" in raw_data:
            canonical["PRODUCT_CATALOG"] = [
                self._transform_product(p) for p in raw_data["products"]
            ]

        # 3. Transformer lignes
        if "sales_lines" in raw_data:
            canonical["SALES_LINES"] = [
                self._transform_sale_line(s) for s in raw_data["sales_lines"]
            ]

        # 4. Transformer stock
        if "stock_levels" in raw_data:
            canonical["STOCK_LEVELS"] = [
                self._transform_stock(st) for st in raw_data["stock_levels"]
            ]

        return canonical

    def _transform_customer(self, odoo_partner: Dict) -> Customer:
        """Transformer res.partner vers Customer canonique"""
        customer_key = f"odoo-{odoo_partner['id']}"
        name_parts = odoo_partner["name"].split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        return Customer(
            customer_key=customer_key,
            first_name=first_name,
            last_name=last_name,
            email=odoo_partner.get("email", ""),
            phone=odoo_partner.get("phone"),
            mobile=odoo_partner.get("mobile"),
            zip_code=odoo_partner.get("zip"),
            city=odoo_partner.get("city"),
            country=odoo_partner.get("country_id", [""])[1] if odoo_partner.get("country_id") else None,
        )

    def _transform_product(self, odoo_product: Dict) -> ProductCatalog:
        """Transformer product.product vers ProductCatalog canonique"""
        # Normaliser product_key
        default_code = odoo_product.get("default_code", "")
        product_key = f"odoo-{odoo_product['id']}-{default_code}".upper().replace(" ", "-")

        # Déterminer le segment de prix
        list_price = odoo_product.get("list_price", 0)
        if list_price < 15:
            price_segment = PriceSegment.ENTRY
        elif list_price < 30:
            price_segment = PriceSegment.STANDARD
        elif list_price < 75:
            price_segment = PriceSegment.PREMIUM
        else:
            price_segment = PriceSegment.LUXURY

        return ProductCatalog(
            product_key=product_key,
            name=odoo_product["name"],
            category=ProductCategory.AUTRE,  # À affiner via custom fields Odoo
            price_segment=price_segment,
            list_price_eur=list_price,
            cost_price_eur=odoo_product.get("standard_price"),
        )

    def _transform_sale_line(self, odoo_line: Dict) -> SalesLine:
        """Transformer sale.order.line vers SalesLine canonique"""
        customer_key = f"odoo-{odoo_line.get('order_id', [0])[0]}"
        product_key = f"odoo-{odoo_line['product_id'][0]}"

        return SalesLine(
            sale_line_key=f"odoo-{odoo_line['id']}",
            customer_key=customer_key,
            product_key=product_key,
            date_sale=datetime.fromisoformat(odoo_line.get("write_date", datetime.now().isoformat())),
            quantity_units=odoo_line.get("product_uom_qty", 0),
            quantity_bottles_75cl_eq=odoo_line.get("product_uom_qty", 0),  # À normaliser
            price_unit_eur=odoo_line.get("price_unit", 0),
            price_total_eur=odoo_line.get("price_total", 0),
        )

    def _transform_stock(self, odoo_quant: Dict) -> StockLevel:
        """Transformer stock.quant vers StockLevel canonique"""
        product_key = f"odoo-{odoo_quant['product_id'][0]}"
        warehouse = odoo_quant.get("location_id", [""])[1] if odoo_quant.get("location_id") else "Unknown"

        return StockLevel(
            stock_key=f"odoo-{odoo_quant['id']}",
            product_key=product_key,
            warehouse=warehouse,
            quantity_units=odoo_quant.get("quantity", 0),
            quantity_bottles_75cl_eq=odoo_quant.get("quantity", 0),  # À normaliser
            last_count_date=datetime.now(),
            reserved_qty=odoo_quant.get("reserved_quantity", 0),
        )

    def load(self, canonical_data: Dict[str, List[Dict]], **kwargs) -> SyncResult:
        """
        Charger les données canoniques en base.

        Pour Odoo connector, on va stocker en tables SQL normalisées
        (pas directement modifier Odoo, qui est source de vérité).

        Args:
            canonical_data: Données canoniques
            **kwargs: Params

        Returns:
            SyncResult
        """
        records_processed = {}

        # Pour maintenant, juste compter les records
        # En production: upsert en PostgreSQL
        for table_name, records in canonical_data.items():
            records_processed[table_name] = len(records)
            logger.info(f"Would load {len(records)} records into {table_name}")

        return SyncResult(
            success=True,
            connector_type=ConnectorType.ODOO,
            timestamp=datetime.now(),
            records_processed=records_processed,
        )


print("✓ OdooConnector loaded")
