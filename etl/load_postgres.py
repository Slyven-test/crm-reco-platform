"""
Étape 3: Chargement des données CURATED en PostgreSQL
Version: 1.0
Auteur: Projet CRM Ruhlmann

Rôle: Charger les fichiers CSV transformés (CURATED) dans les tables PostgreSQL
Fonctionnalités:
  - Détection des doublons
  - Gestion des clés étrangères
  - Logs détaillés
  - Gestion des erreurs robuste
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from etl.config import DATABASE_URL, CURATED_DIR, logger


def load_table(table_name, csv_file, schema='etl'):
    """
    Charge un fichier CSV dans une table PostgreSQL
    
    Args:
        table_name: nom de la table cible (ex: 'ventes_lignes')
        csv_file: chemin du fichier CURATED CSV
        schema: schéma PostgreSQL (défaut: 'etl')
    
    Returns:
        dict avec statut de chargement
    """
    try:
        logger.info(f"\n📥 Chargement {schema}.{table_name}")
        logger.info(f"   Source: {csv_file}")
        
        # Charger le CSV
        df = pd.read_csv(csv_file)
        initial_rows = len(df)
        logger.info(f"   Chargé: {initial_rows} lignes brutes")
        
        # Détection des doublons selon la table
        duplicates_removed = 0
        if table_name == 'ventes_lignes':
            # Clé naturelle: document_id + produit_key + client_code
            key_cols = ['document_id', 'produit_key', 'client_code']
            if all(col in df.columns for col in key_cols):
                df_dedup = df.drop_duplicates(subset=key_cols, keep='last')
                duplicates_removed = initial_rows - len(df_dedup)
                if duplicates_removed > 0:
                    logger.warning(f"   ⚠️ Doublons détectés: {duplicates_removed}")
                df = df_dedup
        
        elif table_name == 'clients':
            # Clé: client_code
            if 'client_code' in df.columns:
                df_dedup = df.drop_duplicates(subset=['client_code'], keep='last')
                duplicates_removed = initial_rows - len(df_dedup)
                if duplicates_removed > 0:
                    logger.warning(f"   ⚠️ Doublons clients: {duplicates_removed}")
                df = df_dedup
        
        elif table_name == 'produits':
            # Clé: produit_key
            if 'produit_key' in df.columns:
                df_dedup = df.drop_duplicates(subset=['produit_key'], keep='last')
                duplicates_removed = initial_rows - len(df_dedup)
                if duplicates_removed > 0:
                    logger.warning(f"   ⚠️ Doublons produits: {duplicates_removed}")
                df = df_dedup
        
        final_rows = len(df)
        
        # Connexion PostgreSQL
        engine = create_engine(DATABASE_URL)
        
        # Test de connexion
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            db_version = result.fetchone()[0]
            logger.info(f"   ✓ Connecté: {db_version.split(',')[0]}")
        
        # Chargement par lots (chunks)
        chunksize = 500
        total_loaded = 0
        
        with engine.begin() as conn:
            # Chargement
            df.to_sql(
                table_name,
                conn,
                schema=schema,
                if_exists='append',  # Ajouter, ne pas remplacer
                index=False,
                chunksize=chunksize,
                method='multi'  # Plus rapide
            )
            total_loaded = len(df)
        
        logger.info(f"   ✅ Succès: {total_loaded} lignes chargées")
        
        return {
            'success': True,
            'table': f"{schema}.{table_name}",
            'rows_initial': initial_rows,
            'rows_duplicates': duplicates_removed,
            'rows_loaded': total_loaded,
            'status': 'OK'
        }
        
    except IntegrityError as e:
        logger.error(f"   ✗ Erreur intégrité (clé étrangère): {str(e)}")
        return {
            'success': False,
            'table': f"{schema}.{table_name}",
            'error_type': 'IntegrityError',
            'error': str(e)
        }
    
    except SQLAlchemyError as e:
        logger.error(f"   ✗ Erreur SQL: {str(e)}")
        return {
            'success': False,
            'table': f"{schema}.{table_name}",
            'error_type': 'SQLAlchemyError',
            'error': str(e)
        }
    
    except Exception as e:
        logger.error(f"   ✗ Erreur inattendue: {str(e)}", exc_info=True)
        return {
            'success': False,
            'table': f"{schema}.{table_name}",
            'error_type': 'Exception',
            'error': str(e)
        }


def get_table_stats(schema, table_name):
    """
    Récupère les statistiques d'une table PostgreSQL
    
    Args:
        schema: schéma PostgreSQL
        table_name: nom de la table
    
    Returns:
        dict avec nombre de lignes et autres stats
    """
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            query = f"SELECT COUNT(*) as row_count FROM {schema}.{table_name};"
            result = conn.execute(text(query))
            count = result.fetchone()[0]
            return {'row_count': count, 'error': None}
    except Exception as e:
        return {'row_count': None, 'error': str(e)}


def load_all_curated():
    """
    Charge TOUS les fichiers curated en PostgreSQL
    Applique la logique de mapping fichier -> table
    
    Returns:
        dict avec résultats de chaque table
    """
    logger.info("\n" + "="*60)
    logger.info("🔵 ÉTAPE 3/3: CHARGEMENT CURATED → PostgreSQL")
    logger.info("="*60)
    
    results = {}
    curated_files = list(CURATED_DIR.glob('*.csv'))
    
    if not curated_files:
        logger.warning("⚠️ Aucun fichier CURATED détecté")
        return {'error': 'No curated files found'}
    
    logger.info(f"\nDétecté {len(curated_files)} fichier(s) CURATED\n")
    
    # Mapping fichier -> table
    for csv_file in curated_files:
        filename = csv_file.name.upper()
        
        if 'VENTES_LIGNES' in filename:
            table_name = 'ventes_lignes'
            schema = 'etl'
        elif 'CLIENTS' in filename:
            table_name = 'clients'
            schema = 'etl'
        elif 'PRODUITS' in filename:
            table_name = 'produits'
            schema = 'etl'
        elif 'STOCK' in filename:
            table_name = 'stock'
            schema = 'etl'
        else:
            logger.warning(f"⚠️ Fichier non reconnu: {csv_file.name}")
            continue
        
        # Charger la table
        result = load_table(table_name, str(csv_file), schema)
        full_table_name = f"{schema}.{table_name}"
        results[full_table_name] = result
        
        # Stats finales après chargement
        if result['success']:
            stats = get_table_stats(schema, table_name)
            result['total_rows_in_table'] = stats['row_count']
            logger.info(f"   📊 Total dans {schema}.{table_name}: {stats['row_count']} lignes")
    
    return results


def verify_load(results):
    """
    Vérifie que le chargement s'est bien déroulé
    
    Args:
        results: résultats du load_all_curated()
    
    Returns:
        dict avec statut de vérification
    """
    logger.info("\n" + "-"*60)
    logger.info("✓ VÉRIFICATION DU CHARGEMENT")
    logger.info("-"*60)
    
    total_success = sum(1 for r in results.values() if r.get('success', False))
    total_failed = sum(1 for r in results.values() if not r.get('success', True))
    total_rows = sum(r.get('rows_loaded', 0) for r in results.values())
    
    logger.info(f"\n📊 Statistiques:")
    logger.info(f"   Tables réussies: {total_success}")
    logger.info(f"   Tables échouées: {total_failed}")
    logger.info(f"   Total lignes chargées: {total_rows}")
    
    for table_name, result in results.items():
        if result['success']:
            logger.info(f"   ✅ {table_name}: {result['rows_loaded']} lignes")
        else:
            logger.error(f"   ❌ {table_name}: {result['error_type']}")
    
    return {
        'success': total_failed == 0,
        'total_success': total_success,
        'total_failed': total_failed,
        'total_rows': total_rows
    }


if __name__ == '__main__':
    logger.info(f"\nDémarrage à {datetime.now().isoformat()}\n")
    
    results = load_all_curated()
    verification = verify_load(results)
    
    logger.info("\n" + "="*60)
    if verification['success']:
        logger.info(f"✅ CHARGEMENT RÉUSSI - {verification['total_rows']} lignes")
    else:
        logger.error(f"❌ ERREURS DÉTECTÉES - {verification['total_failed']} table(s)")
    logger.info("="*60 + "\n")
