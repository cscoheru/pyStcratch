"""
Database migration script: v1.0 → v1.1
Adds support for Hugging Face datasets and enhanced content classification

Run: python3 storage/migration_add_huggingface_fields.py
"""
import os
import sys
from datetime import datetime

# Add project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa
from sqlalchemy import create_engine, text
from loguru import logger

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "crawler.db")


def backup_database():
    """Create a backup of the database."""
    import shutil
    from pathlib import Path

    db_path = Path(DB_PATH)
    if not db_path.exists():
        logger.warning(f"Database file not found: {db_path}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"crawler.db.backup_{timestamp}"

    shutil.copy2(db_path, backup_path)
    logger.info(f"Database backed up to: {backup_path}")
    return backup_path


def validate_pre_migration():
    """Validate database state before migration."""
    engine = create_engine(f"sqlite:///{DB_PATH}")

    with engine.connect() as conn:
        # Check if new columns already exist
        result = conn.execute(text("PRAGMA table_info(articles)"))
        columns = [row[1] for row in result.fetchall()]

        new_columns = [
            'content_type', 'dataset_source', 'sentiment', 'sentiment_label',
            'question', 'answer', 'choices', 'similarity', 'language'
        ]

        existing_new = [col for col in new_columns if col in columns]

        if existing_new:
            logger.warning(f"New columns already exist: {existing_new}")
            logger.info("Database appears to be already migrated")
            return False

        # Check article count
        result = conn.execute(text("SELECT COUNT(*) FROM articles"))
        count = result.scalar()
        logger.info(f"Current article count: {count}")

        return True

    return True


def upgrade():
    """Upgrade database to v1.1 - Add Hugging Face support fields."""
    engine = create_engine(f"sqlite:///{DB_PATH}")

    logger.info("Starting database migration to v1.1...")

    with engine.connect() as conn:
        # Step 1: Add new columns
        logger.info("Step 1: Adding new columns...")
        new_columns = {
            'content_type': sa.Column('content_type', sa.String(50), nullable=True),
            'dataset_source': sa.Column('dataset_source', sa.String(200), nullable=True),
            'sentiment': sa.Column('sentiment', sa.String(20), nullable=True),
            'sentiment_label': sa.Column('sentiment_label', sa.Integer, nullable=True),
            'question': sa.Column('question', sa.Text, nullable=True),
            'answer': sa.Column('answer', sa.Text, nullable=True),
            'choices': sa.Column('choices', sa.Text, nullable=True),
            'similarity': sa.Column('similarity', sa.String(20), nullable=True),
            'language': sa.Column('language', sa.String(10), nullable=True),
        }

        for col_name, col_def in new_columns.items():
            try:
                conn.execute(text(f"ALTER TABLE articles ADD COLUMN {col_name} {col_def}"))
                logger.info(f"  ✓ Added column: {col_name}")
            except Exception as e:
                if "duplicate column" not in str(e):
                    logger.warning(f"  ✗ Failed to add {col_name}: {e}")

        # Step 2: Set default values for existing data
        logger.info("Step 2: Setting default values...")
        conn.execute(text("UPDATE articles SET content_type = 'article' WHERE content_type IS NULL"))
        conn.execute(text("UPDATE articles SET language = 'zh' WHERE language IS NULL"))
        conn.execute(text("UPDATE articles SET similarity = 'medium' WHERE similarity IS NULL"))
        logger.info("  ✓ Default values set")

        # Step 3: Infer content_type from source
        logger.info("Step 3: Inferring content_type from source...")
        conn.execute(text("UPDATE articles SET content_type = 'social' WHERE source = 'weibo'"))
        conn.execute(text("UPDATE articles SET content_type = 'qa' WHERE source = 'zhihu' AND dataset_source IS NOT NULL"))
        logger.info("  ✓ content_type inferred")

        # Step 4: Create indexes
        logger.info("Step 4: Creating indexes...")
        indexes = [
            ("idx_content_type", "CREATE INDEX IF NOT EXISTS idx_content_type ON articles(content_type)"),
            ("idx_sentiment", "CREATE INDEX IF NOT EXISTS idx_sentiment ON articles(sentiment)"),
            ("idx_dataset_source", "CREATE INDEX IF NOT EXISTS idx_dataset_source ON articles(dataset_source)"),
            ("idx_language", "CREATE INDEX IF NOT EXISTS idx_language ON articles(language)"),
        ]

        for idx_name, idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                logger.info(f"  ✓ Created index: {idx_name}")
            except Exception as e:
                logger.warning(f"  ✗ Failed to create index {idx_name}: {e}")

        # Step 5: Commit changes
        conn.commit()
        logger.info("✅ Migration to v1.1 completed successfully")


def downgrade():
    """Rollback database to v1.0 - Remove Hugging Face support fields."""
    engine = create_engine(f"sqlite:///{DB_PATH}")

    logger.info("Rolling back database to v1.0...")

    with engine.connect() as conn:
        # Step 1: Drop indexes
        logger.info("Step 1: Dropping indexes...")
        indexes = [
            "idx_content_type", "idx_sentiment", "idx_dataset_source", "idx_language"
        ]

        for idx_name in indexes:
            try:
                conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                logger.info(f"  ✓ Dropped index: {idx_name}")
            except Exception as e:
                logger.warning(f"  ✗ Failed to drop index {idx_name}: {e}")

        # Step 2: Drop columns
        logger.info("Step 2: Dropping columns...")
        columns_to_drop = [
            'content_type', 'dataset_source', 'sentiment', 'sentiment_label',
            'question', 'answer', 'choices', 'similarity', 'language'
        ]

        for col_name in columns_to_drop:
            try:
                conn.execute(text(f"ALTER TABLE articles DROP COLUMN {col_name}"))
                logger.info(f"  ✓ Dropped column: {col_name}")
            except Exception as e:
                if "no such column" not in str(e):
                    logger.warning(f"  ✗ Failed to drop column {col_name}: {e}")

        # Commit changes
        conn.commit()
        logger.info("✅ Rollback to v1.0 completed successfully")


def validate_post_migration():
    """Validate database state after migration."""
    engine = create_engine(f"sqlite:///{DB_PATH}")

    with engine.connect() as conn:
        logger.info("Validating post-migration state...")

        # Check all articles have content_type
        result = conn.execute(text("SELECT COUNT(*) FROM articles WHERE content_type IS NULL"))
        null_content_type = result.scalar()
        if null_content_type > 0:
            logger.error(f"  ✗ Found {null_content_type} articles without content_type")
            return False
        logger.info(f"  ✓ All articles have content_type")

        # Check all articles have language
        result = conn.execute(text("SELECT COUNT(*) FROM articles WHERE language IS NULL"))
        null_language = result.scalar()
        if null_language > 0:
            logger.error(f"  ✗ Found {null_language} articles without language")
            return False
        logger.info(f"  ✓ All articles have language")

        # Check content_type distribution
        result = conn.execute(text("""
            SELECT content_type, COUNT(*) as count
            FROM articles
            GROUP BY content_type
        """))
        logger.info("  Content type distribution:")
        for row in result.fetchall():
            logger.info(f"    - {row[0]}: {row[1]}")

        logger.info("✅ Post-migration validation passed")
        return True


def main():
    """Main migration function."""
    import argparse

    parser = argparse.ArgumentParser(description="Database migration v1.0 → v1.1")
    parser.add_argument('--action', choices=['upgrade', 'downgrade', 'validate', 'backup'],
                       default='upgrade', help='Migration action')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip database backup')

    args = parser.parse_args()

    # Check database exists
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found: {DB_PATH}")
        return 1

    # Execute action
    if args.action == 'backup':
        backup_database()

    elif args.action == 'upgrade':
        if not args.no_backup:
            backup_path = backup_database()
            if not backup_path:
                logger.warning("Proceeding without backup...")

        if validate_pre_migration():
            upgrade()
            if validate_post_migration():
                logger.info("=" * 60)
                logger.info("✅ Migration completed successfully!")
                logger.info("=" * 60)
                return 0
        logger.error("❌ Migration validation failed")
        return 1

    elif args.action == 'downgrade':
        downgrade()
        logger.info("=" * 60)
        logger.info("✅ Rollback completed successfully!")
        logger.info("=" * 60)
        return 0

    elif args.action == 'validate':
        if validate_post_migration():
            logger.info("✅ Database is in valid state")
            return 0
        else:
            logger.error("❌ Database validation failed")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
