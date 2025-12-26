#!/usr/bin/env python
"""Database initialization script.

Usage:
    python scripts/init_db.py --init          # Initialize database with migrations
    python scripts/init_db.py --drop          # Drop all tables (USE WITH CAUTION)
    python scripts/init_db.py --reset         # Drop and reinitialize
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.db.database import init_db, drop_db, engine, Base
from core.db.models import (
    Product, ProductAlias, Customer, OrderLine, ContactEvent,
    ClientMasterProfile, RecoRun, RecoItem, AuditItem, OutcomeEvent
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize database by creating all tables."""
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("✓ Database initialized successfully")
        logger.info(f"  Connected to: {os.getenv('DATABASE_URL', 'localhost:5432')}")
        logger.info(f"  Tables created:")
        logger.info(f"    - product")
        logger.info(f"    - product_alias")
        logger.info(f"    - customer")
        logger.info(f"    - order_line")
        logger.info(f"    - contact_event")
        logger.info(f"    - client_master_profile")
        logger.info(f"    - reco_run")
        logger.info(f"    - reco_item")
        logger.info(f"    - audit_item")
        logger.info(f"    - outcome_event")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {str(e)}")
        return False


def drop_database():
    """Drop all tables from the database."""
    confirmation = input(
        "\n⚠️  WARNING: This will delete ALL data!\n"
        "Type 'yes' to confirm: "
    )
    if confirmation.lower() != 'yes':
        logger.info("Drop cancelled.")
        return False
    
    logger.info("Dropping all tables...")
    try:
        drop_db()
        logger.info("✓ All tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to drop tables: {str(e)}")
        return False


def reset_database():
    """Drop and reinitialize database."""
    if drop_database():
        return initialize_database()
    return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == '--init':
        success = initialize_database()
    elif command == '--drop':
        success = drop_database()
    elif command == '--reset':
        success = reset_database()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
