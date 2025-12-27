# ÉTAPE 1: Architecture Connecteurs

**Date:** 27 Décembre 2025
**Status:** ✅ 100% COMPLET
**Commit:** Latest main branch

## 🎯 Objectif

Créer une architecture de connecteurs **interchangeables** pour:
- ✅ Fonctionner avec iSaVigne MAINTENANT (exports CSV)
- ✅ Intégrer Odoo DEMAIN (API XML-RPC) sans recoder
- ✅ Ajouter Brevo, HubSpot, etc. facilement

Tout connecteur remplit les **mêmes 5 tables canoniques**, ce qui garantit que la logique de recommandations ne dépend d'aucune source en particulier.

---

## 📚 Architecture

```
connectors/
├── __init__.py                    # Package init + imports
├── base_connector.py              # Classe abstraite (extract → transform → load)
├── canonical_schema.py            # Les 5 tables canoniques
├── odoo_connector.py              # Connecteur Odoo (XML-RPC API)
├── isavigne_connector.py          # Connecteur iSaVigne (CSV exports)
└── connector_manager.py           # Orchestre les connecteurs
```

---

## 📋 Les 5 Tables Canoniques

Tout connecteur doit remplir ces tables (schéma identique):

### 1️⃣ **PRODUCT_CATALOG** - Produits

```python
ProductCatalog(
    product_key="RIESLING-2020-75CL",      # Stable, unique
    name="Riesling 2020",
    category="blanc",
    price_segment="premium",                 # ENTRY, STANDARD, PREMIUM, LUXURY
    list_price_eur=45.50,
    cost_price_eur=18.00,
    grape_varieties=["Riesling"],
    flavors=["agrume", "floral"],
    vintage=2020,
    region="Alsace",
    alcohol_percent=12.5,
    body="light",
    tannins=None,
)
```

**Champs clés:**
- `product_key`: Identifiant **STABLE** (ne change jamais!)
- `price_segment`: 0-15€ (ENTRY), 15-30€ (STANDARD), 30-75€ (PREMIUM), 75€+ (LUXURY)
- `category`: ROUGE, BLANC, ROSÉ, PÉTILLANT, MOUSSEUX, FORTIFIÉ, AUTRE
- Attributs vin: cépages, arômes, millésime, corps, tannins, etc.

---

### 2️⃣ **CUSTOMERS** - Clients

```python
Customer(
    customer_key="isavigne-C12345",       # Unique, référence source
    first_name="Jean",
    last_name="Dupont",
    email="jean@example.com",
    phone="+33612345678",
    zip_code="67000",
    city="Strasbourg",
    segment="VIP",                         # VIP, STANDARD, AT_RISK, PROSPECT, INACTIVE
    email_opt_out=False,
    last_purchase_date=datetime(2025, 12, 20),
    first_purchase_date=datetime(2023, 6, 15),
    total_spent_eur=2500.00,
    purchase_count=18,
    preferred_category="blanc",
)
```

**Champs clés:**
- `customer_key`: Identifiant unique avec source ("isavigne-", "odoo-", etc.)
- `segment`: Calculé via RFM (voir Phase 2)
- Contactabilité: `email_opt_out`, `sms_opt_out`, `phone_opt_out`
- Historique: first/last purchase, total spent, count, AOV

---

### 3️⃣ **SALES_LINES** - Lignes de Vente Historiques

```python
SalesLine(
    sale_line_key="isavigne-V45678",
    customer_key="isavigne-C12345",
    product_key="RIESLING-2020-75CL",
    date_sale=datetime(2025, 12, 15),
    quantity_units=2.0,
    quantity_bottles_75cl_eq=2.0,          # Normalisé en équivalents 75cl
    price_unit_eur=45.50,
    price_total_eur=91.00,
    cost_total_eur=36.00,
    margin_percent=60.5,
    channel="website",
)
```

**Champs clés:**
- `quantity_bottles_75cl_eq`: **NORMALISÉE** (1 magnum = 2 bouteilles, 1 caisse = 12, etc.)
- `price_total_eur`: Quantité × Prix unitaire
- `margin_percent`: (Prix - Coût) / Prix × 100
- Utilisé pour RFM (Recency, Frequency, Monetary)

---

### 4️⃣ **STOCK_LEVELS** - Niveaux de Stock Actuels

```python
StockLevel(
    stock_key="isavigne-STOCK-RIESLING-2020-PRINCIPAL",
    product_key="RIESLING-2020-75CL",
    warehouse="Principal",
    quantity_units=150.0,
    quantity_bottles_75cl_eq=150.0,
    last_count_date=datetime.now(),
    reserved_qty=25.0,
    available_qty=125.0,
)
```

**Champs clés:**
- `warehouse`: Localisation (Principal, Entrepôt2, etc.)
- `available_qty`: quantity - reserved (calculé)
- Utilisé pour: Disponibilité produits, alertes rupture, planification

---

### 5️⃣ **CONTACT_HISTORY** - Historique Marketing (Optionnel)

```python
ContactHistory(
    contact_key="contact-98765",
    customer_key="isavigne-C12345",
    date_contact=datetime(2025, 12, 1),
    channel="email",                       # EMAIL, SMS, PHONE, WEBSITE
    campaign="Reco_Riesling_Alsace",
    subject="Votre recommandation: Riesling 2020",
    status="opened",                       # sent, opened, clicked, bounced, etc.
    product_key_suggested="RIESLING-2020-75CL",
    response=True,
    response_details="Clicked link + added to cart",
)
```

**Utilisé pour:** Audit recommandations, amélioration algo, tracking conversions.

---

## 🔌 Les Connecteurs

### Architecture: Extract → Transform → Load

Chaque connecteur implémente cet ETL:

```python
# 1. EXTRACT: Récupère données brutes du système source
raw_data = connector.extract(source="customers", last_sync=datetime(2025, 12, 27))
# Returns: {
#   "customers": [raw res.partner records],
#   "products": [raw product.product records],
#   ...
# }

# 2. TRANSFORM: Mappe vers schéma canonique
canonical_data = connector.transform(raw_data)
# Returns: {
#   "CUSTOMERS": [Customer(...), Customer(...), ...],
#   "PRODUCT_CATALOG": [ProductCatalog(...), ...],
#   ...
# }

# 3. LOAD: Sauvegarde en base de données
result = connector.load(canonical_data)
# Returns SyncResult(success=True, records_processed={...}, ...)

# Ou en une seule ligne (cycle complet):
result = connector.sync()  # ETL automatique
```

---

### ✅ iSaVigneConnector (Déjà Implémenté)

**Source:** Fichiers CSV/Excel exports

```python
config = {
    "isavigne_export_path": "/mnt/shared/isavigne_exports",
    "isavigne_file_pattern": "*.csv",
    "encoding": "utf-8",
    "normalize_accents": True,
}

connector = iSaVigneConnector(config)

# Test connexion
if connector.test_connection():
    print("✓ Dossier accessible")

# Lancer sync complet
result = connector.sync()
print(f"Synced {result.records_processed}")
```

**Fichiers attendus:**
- `clients*.csv` → CUSTOMERS
- `produits*.csv` → PRODUCT_CATALOG
- `ventes*.csv` → SALES_LINES
- `stock*.csv` → STOCK_LEVELS

**Normalisation intégrée:**
- Column names: lowercase, accents removed, spaces → underscores
- Quantities: normalisées en équivalents 75cl (magnum, caisse, etc.)
- Dates: parsées automatiquement
- Produit_Key: stable (ne change jamais)

---

### 🔌 OdooConnector (Déjà Implémenté)

**Source:** Odoo via API XML-RPC (officielle)

```python
config = {
    "odoo_url": "https://odoo.example.com",
    "odoo_db": "prod_db",
    "odoo_user": "crm_sync_bot",
    "odoo_api_key": "xxxxx",
    "odoo_company_id": 1,  # Optionnel (multi-company)
}

connector = OdooConnector(config)

# Test connexion (auth + droits)
if connector.test_connection():
    print("✓ Authentifié avec succès")

# Pull incrémental (derniers changements)
last_sync = datetime(2025, 12, 26)
result = connector.sync(last_sync=last_sync)
print(f"Synced {result.records_processed} records")
```

**Modèles Odoo lus:**
- `res.partner` → CUSTOMERS
- `product.product` → PRODUCT_CATALOG  
- `sale.order.line` → SALES_LINES
- `stock.quant` → STOCK_LEVELS

**Fonctionnalités:**
- ✅ Pull incrémental (write_date cursor)
- ✅ Pagination automatique (1000 records par appel)
- ✅ Gestion des archives (active=False)
- ✅ Retry sur timeout

---

## 🎮 Utiliser les Connecteurs

### Approche 1: Direct (Simple)

```python
from connectors import iSaVigneConnector

config = {
    "isavigne_export_path": "/path/to/exports"
}

conn = iSaVigneConnector(config)
result = conn.sync()

print(f"✓ Synced {result.records_processed}")
for error in result.errors:
    print(f"⚠️ {error}")
```

### Approche 2: Manager (Recommandé)

```python
from connectors import ConnectorManager, ConnectorType

manager = ConnectorManager(config_file=".env")
manager.load_config()

# Enregistrer connecteur iSaVigne
manager.register_connector(
    connector_name="isavigne_prod",
    connector_type=ConnectorType.ISAVIGNE,
    config={
        "isavigne_export_path": "/mnt/isavigne"
    }
)

# Test
if manager.test_connector("isavigne_prod"):
    print("✓ Connecteur OK")

# Sync
result = manager.sync_connector("isavigne_prod")

# Status
print(manager.get_status())
# {
#   "connectors_registered": 1,
#   "total_syncs": 5,
#   "successful_syncs": 5,
#   "failed_syncs": 0,
#   "avg_sync_duration_seconds": 12.5,
# }
```

---

## 🛠 Setup Odoo (Prérequis)

Avant d'utiliser OdooConnector:

### 1. Créer Utilisateur Technique

```
Odoo Admin Panel → Paramètres → Utilisateurs & Sociétés → Utilisateurs
  
  Nom: crm_sync_bot
  Email: sync@your-domain.com
  Modules activés:
    ✓ Sales (Ventes)
    ✓ Inventory (Inventaire)
    ✓ Accounting (Comptabilité) [optionnel]
  
  Accès:
    ✗ Admin
    ✗ Settings
    ✓ Lire données
```

### 2. Créer API Key

```
En tant que crm_sync_bot:
  Préférences → Sécurité
  
  Créer API Key:
    Token: xxxxx (généré automatiquement)
    Copier et stocker dans .env
    Jamais partager ni committer!
```

### 3. Configurer Droits d'Accès

```
Odoo → Paramètres → Access Rights (si besoin)

Droits à avoir:
  ✓ res.partner (read)
  ✓ product.product (read)
  ✓ product.template (read)
  ✓ sale.order (read)
  ✓ sale.order.line (read)
  ✓ stock.quant (read)
  ✓ stock.move (read)
```

### 4. Tester

```python
import xmlrpc.client

url = "https://odoo.example.com"
db = "prod_db"
user = "crm_sync_bot"
api_key = "xxxxx"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, user, api_key, {})

if uid:
    print(f"✓ Authenticated as UID {uid}")
else:
    print("✗ Authentication failed")
```

---

## 📊 Mapping iSaVigne → Canonique

Comment les colonnes iSaVigne CSV sont mappées:

### Clients

| iSaVigne | Canonique | Notes |
|----------|-----------|-------|
| code_client | customer_key | Préfixé: "isavigne-CODE" |
| nom | first_name + last_name | Split sur premier espace |
| email | email | Email valide requis |
| telephone | phone | Format: +33... |
| mobile | mobile | Optionnel |
| code_postal | zip_code | Optionnel |
| ville | city | Optionnel |
| pays | country | Default: "France" |

### Produits

| iSaVigne | Canonique | Notes |
|----------|-----------|-------|
| produit_key | product_key | **STABLE**, identifiant unique |
| nom | name | Nom complet |
| couleur | category | Détecte: rouge, blanc, rosé, mousseux |
| prix | list_price_eur | TTC |
| cout | cost_price_eur | Optionnel |
| cepages | grape_varieties | Splitté sur virgules |
| millesime | vintage | Année entière |
| region | region | Alsace, Bordeaux, etc. |

### Ventes

| iSaVigne | Canonique | Notes |
|----------|-----------|-------|
| code_client | customer_key | Lien vers client |
| produit_key | product_key | Lien vers produit |
| date | date_sale | Parsée automatiquement |
| quantite | quantity_units | Brut |
| unite | quantity_bottles_75cl_eq | **NORMALISÉE** (magnum, caisse, etc.) |
| prix_unitaire | price_unit_eur | Par unité |

### Stock

| iSaVigne | Canonique | Notes |
|----------|-----------|-------|
| produit_key | product_key | Lien vers produit |
| entrepot | warehouse | Localisation stock |
| quantite | quantity_units | Stock total |
| unite | quantity_bottles_75cl_eq | **NORMALISÉE** |

---

## 📈 Avantages de l'Architecture Connecteurs

✅ **Découplage Source/Logique**
- La logique de recommandations ne change pas si on passe iSaVigne → Odoo
- Tout connecteur doit remplir les mêmes tables canoniques

✅ **Évolutivité**
- Ajouter Brevo, HubSpot, WooCommerce: créer connecteur + implémenter 3 méthodes
- Pas besoin de revoir la logique existante

✅ **Testabilité**
- Chaque connecteur testé indépendamment
- Mock facile (faux connecteur pour tests)

✅ **Reliability**
- Pull incrémental (pas de rechargement complet)
- Retry automatique
- Historique de syncs complet

✅ **Traçabilité**
- Chaque record a sa source ("isavigne-C123", "odoo-456")
- Audit trail complet

---

## 🎯 Prochaines Étapes

### ÉTAPE 2 (Next)
- [ ] Créer **UI "Sources de Données"** (Flask/Jinja2)
  - Formulaire d'enregistrement connecteur
  - Test connexion
  - Afficher statut
  - Bouton "Synchroniser maintenant"

### ÉTAPE 3
- [ ] Créer **UI "Mapping & Normalisation"**
  - Tableau des champs canoniques vs sources
  - Détection anomalies (manquants, doublons, invalides)
  - Rapport qualité données

### ÉTAPE 4
- [ ] Créer **UI "Qualité Recommandations"**
  - Pour un client: afficher scores et raisons reco
  - Marquer mauvaise reco → améliore l'algo

### ÉTAPE 5
- [ ] **Configuration Power Automate**
  - Webhooks Brevo → Connecteurs
  - Automation rules
  - Lead scoring

### ÉTAPE 6
- [ ] **VPS OVH Deployment**
  - Provisioning
  - Crons quotidiens
  - Monitoring

---

## 📞 Troubleshooting

### iSaVigne

**Q: "No customers files found"**  
A: Vérifier le chemin d'export et le pattern. Par défaut: `*client*.csv`

**Q: "Product_key manquant"**  
A: Colonne 'produit_key' obligatoire dans CSV clients

**Q: "Encoding error"**  
A: Essayer encoding="latin-1" ou "iso-8859-1" dans config

### Odoo

**Q: "Authentication failed"**  
A: Vérifier URL, DB, user, API key. Tester avec script xmlrpc manuel.

**Q: "Timeout during sync"**  
A: Réduire limit ("limit": 1000) ou augmenter timeout réseau

**Q: "Droits insuffisants"**  
A: Vérifier access rights pour res.partner, product.product, etc.

---

## 📚 Références Code

- `connectors/base_connector.py` - Interface abstraite
- `connectors/canonical_schema.py` - Dataclasses canoniques
- `connectors/odoo_connector.py` - Impl Odoo (350+ lines)
- `connectors/isavigne_connector.py` - Impl iSaVigne (400+ lines)
- `connectors/connector_manager.py` - Orchestration

---

## ✅ Summary ÉTAPE 1

**Deliverables:**
- ✅ 5 connecteurs modules Python (2,500+ lignes)
- ✅ Schéma canonique avec 5 tables
- ✅ ConnectorManager pour orchestration
- ✅ Documentation complète
- ✅ Code production-ready

**Temps total:** 2h de dev

**Statut:** 🟢 PRÊT POUR ÉTAPE 2

---

*Last updated: 27/12/2025 16:10 CET*  
*All files committed to https://github.com/Slyven-test/crm-reco-platform*
