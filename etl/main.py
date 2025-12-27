"""
Orchestration du Pipeline ETL Complet
Version: 1.0
Auteur: Projet CRM Ruhlmann

Rôle: Lancer le pipeline ETL complet:
  1. Ingestion RAW → STAGING
  2. Transformation STAGING → CURATED
  3. Chargement CURATED → PostgreSQL

Usage:
  python etl/main.py

Cela lancera automatiquement les 3 étapes et affichera un rapport final.
"""

import time
import sys
from datetime import datetime
from pathlib import Path

from etl.config import logger
from etl.ingest_raw import ingest_all_datasets
from etl.transform_sales import process_all_sales_files
from etl.load_postgres import load_all_curated, verify_load


def print_header(title):
    """
    Affiche un en-tête formatté
    """
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_section(title):
    """
    Affiche un titre de section
    """
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_summary(title, data):
    """
    Affiche un résumé avec formattage
    """
    print(f"\n{title}")
    print("-" * 70)
    for key, value in data.items():
        print(f"  {key}: {value}")
    print("-" * 70)


def run_etl_pipeline():
    """
    Orchestre le pipeline ETL complet:
    1. Ingestion RAW → STAGING
    2. Transformation STAGING → CURATED
    3. Chargement CURATED → PostgreSQL
    
    Returns:
        dict avec résultats complets du pipeline
    """
    start_time = time.time()
    start_datetime = datetime.now()
    
    try:
        print_header("📊 DÉMARRAGE PIPELINE ETL COMPLET")
        print(f"Date/Heure: {start_datetime.isoformat()}")
        print(f"Version: 1.0 - Projet CRM Ruhlmann\n")
        
        # ========================================================================
        # ÉTAPE 1: INGESTION RAW → STAGING
        # ========================================================================
        print_section("🔵 ÉTAPE 1/3: INGESTION RAW → STAGING")
        
        stage1_start = time.time()
        logger.info("\n=== ÉTAPE 1: INGESTION RAW → STAGING ===")
        
        try:
            ingest_results = ingest_all_datasets()
            stage1_duration = time.time() - stage1_start
            
            # Résumé ingestion
            ingest_summary = {
                'Durée': f"{stage1_duration:.2f}s",
                'Statut': '✅ SUCCÈS' if ingest_results else '❌ ERREUR',
                'Fichiers traités': len(ingest_results) if isinstance(ingest_results, dict) else 0
            }
            print_summary("📋 RÉSUMÉ INGESTION", ingest_summary)
            
        except Exception as e:
            stage1_duration = time.time() - stage1_start
            logger.error(f"Erreur ÉTAPE 1: {str(e)}", exc_info=True)
            print(f"\n❌ ERREUR ÉTAPE 1: {str(e)}")
            return {
                'success': False,
                'stage': 1,
                'error': str(e),
                'duration': stage1_duration
            }
        
        # ========================================================================
        # ÉTAPE 2: TRANSFORMATION STAGING → CURATED
        # ========================================================================
        print_section("🔵 ÉTAPE 2/3: TRANSFORMATION STAGING → CURATED")
        
        stage2_start = time.time()
        logger.info("\n=== ÉTAPE 2: TRANSFORMATION STAGING → CURATED ===")
        
        try:
            transform_results = process_all_sales_files()
            stage2_duration = time.time() - stage2_start
            
            # Résumé transformation
            transform_summary = {
                'Durée': f"{stage2_duration:.2f}s",
                'Statut': '✅ SUCCÈS' if transform_results else '❌ ERREUR',
                'Fichiers transformés': transform_results.get('curated_files', 0) if isinstance(transform_results, dict) else 0
            }
            print_summary("📋 RÉSUMÉ TRANSFORMATION", transform_summary)
            
        except Exception as e:
            stage2_duration = time.time() - stage2_start
            logger.error(f"Erreur ÉTAPE 2: {str(e)}", exc_info=True)
            print(f"\n❌ ERREUR ÉTAPE 2: {str(e)}")
            return {
                'success': False,
                'stage': 2,
                'error': str(e),
                'duration': stage2_duration
            }
        
        # ========================================================================
        # ÉTAPE 3: CHARGEMENT CURATED → PostgreSQL
        # ========================================================================
        print_section("🔵 ÉTAPE 3/3: CHARGEMENT CURATED → PostgreSQL")
        
        stage3_start = time.time()
        logger.info("\n=== ÉTAPE 3: CHARGEMENT CURATED → PostgreSQL ===")
        
        try:
            load_results = load_all_curated()
            verification = verify_load(load_results)
            stage3_duration = time.time() - stage3_start
            
            # Résumé chargement
            load_summary = {
                'Durée': f"{stage3_duration:.2f}s",
                'Statut': '✅ SUCCÈS' if verification['success'] else '❌ ERREUR',
                'Tables réussies': verification.get('total_success', 0),
                'Tables échouées': verification.get('total_failed', 0),
                'Total lignes chargées': verification.get('total_rows', 0)
            }
            print_summary("📋 RÉSUMÉ CHARGEMENT", load_summary)
            
        except Exception as e:
            stage3_duration = time.time() - stage3_start
            logger.error(f"Erreur ÉTAPE 3: {str(e)}", exc_info=True)
            print(f"\n❌ ERREUR ÉTAPE 3: {str(e)}")
            return {
                'success': False,
                'stage': 3,
                'error': str(e),
                'duration': stage3_duration
            }
        
        # ========================================================================
        # RÉSUMÉ FINAL
        # ========================================================================
        total_duration = time.time() - start_time
        
        print_section("🌟 PIPELINE COMPLET - RÉSUMÉ FINAL")
        
        final_summary = {
            'Démarrage': start_datetime.isoformat(),
            'Fin': datetime.now().isoformat(),
            'Durée totale': f"{total_duration:.2f}s",
            'Étape 1 (Ingestion)': f"{stage1_duration:.2f}s",
            'Étape 2 (Transformation)': f"{stage2_duration:.2f}s",
            'Étape 3 (Chargement)': f"{stage3_duration:.2f}s",
        }
        print_summary("📋 TIMINGS", final_summary)
        
        logger.info(f"\n✅ PIPELINE ETL TERMINÉ AVEC SUCCÈS en {total_duration:.2f}s")
        
        print("\n" + "="*70)
        print("  🌟 SUCCÈS COMPLET - Pipeline ETL Fonctionnel! 🚀")
        print("="*70)
        print("\nProchaines étapes:")
        print("  1. Vérifier les données dans PostgreSQL")
        print("  2. Consulter les logs: exports/logs/")
        print("  3. Intégrer Brevo pour les emails")
        print("  4. Créer le moteur de recommandations")
        print("\nGitHub: https://github.com/Slyven-test/crm-reco-platform")
        print("\n" + "="*70 + "\n")
        
        return {
            'success': True,
            'total_duration': total_duration,
            'stage_1_duration': stage1_duration,
            'stage_2_duration': stage2_duration,
            'stage_3_duration': stage3_duration,
            'ingest_results': ingest_results,
            'transform_results': transform_results,
            'load_results': load_results,
            'verification': verification
        }
        
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"\n❌ ERREUR PIPELINE GLOBALE après {total_duration:.2f}s: {str(e)}", exc_info=True)
        
        print(f"\n" + "="*70)
        print(f"  ❌ ERREUR CRITIQUE")
        print(f"="*70")
        print(f"\nErreur: {str(e)}")
        print(f"Durée avant erreur: {total_duration:.2f}s")
        print(f"\nConsulter les logs pour détails complets: exports/logs/")
        print("\n" + "="*70 + "\n")
        
        return {
            'success': False,
            'error': str(e),
            'total_duration': total_duration
        }


if __name__ == '__main__':
    # Démarrage du pipeline
    result = run_etl_pipeline()
    
    # Code de sortie
    exit_code = 0 if result['success'] else 1
    sys.exit(exit_code)
