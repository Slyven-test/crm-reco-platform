"""
================================================================================
  CONNECTORS ARCHITECTURE
================================================================================

Connecteurs interchangeables pour alimenter le schéma canonique.

Chaque connecteur remplit les mêmes 5 tables:
  - PRODUCT_CATALOG
  - CUSTOMERS
  - SALES_LINES
  - STOCK_LEVELS
  - CONTACT_HISTORY (optionnel)

Cela permet de fonctionner avec iSaVigne AUJOURD'HUI et Odoo DEMAIN
sans recoder la logique de recommandations.

Structure:
  connectors/
    ├── __init__.py (ce fichier)
    ├── base_connector.py (classe abstraite BaseConnector)\n    ├── canonical_schema.py (tables canoniques)\n    ├── odoo_connector.py (connecteur Odoo - API XML-RPC)\n    ├── isavigne_connector.py (connecteur iSaVigne - exports CSV)\n    └── connector_manager.py (orchestration)\n\n================================================================================\n\"\"\"\n\nfrom .base_connector import BaseConnector, ConnectorType, ConnectorStatus\nfrom .canonical_schema import (\n    CanonicalSchema,\n    ProductCatalog,\n    Customer,\n    SalesLine,\n    StockLevel,\n    ContactHistory,\n)\nfrom .odoo_connector import OdooConnector\nfrom .isavigne_connector import iSaVigneConnector\nfrom .connector_manager import ConnectorManager\n\n__all__ = [\n    \"BaseConnector\",\n    \"ConnectorType\",\n    \"ConnectorStatus\",\n    \"CanonicalSchema\",\n    \"ProductCatalog\",\n    \"Customer\",\n    \"SalesLine\",\n    \"StockLevel\",\n    \"ContactHistory\",\n    \"OdooConnector\",\n    \"iSaVigneConnector\",\n    \"ConnectorManager\",\n]\n\nprint(\"\"\"\n✅ Connecteurs Module Loaded\n\nAvailable connectors:\n  - OdooConnector (API XML-RPC)\n  - iSaVigneConnector (CSV exports)\n\nCanonical Schema:\n  - PRODUCT_CATALOG\n  - CUSTOMERS\n  - SALES_LINES\n  - STOCK_LEVELS\n  - CONTACT_HISTORY\n\"\"\")\n