"""
Routes pour Mapping & Normalisation

Gère l'interface de mapping entre champs source et schéma canonique.

Endpoints:
  - GET  /mapping                         # Liste mappings
  - GET  /mapping/new                     # Formulaire mapping
  - POST /mapping                         # Créer mapping
  - GET  /mapping/<name>                  # Détails mapping
  - PUT  /mapping/<name>                  # Mettre à jour mapping
  - POST /mapping/<name>/preview          # Preview normalisation
  - GET  /mapping/api/quality-report      # Rapport qualité
  - GET  /mapping/api/anomalies           # Détection anomalies
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
import json

connectors_bp = Blueprint('mapping', __name__, url_prefix='/mapping')

# ============================================================================
# DATA MODELS (Mock - sera remplacé par DB)
# ============================================================================

MAPPINGS_DB = {
    # Exemple structure:
    # 'isavigne_mapping': {
    #     'connector_name': 'isavigne_prod',
    #     'connector_type': 'isavigne',
    #     'created_at': '2025-12-27T16:00:00',
    #     'last_modified': '2025-12-27T16:00:00',
    #     'field_mappings': {
    #         'CUSTOMERS': {
    #             'source_fields': ['client_id', 'client_name', 'client_email', ...],
    #             'mappings': {
    #                 'customer_id': {'source_field': 'client_id', 'transform': None},
    #                 'customer_name': {'source_field': 'client_name', 'transform': 'trim'},
    #                 'email': {'source_field': 'client_email', 'transform': 'lowercase'},
    #                 ...
    #             },
    #             'unmapped': ['client_phone'],
    #             'quality_score': 0.95
    #         },
    #         'PRODUCTS': {...},
    #     },
    #     'quality_score': 0.92,
    #     'status': 'active'
    # }
}

QUALITY_RULES = {
    'CUSTOMERS': {
        'customer_id': {'required': True, 'type': 'string'},
        'customer_name': {'required': True, 'type': 'string'},
        'email': {'required': False, 'type': 'email', 'format': 'email'},
        'phone': {'required': False, 'type': 'string'},
        'address': {'required': False, 'type': 'string'},
        'country': {'required': False, 'type': 'string'},
        'created_at': {'required': False, 'type': 'datetime'},
    },
    'PRODUCTS': {
        'product_id': {'required': True, 'type': 'string'},
        'product_name': {'required': True, 'type': 'string'},
        'sku': {'required': False, 'type': 'string'},
        'price': {'required': True, 'type': 'float', 'min': 0},
        'category': {'required': False, 'type': 'string'},
        'description': {'required': False, 'type': 'string'},
    },
    'SALES_LINES': {
        'sale_id': {'required': True, 'type': 'string'},
        'customer_id': {'required': True, 'type': 'string'},
        'product_id': {'required': True, 'type': 'string'},
        'quantity': {'required': True, 'type': 'float', 'min': 0},
        'unit_price': {'required': True, 'type': 'float', 'min': 0},
        'total_amount': {'required': True, 'type': 'float', 'min': 0},
        'sale_date': {'required': True, 'type': 'datetime'},
    },
    'STOCK_LEVELS': {
        'product_id': {'required': True, 'type': 'string'},
        'warehouse_id': {'required': False, 'type': 'string'},
        'quantity_on_hand': {'required': True, 'type': 'float', 'min': 0},
        'last_updated': {'required': False, 'type': 'datetime'},
    },
    'PRODUCT_CATALOG': {
        'product_id': {'required': True, 'type': 'string'},
        'product_name': {'required': True, 'type': 'string'},
        'sku': {'required': False, 'type': 'string'},
        'price': {'required': True, 'type': 'float', 'min': 0},
    }
}

TRANSFORMS_AVAILABLE = {
    'trim': 'Supprimer espaces',
    'lowercase': 'Convertir minuscules',
    'uppercase': 'Convertir majuscules',
    'capitalize': 'Première lettre maj',
    'remove_special_chars': 'Supprimer caractères spéciaux',
    'parse_email': 'Valider email',
    'parse_date': 'Formater date',
    'parse_currency': 'Formater devise',
    'null_to_empty': 'NULL -> chaîne vide',
    'empty_to_zero': 'Vide -> 0',
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_quality_score(mapping_data):
    """Calcule score de qualité du mapping (0-100)"""
    total_fields = 0
    mapped_fields = 0
    required_missing = 0
    
    for table, rules in QUALITY_RULES.items():
        if table not in mapping_data['field_mappings']:
            continue
            
        table_mapping = mapping_data['field_mappings'][table]
        for field, rule in rules.items():
            total_fields += 1
            
            if field in table_mapping['mappings']:
                mapped_fields += 1
            elif rule.get('required'):
                required_missing += 1
    
    if total_fields == 0:
        return 0
    
    # Score = (mapped / total) * 0.6 + (1 - required_missing/total) * 0.4
    mapping_score = (mapped_fields / total_fields) * 60
    required_score = (1 - min(required_missing / total_fields, 1)) * 40
    
    return int(mapping_score + required_score)

def detect_anomalies(mapping_data, sample_records):
    """Détecte anomalies dans les données"""
    anomalies = []
    
    for table, records in sample_records.items():
        if table not in mapping_data['field_mappings']:
            continue
        
        table_mapping = mapping_data['field_mappings'][table]
        rules = QUALITY_RULES.get(table, {})
        
        for idx, record in enumerate(records[:100]):  # Sample 100 records
            for canonical_field, mapping_info in table_mapping['mappings'].items():
                source_field = mapping_info.get('source_field')
                rule = rules.get(canonical_field, {})
                
                if source_field not in record:
                    continue
                
                value = record[source_field]
                
                # Détecte NULL
                if value is None and rule.get('required'):
                    anomalies.append({
                        'table': table,
                        'row': idx,
                        'field': canonical_field,
                        'issue': 'Champ requis NULL',
                        'severity': 'critical'
                    })
                
                # Détecte type mismatch
                expected_type = rule.get('type')
                if expected_type == 'email' and '@' not in str(value or ''):
                    anomalies.append({
                        'table': table,
                        'row': idx,
                        'field': canonical_field,
                        'issue': 'Email invalide',
                        'severity': 'high'
                    })
                
                # Détecte valeurs vides
                if value == '' and rule.get('required'):
                    anomalies.append({
                        'table': table,
                        'row': idx,
                        'field': canonical_field,
                        'issue': 'Champ vide',
                        'severity': 'medium'
                    })
    
    return anomalies

# ============================================================================
# ROUTES - PAGE WEB
# ============================================================================

@connectors_bp.route('', methods=['GET'])
def list_mappings():
    """Liste tous les mappings"""
    mappings = MAPPINGS_DB
    
    mapping_list = [
        {
            'name': name,
            'connector_name': data.get('connector_name'),
            'connector_type': data.get('connector_type'),
            'created_at': data.get('created_at'),
            'last_modified': data.get('last_modified'),
            'quality_score': data.get('quality_score', 0),
            'status': data.get('status', 'active'),
            'field_count': sum(
                len(v.get('mappings', {})) 
                for v in data.get('field_mappings', {}).values()
            )
        }
        for name, data in mappings.items()
    ]
    
    stats = {
        'total_mappings': len(mapping_list),
        'avg_quality_score': int(sum(m['quality_score'] for m in mapping_list) / len(mapping_list)) if mapping_list else 0,
        'active_mappings': sum(1 for m in mapping_list if m['status'] == 'active'),
    }
    
    return render_template(
        'mapping/list.html',
        mappings=mapping_list,
        stats=stats
    )

@connectors_bp.route('/new', methods=['GET'])
def new_mapping():
    """Formulaire création mapping"""
    # Récupérer liste des connecteurs
    connectors = [
        {'name': 'isavigne_prod', 'type': 'isavigne'},
        {'name': 'odoo_prod', 'type': 'odoo'},
    ]
    
    canonical_tables = list(QUALITY_RULES.keys())
    
    return render_template(
        'mapping/register.html',
        connectors=connectors,
        canonical_tables=canonical_tables,
        transforms=TRANSFORMS_AVAILABLE
    )

@connectors_bp.route('', methods=['POST'])
def create_mapping():
    """Crée un nouveau mapping"""
    try:
        mapping_name = request.form.get('mapping_name')
        connector_name = request.form.get('connector_name')
        
        if not mapping_name or not connector_name:
            flash('Nom et connecteur requis', 'error')
            return redirect(url_for('mapping.new_mapping'))
        
        # Créer structure mapping
        mapping = {
            'connector_name': connector_name,
            'connector_type': 'isavigne',  # TODO: récupérer du connecteur
            'created_at': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'field_mappings': {},
            'status': 'draft'
        }
        
        # Ajouter au DB
        MAPPINGS_DB[mapping_name] = mapping
        
        flash(f'Mapping "{mapping_name}" créé avec succès', 'success')
        return redirect(url_for('mapping.view_mapping', name=mapping_name))
    
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('mapping.new_mapping'))

@connectors_bp.route('/<name>', methods=['GET'])
def view_mapping(name):
    """Affiche détails d'un mapping"""
    if name not in MAPPINGS_DB:
        flash(f'Mapping "{name}" non trouvé', 'error')
        return redirect(url_for('mapping.list_mappings'))
    
    mapping = MAPPINGS_DB[name]
    
    # Préparer données pour affichage
    field_mappings_display = []
    for table, table_mapping in mapping.get('field_mappings', {}).items():
        rules = QUALITY_RULES.get(table, {})
        
        for canonical_field, mapping_info in table_mapping.get('mappings', {}).items():
            rule = rules.get(canonical_field, {})
            field_mappings_display.append({
                'table': table,
                'canonical_field': canonical_field,
                'source_field': mapping_info.get('source_field'),
                'transform': mapping_info.get('transform'),
                'required': rule.get('required', False),
                'type': rule.get('type'),
            })
    
    unmapped_fields = []
    for table, table_mapping in mapping.get('field_mappings', {}).items():
        for field in table_mapping.get('unmapped', []):
            unmapped_fields.append({
                'table': table,
                'field': field
            })
    
    return render_template(
        'mapping/detail.html',
        mapping_name=name,
        mapping=mapping,
        field_mappings=field_mappings_display,
        unmapped_fields=unmapped_fields,
        transforms=TRANSFORMS_AVAILABLE,
        quality_rules=QUALITY_RULES,
        canonical_tables=list(QUALITY_RULES.keys())
    )

@connectors_bp.route('/<name>', methods=['PUT'])
def update_mapping(name):
    """Met à jour un mapping"""
    if name not in MAPPINGS_DB:
        return jsonify({'success': False, 'message': 'Mapping not found'}), 404
    
    try:
        data = request.get_json()
        mapping = MAPPINGS_DB[name]
        
        # Mettre à jour field_mappings
        if 'field_mappings' in data:
            mapping['field_mappings'] = data['field_mappings']
        
        # Recalculer quality score
        mapping['quality_score'] = calculate_quality_score(mapping)
        mapping['last_modified'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'quality_score': mapping['quality_score'],
            'message': 'Mapping mis à jour'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

# ============================================================================
# ROUTES - API JSON
# ============================================================================

@connectors_bp.route('/<name>/preview', methods=['POST'])
def preview_mapping(name):
    """Preview de normalisation sur données sample"""
    if name not in MAPPINGS_DB:
        return jsonify({'success': False, 'message': 'Mapping not found'}), 404
    
    try:
        mapping = MAPPINGS_DB[name]
        sample_data = request.get_json().get('sample_data', {})
        
        # Normaliser données selon mapping
        normalized = {}
        for table, records in sample_data.items():
            if table not in mapping['field_mappings']:
                continue
            
            table_mapping = mapping['field_mappings'][table]
            normalized[table] = []
            
            for record in records:
                normalized_record = {}
                for canonical_field, mapping_info in table_mapping['mappings'].items():
                    source_field = mapping_info.get('source_field')
                    transform = mapping_info.get('transform')
                    
                    if source_field in record:
                        value = record[source_field]
                        # Appliquer transform (placeholder)
                        normalized_record[canonical_field] = value
                
                normalized[table].append(normalized_record)
        
        # Détecter anomalies
        anomalies = detect_anomalies(mapping, sample_data)
        
        return jsonify({
            'success': True,
            'normalized_sample': normalized,
            'anomalies': anomalies,
            'anomalies_count': len(anomalies),
            'critical_count': sum(1 for a in anomalies if a['severity'] == 'critical'),
            'high_count': sum(1 for a in anomalies if a['severity'] == 'high'),
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@connectors_bp.route('/api/quality-report', methods=['GET'])
def quality_report():
    """Rapport de qualité pour tous les mappings"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'mappings': []
    }
    
    for name, mapping in MAPPINGS_DB.items():
        quality_score = calculate_quality_score(mapping)
        
        field_stats = {}
        for table, table_mapping in mapping.get('field_mappings', {}).items():
            rules = QUALITY_RULES.get(table, {})
            total = len(rules)
            mapped = len(table_mapping.get('mappings', {}))
            unmapped = len(table_mapping.get('unmapped', []))
            required_missing = sum(
                1 for f, r in rules.items() 
                if r.get('required') and f not in table_mapping.get('mappings', {})
            )
            
            field_stats[table] = {
                'total_fields': total,
                'mapped': mapped,
                'unmapped': unmapped,
                'required_missing': required_missing,
                'coverage': int((mapped / total * 100)) if total > 0 else 0,
            }
        
        report['mappings'].append({
            'name': name,
            'connector': mapping.get('connector_name'),
            'quality_score': quality_score,
            'field_stats': field_stats,
            'status': mapping.get('status'),
        })
    
    return jsonify(report)

@connectors_bp.route('/api/anomalies', methods=['GET'])
def anomalies():
    """Détecte anomalies dans tous les mappings"""
    mapping_name = request.args.get('mapping')
    severity = request.args.get('severity')  # critical, high, medium
    table_filter = request.args.get('table')
    
    anomalies_list = []
    
    # Pour démo, retourner anomalies mock
    # En prod: parcourir DB réelle avec sample records
    mock_anomalies = [
        {
            'mapping': 'isavigne_mapping',
            'table': 'CUSTOMERS',
            'row': 5,
            'field': 'email',
            'issue': 'Email invalide: not-an-email',
            'severity': 'high',
            'value': 'not-an-email'
        },
        {
            'mapping': 'isavigne_mapping',
            'table': 'SALES_LINES',
            'row': 12,
            'field': 'customer_id',
            'issue': 'Champ requis NULL',
            'severity': 'critical',
            'value': None
        },
        {
            'mapping': 'odoo_mapping',
            'table': 'PRODUCTS',
            'row': 8,
            'field': 'price',
            'issue': 'Prix négatif: -5.99',
            'severity': 'critical',
            'value': '-5.99'
        },
    ]
    
    for anom in mock_anomalies:
        if mapping_name and anom['mapping'] != mapping_name:
            continue
        if severity and anom['severity'] != severity:
            continue
        if table_filter and anom['table'] != table_filter:
            continue
        anomalies_list.append(anom)
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'total': len(anomalies_list),
        'critical': sum(1 for a in anomalies_list if a['severity'] == 'critical'),
        'high': sum(1 for a in anomalies_list if a['severity'] == 'high'),
        'medium': sum(1 for a in anomalies_list if a['severity'] == 'medium'),
        'anomalies': anomalies_list,
    })

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@connectors_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@connectors_bp.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500
