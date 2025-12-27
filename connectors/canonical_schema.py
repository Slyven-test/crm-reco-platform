"""
Schéma Canonique

Définit les 5 tables canoniques que TOUS les connecteurs doivent remplir.
Cela garantit que la logique de recommandations ne dépend pas d'une source en particulier.

Tables:
  1. PRODUCT_CATALOG - Produits et leurs attributs
  2. CUSTOMERS - Clients et données de contactabilité
  3. SALES_LINES - Lignes de ventes historiques
  4. STOCK_LEVELS - Niveaux de stock actuels
  5. CONTACT_HISTORY - (Optionnel) Historique des contacts marketing
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ProductCategory(Enum):
    """Catégories de produits vin"""
    ROUGE = "rouge"
    BLANC = "blanc"
    ROSE = "rosé"
    PETILLANT = "pétillant"
    MOUSSEUX = "mousseux"
    FORTIFIE = "fortifié"
    AUTRE = "autre"


class PriceSegment(Enum):
    """Segments de prix"""
    ENTRY = "entry"  # 0-15€
    STANDARD = "standard"  # 15-30€
    PREMIUM = "premium"  # 30-75€
    LUXURY = "luxury"  # 75€+


class CustomerSegment(Enum):
    """Segments clients"""
    VIP = "vip"
    STANDARD = "standard"
    AT_RISK = "at_risk"
    PROSPECT = "prospect"
    INACTIVE = "inactive"


class ContactChannel(Enum):
    """Canaux de contact"""
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"
    WEBSITE = "website"
    DIRECT = "direct"


@dataclass
class ProductCatalog:
    """
    Produit dans le schéma canonique.

    Attributs:
        product_key: Identifiant stable et unique du produit
                     (ex: "RIESLING-2020-75CL" normalisé)
        name: Nom du produit
        category: Catégorie vin (ROUGE, BLANC, etc)
        price_segment: Segment de prix (ENTRY, STANDARD, PREMIUM, LUXURY)
        list_price_eur: Prix de vente TTC en EUR
        cost_price_eur: Coût achat en EUR (optionnel)
        grape_varieties: Liste de cépages (ex: ["Riesling", "Gewürztraminer"])
        flavors: Profils aromatiques (ex: ["agrume", "floral", "sec"])
        vintage: Millésime si applicable
        region: Région viticole
        alcohol_percent: % d'alcool
        total_acidity: Acidité totale g/L
        residual_sugar: Sucre résiduel g/L
        body: Corpulence (light, medium, full)
        tannins: Niveau tannins (soft, medium, firm, bold)
        active: Si produit est actif/discontinued
        last_updated: Timestamp dernière modification
    """

    product_key: str
    name: str
    category: ProductCategory
    price_segment: PriceSegment
    list_price_eur: float
    cost_price_eur: Optional[float] = None
    grape_varieties: List[str] = field(default_factory=list)
    flavors: List[str] = field(default_factory=list)
    vintage: Optional[int] = None
    region: Optional[str] = None
    alcohol_percent: Optional[float] = None
    total_acidity: Optional[float] = None
    residual_sugar: Optional[float] = None
    body: Optional[str] = None
    tannins: Optional[str] = None
    active: bool = True
    last_updated: datetime = field(default_factory=datetime.now)

    def get_margin_percent(self) -> Optional[float]:
        """Calculer marge %"""
        if not self.cost_price_eur:
            return None
        return ((self.list_price_eur - self.cost_price_eur) / self.list_price_eur) * 100


@dataclass
class Customer:
    """
    Client dans le schéma canonique.

    Attributs:
        customer_key: Identifiant stable du client
                      (ex: "CLIENT-12345" ou "odoo-5678")
        first_name: Prénom
        last_name: Nom
        email: Email principal
        phone: Téléphone
        mobile: Mobile
        zip_code: Code postal
        city: Ville
        country: Pays
        segment: Segment client calculé (VIP, STANDARD, etc)
        email_opt_out: Si client a unsubscribé aux emails
        sms_opt_out: Si client a refusé SMS
        phone_opt_out: Si client a refusé appels
        last_purchase_date: Date du dernier achat
        first_purchase_date: Date du premier achat
        total_spent_eur: Montant total dépensé
        purchase_count: Nombre d'achats
        avg_order_value_eur: AOV
        preferred_category: Catégorie préférée (ROUGE, BLANC, etc)
        last_updated: Timestamp dernière modification
    """

    customer_key: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    mobile: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    segment: CustomerSegment = CustomerSegment.PROSPECT
    email_opt_out: bool = False
    sms_opt_out: bool = False
    phone_opt_out: bool = False
    last_purchase_date: Optional[datetime] = None
    first_purchase_date: Optional[datetime] = None
    total_spent_eur: float = 0.0
    purchase_count: int = 0
    avg_order_value_eur: float = 0.0
    preferred_category: Optional[ProductCategory] = None
    last_updated: datetime = field(default_factory=datetime.now)

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class SalesLine:
    """
    Ligne de vente historique (transaction).

    Attributs:
        sale_line_key: Identifiant unique de la ligne
        customer_key: Référence au client
        product_key: Référence au produit
        date_sale: Date de la vente
        quantity_units: Quantité en unités (bouteilles, caisses)
        quantity_bottles_75cl_eq: Quantité en équivalents 75cl normalisés
        price_unit_eur: Prix unitaire TTC
        price_total_eur: Montant ligne (qty * unit_price)
        cost_total_eur: Coût total (qty * cost_price)
        margin_percent: Marge %
        order_id: ID de la commande (si disponible)
        channel: Canal de vente (website, direct, distributor, etc)
        notes: Commentaires
    """

    sale_line_key: str
    customer_key: str
    product_key: str
    date_sale: datetime
    quantity_units: float
    quantity_bottles_75cl_eq: float
    price_unit_eur: float
    price_total_eur: float
    cost_total_eur: Optional[float] = None
    margin_percent: Optional[float] = None
    order_id: Optional[str] = None
    channel: str = "direct"
    notes: Optional[str] = None


@dataclass
class StockLevel:
    """
    Niveau de stock actuel.

    Attributs:
        stock_key: Identifiant unique
        product_key: Référence au produit
        warehouse: Nom de l'entrepôt/lieu
        quantity_units: Quantité en stock
        quantity_bottles_75cl_eq: En équivalents 75cl
        last_count_date: Date du dernier inventaire
        reserved_qty: Quantité réservée (commandes non livrées)
        available_qty: Quantité disponible pour vente
    """

    stock_key: str
    product_key: str
    warehouse: str
    quantity_units: float
    quantity_bottles_75cl_eq: float
    last_count_date: datetime
    reserved_qty: float = 0.0
    available_qty: Optional[float] = None

    def calculate_available(self) -> float:
        """Calculer qté disponible"""
        return self.quantity_units - self.reserved_qty


@dataclass
class ContactHistory:
    """
    Historique de contact marketing.

    Attributs:
        contact_key: Identifiant unique
        customer_key: Référence client
        date_contact: Date du contact
        channel: Canal (EMAIL, SMS, PHONE, WEBSITE)
        campaign: Campagne/scénario
        subject: Sujet (pour emails)
        status: Statut (sent, opened, clicked, bounced, replied, etc)
        product_key_suggested: Produit recommandé (si applicable)
        response: Si client a répondu (binary)
        response_details: Détails de la réponse
    """

    contact_key: str
    customer_key: str
    date_contact: datetime
    channel: ContactChannel
    campaign: str
    subject: Optional[str] = None
    status: str = "sent"
    product_key_suggested: Optional[str] = None
    response: bool = False
    response_details: Optional[str] = None


class CanonicalSchema:
    """
    Schéma canonique complet.
    Gestionnaire des 5 tables canoniques.
    """

    TABLES = {
        "PRODUCT_CATALOG": ProductCatalog,
        "CUSTOMERS": Customer,
        "SALES_LINES": SalesLine,
        "STOCK_LEVELS": StockLevel,
        "CONTACT_HISTORY": ContactHistory,
    }

    @classmethod
    def get_table_schema(cls, table_name: str) -> type:
        """Obtenir la classe dataclass pour une table"""
        if table_name not in cls.TABLES:
            raise ValueError(f"Unknown table: {table_name}")
        return cls.TABLES[table_name]

    @classmethod
    def list_tables(cls) -> List[str]:
        """Lister tous les noms de tables"""
        return list(cls.TABLES.keys())

    @classmethod
    def to_dict(cls, record: Any) -> Dict[str, Any]:
        """Convertir un record dataclass en dict"""
        from dataclasses import asdict
        return asdict(record)


print("✅ Canonical Schema loaded")
print(f"   Tables: {', '.join(CanonicalSchema.list_tables())}")
