"""
Routes pour Qualité des Recommandations

Gère l'interface d'audit et de feedback des recommandations générées.

Endpoints:
  - GET  /recommendations                      # Liste recommandations
  - GET  /recommendations/<id>                 # Détail recommandation
  - POST /recommendations/<id>/feedback        # Soumettre feedback
  - GET  /recommendations/api/quality-metrics  # Métriques qualité
  - GET  /recommendations/api/audit            # Audit complet
  - POST /recommendations/<id>/regenerate      # Régénérer recommandation
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
import json

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/recommendations')

# ============================================================================
# DATA MODELS (Mock - sera remplacé par DB)
# ============================================================================

RECOMMENDATIONS_DB = {
    # Structure:
    # 'reco_id': {
    #     'customer_id': 'C001',
    #     'customer_name': 'John Doe',
    #     'products_recommended': [
    #         {'product_id': 'P123', 'product_name': 'Riesling Grand Cru 2020', 'score': 0.92},
    #         ...
    #     ],
    #     'reasoning': 'Based on purchase history...',
    #     'algorithm': 'collaborative_filtering',
    #     'confidence_score': 0.89,
    #     'generated_at': '2025-12-27T16:00:00',
    #     'status': 'pending_review',  # pending_review, approved, rejected
    #     'feedback': None,
    #     'feedback_by': None,
    #     'feedback_at': None,
    # }
}

# Mock recommendations
RECOMMENDATIONS_DB = {
    'R001': {
        'customer_id': 'C001',
        'customer_name': 'Jean Dupont',
        'customer_email': 'jean.dupont@example.com',
        'products_recommended': [
            {'product_id': 'P123', 'product_name': 'Riesling Grand Cru 2020', 'score': 0.92, 'price': 45.00},
            {'product_id': 'P456', 'product_name': 'Gewurztraminer VT 2019', 'score': 0.87, 'price': 38.00},
            {'product_id': 'P789', 'product_name': 'Pinot Noir Réserve 2018', 'score': 0.81, 'price': 52.00},
        ],
        'reasoning': 'Basé sur historique d\'achats récent: préférence pour vins blancs alsaciens haut de gamme. Similarité avec clients segment "Amateurs Grand Cru".',
        'algorithm': 'collaborative_filtering',
        'confidence_score': 0.89,
        'data_quality_score': 0.95,
        'generated_at': '2025-12-27T15:30:00',
        'status': 'pending_review',
        'feedback': None,
        'feedback_by': None,
        'feedback_at': None,
    },
    'R002': {
        'customer_id': 'C002',
        'customer_name': 'Marie Martin',
        'customer_email': 'marie.martin@example.com',
        'products_recommended': [
            {'product_id': 'P234', 'product_name': 'Crémant d\'Alsace Brut', 'score': 0.88, 'price': 18.00},
            {'product_id': 'P567', 'product_name': 'Sylvaner Bio 2021', 'score': 0.79, 'price': 12.00},
        ],
        'reasoning': 'Nouveau client. Recommandations basées sur: profil démographique, localisation géographique, tendance vins bio.',
        'algorithm': 'content_based',
        'confidence_score': 0.72,
        'data_quality_score': 0.88,
        'generated_at': '2025-12-27T14:15:00',
        'status': 'approved',
        'feedback': {'rating': 5, 'comment': 'Excellentes recommandations, client très satisfait!'},
        'feedback_by': 'user@example.com',
        'feedback_at': '2025-12-27T15:00:00',
    },
    'R003': {
        'customer_id': 'C003',
        'customer_name': 'Pierre Schmitt',
        'customer_email': 'pierre.schmitt@example.com',
        'products_recommended': [
            {'product_id': 'P890', 'product_name': 'Muscat Sec 2022', 'score': 0.65, 'price': 15.00},
        ],
        'reasoning': 'Données insuffisantes. Recommandation générique basée sur produits populaires.',
        'algorithm': 'popularity_based',
        'confidence_score': 0.58,
        'data_quality_score': 0.45,
        'generated_at': '2025-12-27T13:00:00',
        'status': 'rejected',
        'feedback': {'rating': 2, 'comment': 'Recommandation non pertinente, client pas intéressé.'},
        'feedback_by': 'user@example.com',
        'feedback_at': '2025-12-27T14:30:00',
    },
}

ALGORITHMS_INFO = {
    'collaborative_filtering': {
        'name': 'Collaborative Filtering',
        'description': 'Basé sur comportements clients similaires',
        'min_data_required': 'High',
        'typical_accuracy': 0.85,
    },
    'content_based': {
        'name': 'Content-Based',
        'description': 'Basé sur caractéristiques produits',
        'min_data_required': 'Medium',
        'typical_accuracy': 0.78,
    },
    'popularity_based': {
        'name': 'Popularity-Based',
        'description': 'Basé sur produits populaires',
        'min_data_required': 'Low',
        'typical_accuracy': 0.62,
    },
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_quality_metrics():
    """Calcule métriques de qualité globales"""
    total = len(RECOMMENDATIONS_DB)
    if total == 0:
        return {
            'total_recommendations': 0,
            'avg_confidence': 0,
            'avg_data_quality': 0,
            'approval_rate': 0,
            'rejection_rate': 0,
            'pending_rate': 0,
        }
    
    approved = sum(1 for r in RECOMMENDATIONS_DB.values() if r['status'] == 'approved')
    rejected = sum(1 for r in RECOMMENDATIONS_DB.values() if r['status'] == 'rejected')
    pending = sum(1 for r in RECOMMENDATIONS_DB.values() if r['status'] == 'pending_review')
    
    avg_confidence = sum(r['confidence_score'] for r in RECOMMENDATIONS_DB.values()) / total
    avg_data_quality = sum(r['data_quality_score'] for r in RECOMMENDATIONS_DB.values()) / total
    
    return {
        'total_recommendations': total,
        'avg_confidence': round(avg_confidence * 100),
        'avg_data_quality': round(avg_data_quality * 100),
        'approval_rate': round((approved / total) * 100) if total > 0 else 0,
        'rejection_rate': round((rejected / total) * 100) if total > 0 else 0,
        'pending_rate': round((pending / total) * 100) if total > 0 else 0,
        'approved_count': approved,
        'rejected_count': rejected,
        'pending_count': pending,
    }

def generate_audit_report():
    """Génère rapport d'audit complet"""
    metrics = calculate_quality_metrics()
    
    # Par algorithme
    by_algorithm = {}
    for reco in RECOMMENDATIONS_DB.values():
        algo = reco['algorithm']
        if algo not in by_algorithm:
            by_algorithm[algo] = {
                'count': 0,
                'avg_confidence': 0,
                'approved': 0,
                'rejected': 0,
            }
        
        by_algorithm[algo]['count'] += 1
        by_algorithm[algo]['avg_confidence'] += reco['confidence_score']
        
        if reco['status'] == 'approved':
            by_algorithm[algo]['approved'] += 1
        elif reco['status'] == 'rejected':
            by_algorithm[algo]['rejected'] += 1
    
    for algo, data in by_algorithm.items():
        if data['count'] > 0:
            data['avg_confidence'] = round((data['avg_confidence'] / data['count']) * 100)
            data['approval_rate'] = round((data['approved'] / data['count']) * 100)
    
    # Issues détectées
    issues = []
    for reco_id, reco in RECOMMENDATIONS_DB.items():
        if reco['confidence_score'] < 0.7:
            issues.append({
                'reco_id': reco_id,
                'issue': 'Low confidence score',
                'severity': 'medium',
                'value': reco['confidence_score'],
            })
        
        if reco['data_quality_score'] < 0.6:
            issues.append({
                'reco_id': reco_id,
                'issue': 'Low data quality',
                'severity': 'high',
                'value': reco['data_quality_score'],
            })
        
        if len(reco['products_recommended']) < 2:
            issues.append({
                'reco_id': reco_id,
                'issue': 'Insufficient product diversity',
                'severity': 'low',
                'value': len(reco['products_recommended']),
            })
    
    return {
        'timestamp': datetime.now().isoformat(),
        'global_metrics': metrics,
        'by_algorithm': by_algorithm,
        'issues': issues,
        'issues_count': len(issues),
    }

# ============================================================================
# ROUTES - PAGE WEB
# ============================================================================

@recommendations_bp.route('', methods=['GET'])
def list_recommendations():
    """Liste toutes les recommandations"""
    # Filtres
    status_filter = request.args.get('status')  # pending_review, approved, rejected
    algorithm_filter = request.args.get('algorithm')
    
    recommendations_list = []
    for reco_id, reco in RECOMMENDATIONS_DB.items():
        if status_filter and reco['status'] != status_filter:
            continue
        if algorithm_filter and reco['algorithm'] != algorithm_filter:
            continue
        
        recommendations_list.append({
            'reco_id': reco_id,
            **reco
        })
    
    # Trier par date (plus récent en premier)
    recommendations_list.sort(key=lambda x: x['generated_at'], reverse=True)
    
    # Métriques
    metrics = calculate_quality_metrics()
    
    return render_template(
        'recommendations/list.html',
        recommendations=recommendations_list,
        metrics=metrics,
        algorithms=ALGORITHMS_INFO,
        status_filter=status_filter,
        algorithm_filter=algorithm_filter,
    )

@recommendations_bp.route('/<reco_id>', methods=['GET'])
def view_recommendation(reco_id):
    """Affiche détails d'une recommandation"""
    if reco_id not in RECOMMENDATIONS_DB:
        flash(f'Recommandation "{reco_id}" non trouvée', 'error')
        return redirect(url_for('recommendations.list_recommendations'))
    
    reco = RECOMMENDATIONS_DB[reco_id]
    algo_info = ALGORITHMS_INFO.get(reco['algorithm'], {})
    
    return render_template(
        'recommendations/detail.html',
        reco_id=reco_id,
        recommendation=reco,
        algorithm_info=algo_info,
    )

# ============================================================================
# ROUTES - API JSON
# ============================================================================

@recommendations_bp.route('/<reco_id>/feedback', methods=['POST'])
def submit_feedback(reco_id):
    """Soumet feedback pour une recommandation"""
    if reco_id not in RECOMMENDATIONS_DB:
        return jsonify({'success': False, 'message': 'Recommendation not found'}), 404
    
    try:
        data = request.get_json()
        rating = data.get('rating')  # 1-5
        comment = data.get('comment', '')
        action = data.get('action')  # 'approve' or 'reject'
        
        if not rating or not action:
            return jsonify({'success': False, 'message': 'Rating and action required'}), 400
        
        reco = RECOMMENDATIONS_DB[reco_id]
        reco['feedback'] = {
            'rating': rating,
            'comment': comment,
        }
        reco['status'] = 'approved' if action == 'approve' else 'rejected'
        reco['feedback_by'] = 'current_user@example.com'  # TODO: get from session
        reco['feedback_at'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'message': f'Recommandation {action}d',
            'new_status': reco['status'],
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@recommendations_bp.route('/api/quality-metrics', methods=['GET'])
def quality_metrics():
    """Retourne métriques de qualité"""
    metrics = calculate_quality_metrics()
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'metrics': metrics,
    })

@recommendations_bp.route('/api/audit', methods=['GET'])
def audit_report():
    """Génère rapport d'audit"""
    report = generate_audit_report()
    return jsonify(report)

@recommendations_bp.route('/<reco_id>/regenerate', methods=['POST'])
def regenerate_recommendation(reco_id):
    """Régénère une recommandation"""
    if reco_id not in RECOMMENDATIONS_DB:
        return jsonify({'success': False, 'message': 'Recommendation not found'}), 404
    
    try:
        # En production: appeler le moteur de recommandation
        # Pour démo: simuler régénération
        reco = RECOMMENDATIONS_DB[reco_id]
        reco['generated_at'] = datetime.now().isoformat()
        reco['status'] = 'pending_review'
        reco['confidence_score'] = min(reco['confidence_score'] + 0.05, 1.0)
        
        return jsonify({
            'success': True,
            'message': 'Recommandation régénérée',
            'new_confidence': reco['confidence_score'],
            'generated_at': reco['generated_at'],
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@recommendations_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@recommendations_bp.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500
