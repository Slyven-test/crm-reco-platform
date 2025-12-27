"""
Flask Routes pour les Connecteurs

Endpoints:
  GET  /connectors                    Liste connecteurs
  GET  /connectors/<name>             Détails connecteur
  POST /connectors                    Enregistrer connecteur
  POST /connectors/<name>/test        Test connexion
  POST /connectors/<name>/sync        Lancer sync
  GET  /connectors/<name>/logs        Logs de sync
  GET  /connectors/status             Status global
  GET  /connectors/metrics            Métriques
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, timedelta
from connectors import ConnectorManager, ConnectorType, OdooConnector, iSaVigneConnector
import logging
import os

logger = logging.getLogger(__name__)

# Blueprint
connectors_bp = Blueprint('connectors', __name__, url_prefix='/connectors')

# Global ConnectorManager instance
manager = None


def init_connector_manager(config_file=".env"):
    """Initialiser le manager"""
    global manager
    manager = ConnectorManager(config_file)
    manager.load_config()
    logger.info("ConnectorManager initialized")


# ============================================================================
# PAGE PRINCIPALE: Lister tous les connecteurs
# ============================================================================

@connectors_bp.route('/', methods=['GET'])
def list_connectors():
    """
    Afficher la page principale avec tous les connecteurs.
    
    Template: connectors/list.html
    Contexte:
      - connectors: Dict {name: {type, status, last_sync, ...}}
      - status: Status global {registered, healthy, error, ...}
      - metrics: Métriques {total_records, total_syncs, ...}
    """
    try:
        # Récupérer info
        connectors = manager.list_connectors()
        status = manager.get_status()
        metrics = manager.get_metrics()
        recent_syncs = manager.get_sync_history(limit=5)
        
        return render_template(
            'connectors/list.html',
            connectors=connectors,
            status=status,
            metrics=metrics,
            recent_syncs=recent_syncs,
        )
    except Exception as e:
        logger.error(f"Error listing connectors: {str(e)}")
        flash(f"Erreur: {str(e)}", "error")
        return render_template('connectors/list.html', connectors={}, error=str(e))


# ============================================================================
# FORM: Enregistrer nouveau connecteur
# ============================================================================

@connectors_bp.route('/new', methods=['GET', 'POST'])
def register_connector():
    """
    Formulaire pour enregistrer un nouveau connecteur.
    
    GET: Afficher le formulaire
    POST: Traiter l'enregistrement
    """
    if request.method == 'GET':
        return render_template(
            'connectors/register.html',
            connector_types=[t.value for t in ConnectorType]
        )
    
    # POST
    try:
        connector_name = request.form.get('connector_name', '').strip()
        connector_type_str = request.form.get('connector_type', '').strip()
        
        # Validation
        if not connector_name:
            flash("Nom du connecteur requis", "error")
            return redirect(url_for('connectors.register_connector'))
        
        if connector_name in manager.connectors:
            flash(f"Connecteur '{connector_name}' existe déjà", "error")
            return redirect(url_for('connectors.register_connector'))
        
        # Déterminer le type
        try:
            connector_type = ConnectorType(connector_type_str)
        except ValueError:
            flash(f"Type de connecteur invalide: {connector_type_str}", "error")
            return redirect(url_for('connectors.register_connector'))
        
        # Récupérer la config selon le type
        config = {}
        
        if connector_type == ConnectorType.ISAVIGNE:
            config['isavigne_export_path'] = request.form.get('isavigne_export_path', '').strip()
            config['isavigne_file_pattern'] = request.form.get('isavigne_file_pattern', '*.csv')
            config['encoding'] = request.form.get('encoding', 'utf-8')
            
            if not config['isavigne_export_path']:
                flash("Chemin d'export iSaVigne requis", "error")
                return redirect(url_for('connectors.register_connector'))
        
        elif connector_type == ConnectorType.ODOO:
            config['odoo_url'] = request.form.get('odoo_url', '').strip()
            config['odoo_db'] = request.form.get('odoo_db', '').strip()
            config['odoo_user'] = request.form.get('odoo_user', '').strip()
            config['odoo_api_key'] = request.form.get('odoo_api_key', '').strip()
            config['odoo_company_id'] = request.form.get('odoo_company_id')
            
            required_odoo = ['odoo_url', 'odoo_db', 'odoo_user', 'odoo_api_key']
            if not all(config.get(k) for k in required_odoo):
                flash("Tous les paramètres Odoo sont requis", "error")
                return redirect(url_for('connectors.register_connector'))
        
        # Enregistrer le connecteur
        if not manager.register_connector(connector_name, connector_type, config):
            flash(f"Erreur lors de l'enregistrement du connecteur", "error")
            return redirect(url_for('connectors.register_connector'))
        
        # Sauvegarder config
        manager.save_config(manager.config)
        
        flash(f"✓ Connecteur '{connector_name}' enregistré avec succès", "success")
        return redirect(url_for('connectors.view_connector', name=connector_name))
    
    except Exception as e:
        logger.error(f"Error registering connector: {str(e)}")
        flash(f"Erreur: {str(e)}", "error")
        return redirect(url_for('connectors.register_connector'))


# ============================================================================
# DÉTAILS: Afficher un connecteur spécifique
# ============================================================================

@connectors_bp.route('/<name>', methods=['GET'])
def view_connector(name):
    """
    Afficher les détails d'un connecteur.
    
    Template: connectors/detail.html
    Contexte:
      - connector_name: Nom du connecteur
      - status: Status du connecteur
      - sync_logs: Historique des syncs
    """
    try:
        connector = manager.get_connector(name)
        
        if not connector:
            flash(f"Connecteur non trouvé: {name}", "error")
            return redirect(url_for('connectors.list_connectors'))
        
        status = connector.get_status()
        sync_logs = manager.get_sync_history(connector_name=name, limit=20)
        
        return render_template(
            'connectors/detail.html',
            connector_name=name,
            status=status,
            sync_logs=sync_logs,
        )
    except Exception as e:
        logger.error(f"Error viewing connector {name}: {str(e)}")
        flash(f"Erreur: {str(e)}", "error")
        return redirect(url_for('connectors.list_connectors'))


# ============================================================================
# API: Test connexion
# ============================================================================

@connectors_bp.route('/<name>/test', methods=['POST'])
def test_connector(name):
    """
    Tester la connexion d'un connecteur.
    
    Response JSON:
      {
        "success": True/False,
        "message": "Connexion OK" / "Erreur...",
        "status": "healthy" / "error"
      }
    """
    try:
        connector = manager.get_connector(name)
        
        if not connector:
            return jsonify({
                "success": False,
                "message": f"Connecteur non trouvé: {name}",
                "status": "error"
            }), 404
        
        # Tester
        success = manager.test_connector(name)
        
        status = connector.get_status()
        
        return jsonify({
            "success": success,
            "message": "✓ Connexion OK" if success else f"✗ {connector.last_error}",
            "status": status['status'],
        }), 200 if success else 400
    
    except Exception as e:
        logger.error(f"Error testing connector {name}: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
            "status": "error"
        }), 500


# ============================================================================
# API: Lancer synchronisation
# ============================================================================

@connectors_bp.route('/<name>/sync', methods=['POST'])
def sync_connector(name):
    """
    Lancer une synchronisation.
    
    Params (POST JSON):
      - source: (optionnel) "customers", "products", etc.
      - last_sync: (optionnel) ISO datetime pour pull incrémental
    
    Response JSON:
      {
        "success": True/False,
        "records_processed": {"CUSTOMERS": 150, "PRODUCTS": 45, ...},
        "duration_seconds": 12.5,
        "errors": [...],
        "warnings": [...]
      }
    """
    try:
        connector = manager.get_connector(name)
        
        if not connector:
            return jsonify({
                "success": False,
                "message": f"Connecteur non trouvé: {name}",
            }), 404
        
        # Parser les params
        data = request.get_json() or {}
        kwargs = {}
        
        if 'source' in data:
            kwargs['source'] = data['source']
        
        if 'last_sync' in data:
            try:
                kwargs['last_sync'] = datetime.fromisoformat(data['last_sync'])
            except:
                pass
        
        # Lancer la sync
        logger.info(f"Starting sync for {name}")
        result = manager.sync_connector(name, **kwargs)
        
        return jsonify({
            "success": result.success,
            "connector_type": result.connector_type.value if result.connector_type else None,
            "records_processed": result.records_processed,
            "duration_seconds": round(result.duration_seconds, 2),
            "errors": result.errors,
            "warnings": result.warnings,
            "timestamp": result.timestamp.isoformat(),
        }), 200 if result.success else 400
    
    except Exception as e:
        logger.error(f"Error syncing connector {name}: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
        }), 500


# ============================================================================
# API: Historique de sync
# ============================================================================

@connectors_bp.route('/<name>/logs', methods=['GET'])
def get_sync_logs(name):
    """
    Récupérer l'historique des syncs pour un connecteur.
    
    Params:
      - limit: (optionnel, default 50) Nombre de logs à retourner
      - offset: (optionnel, default 0) Décalage pour pagination
    
    Response JSON:
      {
        "connector_name": "isavigne_prod",
        "total": 15,
        "logs": [
          {
            "timestamp": "2025-12-27T16:10:00",
            "success": True,
            "records_processed": {...},
            "duration_seconds": 12.5,
            "errors": []
          },
          ...
        ]
      }
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Récupérer les logs
        all_logs = manager.get_sync_history(connector_name=name)
        total = len(all_logs)
        
        # Paginer
        logs = all_logs[offset:offset+limit]
        
        return jsonify({
            "connector_name": name,
            "total": total,
            "offset": offset,
            "limit": limit,
            "logs": logs
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting sync logs for {name}: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
        }), 500


# ============================================================================
# API: Status global
# ============================================================================

@connectors_bp.route('/api/status', methods=['GET'])
def api_status():
    """
    Récupérer le status global du système.
    
    Response JSON:
      {
        "timestamp": "2025-12-27T16:10:00",
        "connectors_registered": 2,
        "connectors_by_status": {"healthy": 1, "error": 1},
        "total_syncs": 10,
        "successful_syncs": 9,
        "failed_syncs": 1,
        "avg_sync_duration_seconds": 12.5
      }
    """
    try:
        status = manager.get_status()
        status['timestamp'] = datetime.now().isoformat()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# API: Métriques
# ============================================================================

@connectors_bp.route('/api/metrics', methods=['GET'])
def api_metrics():
    """
    Récupérer les métriques d'exécution.
    
    Response JSON:
      {
        "timestamp": "2025-12-27T16:10:00",
        "total_records_synced": 5000,
        "records_by_table": {"CUSTOMERS": 1500, "PRODUCTS": 500, ...},
        "total_errors": 5,
        "total_warnings": 12
      }
    """
    try:
        metrics = manager.get_metrics()
        metrics['timestamp'] = datetime.now().isoformat()
        return jsonify(metrics), 200
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        return jsonify({"error": str(e)}), 500


print("✓ Connectors routes loaded")
