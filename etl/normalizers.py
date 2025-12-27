"""
Normalisation des données iSaVigne
Version: 1.0
Auteur: CRM Ruhlmann

Méthodes pour standardiser et nettoyer les données brutes.
"""

import re
import unicodedata
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# NORMALISATION DE CHAMPS
# ============================================================================

def normalize_client_code(code: str) -> str:
    """
    Normalise un code client:
    - Trim + uppercase
    - Pas d'espaces, pas d'accents
    """
    if not isinstance(code, str) or not code.strip():
        return None
    
    # Trim et uppercase
    code = code.strip().upper()
    
    # Supprimer accents
    code = remove_accents(code)
    
    # Supprimer espaces
    code = code.replace(" ", "")
    
    # Supprimer caractères spéciaux
    code = re.sub(r'[^A-Z0-9]', '', code)
    
    return code if code else None


def normalize_string(s: str, max_length: Optional[int] = None) -> str:
    """
    Normalise une chaîne:
    - Trim
    - Supprimer doubles espaces
    - Optionnel: limiter la longueur
    """
    if not isinstance(s, str) or not s.strip():
        return None
    
    s = s.strip()
    # Supprimer les doubles espaces
    s = re.sub(r'\s+', ' ', s)
    
    if max_length:
        s = s[:max_length]
    
    return s


def remove_accents(text: str) -> str:
    """
    Supprime les accents d'une chaîne.
    Ex: "Crémant" → "Cremant"
    """
    if not text:
        return text
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])


def normalize_produit_label(label: str) -> str:
    """
    Crée une Produit_Key stable à partir du label.
    Majuscules, pas d'accents, espace pour séparateurs.
    
    Ex: "Crémant d'Alsace Extra-Brut" → "CREMANT D ALSACE EXTRA BRUT"
    """
    if not label:
        return None
    
    # Uppercase
    label = label.upper()
    
    # Supprimer accents
    label = remove_accents(label)
    
    # Remplacer caractères spéciaux par espace
    label = re.sub(r"['-\./\\]+", " ", label)
    
    # Supprimer tout sauf alphanum et espace
    label = re.sub(r'[^A-Z0-9 ]', '', label)
    
    # Compresser les espaces multiples
    label = re.sub(r'\s+', ' ', label).strip()
    
    return label if label else None


def normalize_date(date_input: Any, format_input: Optional[str] = None) -> Optional[str]:
    """
    Convertit une date en format ISO (YYYY-MM-DD).
    Accepte: str (plusieurs formats), datetime, None
    """
    if date_input is None or (isinstance(date_input, str) and not date_input.strip()):
        return None
    
    # Si c'est déjà un datetime
    if isinstance(date_input, datetime):
        return date_input.strftime("%Y-%m-%d")
    
    # Si c'est une chaîne
    if isinstance(date_input, str):
        date_input = date_input.strip()
        
        # Essayer plusieurs formats
        formats = [
            "%Y-%m-%d",           # ISO (déjà bon)
            "%d/%m/%Y",           # Français
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",           # Suisse
            "%Y.%m.%d",
        ]
        
        if format_input:
            formats = [format_input] + formats
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_input, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        logger.warning(f"Impossible de parser la date: {date_input}")
        return None
    
    return None


def normalize_float(value: Any) -> Optional[float]:
    """
    Convertit une valeur en float.
    Gère: str avec virgule/point, nombres, None
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        value = value.strip()
        # Remplacer virgule par point
        value = value.replace(",", ".")
        # Supprimer espaces (format 1 234,56)
        value = value.replace(" ", "")
        
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Impossible de convertir en float: {value}")
            return None
    
    return None


def normalize_email(email: str) -> Optional[str]:
    """
    Valide et normalise une adresse email.
    """
    if not email or not isinstance(email, str):
        return None
    
    email = email.strip().lower()
    
    # Validation basique
    if re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return email
    
    logger.warning(f"Email invalide: {email}")
    return None


def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalise un numéro de téléphone.
    Supprime espaces, tirets, etc.
    """
    if not phone or not isinstance(phone, str):
        return None
    
    phone = phone.strip()
    # Supprimer espaces, tirets, points
    phone = re.sub(r'[\s\-\.]', '', phone)
    
    return phone if phone else None


# ============================================================================
# TABLES DE MAPPING
# ============================================================================

def get_product_key_mapping() -> Dict[str, str]:
    """
    Retourne la table de mapping Produit_Label → Produit_Key
    À maintenir manuellement ou charger d'une base.
    
    Exemple:
    {
        "CREMANT D ALSACE EXTRA BRUT": "CREMANT_D_ALSACE_EXTRA_BRUT",
        "GEWURZTRAMINER VENDANGES TARDIVES": "GEWURZ_VT",
    }
    """
    # TODO: charger d'une table DATABASE ou fichier CSV
    return {}


def get_article_unit_coefficient(article: str) -> float:
    """
    Retourne le coefficient de conversion article → unités (bouteilles).
    
    Ex: CARTON12 → 12 (12 bouteilles par carton)
    """
    # TODO: charger d'une table DATABASE ou fichier CSV
    mapping = {
        "CARTON6": 6,
        "CARTON12": 12,
        "MAGNUM": 1,
        "DEMI": 0.5,
    }
    return mapping.get(article, 1.0)


# ============================================================================
# CALCULS SECONDAIRES
# ============================================================================

def create_document_id(document_type: str, document_no: str, date: str = None) -> Optional[str]:
    """
    Crée une clé unique et stable pour identifier un document.
    
    Format: DOC_TYPE_NUMBER_DATE (si date dispo)
    Ex: "VENTE_001234" ou "VENTE_001234_2025-12-27"
    """
    if not document_type or not document_no:
        return None
    
    document_type = normalize_string(document_type).upper()[:3]  # Abréger
    document_no = str(document_no).strip()
    
    doc_id = f"{document_type}_{document_no}"
    
    if date:
        doc_id += f"_{date}"
    
    return doc_id


def calculate_qty_unit(qty_line: float, article: str) -> float:
    """
    Convertit Qty_Line en unités standard (bouteilles).
    
    Ex: qty_line=2, article=CARTON12 → 24 bouteilles
    """
    if not qty_line:
        return 0.0
    
    coef = get_article_unit_coefficient(article)
    return qty_line * coef


if __name__ == "__main__":
    # Tests
    print("Tests de normalisation:")
    print(f"Client code: {normalize_client_code('  CLIENT-001  ')}")
    print(f"Produit label: {normalize_produit_label('Crémant d\'Alsace')}")
    print(f"Date: {normalize_date('27/12/2025')}")
    print(f"Float: {normalize_float('1 234,56')}")
    print(f"Email: {normalize_email('john@example.com')}")
