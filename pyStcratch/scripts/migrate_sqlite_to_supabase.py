"""
Migrate data from SQLite to Supabase.

This script:
1. Exports articles from SQLite using existing DatabaseManager
2. Batch imports to Supabase
3. Generates embeddings and migrates to Pinecone
4. Verifies data integrity

Usage:
    python scripts/migrate_sqlite_to_supabase.py
"""
import os
import sys
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from storage.database import DatabaseManager
from storage.supabase_client import SupabaseClient
from storage.pinecone_store import PineconeStore
from utils.embedding import QwenEmbedder


async def migrate_sqlite_to_supabase():
    """Migrate all data from SQLite to Supabase."""
    logger.info("Starting SQLite to Supabase migration...")

    # Initialize clients
    db_manager = DatabaseManager()
    supabase = SupabaseClient()
    embedder = QwenEmbedder()
    pinecone = PineconeStore()

    # Check if Supabase is configured
    if not supabase.client:
        logger.error("Supabase client not initialized. Check SUPABASE_URL and SUPABASE_SERVICE_KEY")
        return

    # Export from SQLite
    logger.info("Exporting articles from SQLite...")
    try:
        with db_manager.get_session() as session:
            from storage.models import Article
            articles = session.query(Article).all()
            logger.info(f"Found {len(articles)} articles in SQLite")

            if not articles:
                logger.warning("No articles to migrate")
                return

            # Convert to dict
            articles_data = [article.to_dict() for article in articles]
    except Exception as e:
        logger.error(f"Failed to export from SQLite: {e}")
        return

    # Import to Supabase
    logger.info("Importing articles to Supabase...")
    batch_size = 50
    success_count = 0
    failed_count = 0

    for i in range(0, len(articles_data), batch_size):
        batch = articles_data[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(articles_data)-1)//batch_size + 1}")

        try:
            result = await supabase.create_articles_batch(batch)
            success_count += result.get("success", 0)
            failed_count += result.get("failed", 0)

            if result.get("errors"):
                logger.warning(f"Batch errors: {result['errors']}")

        except Exception as e:
            logger.error(f"Failed to import batch: {e}")
            failed_count += len(batch)

    logger.info(f"Import complete: {success_count} succeeded, {failed_count} failed")

    # Verify data integrity
    logger.info("Verifying data integrity...")
    stats = await supabase.get_statistics()
    logger.info(f"Supabase stats: {stats['total_articles']} total articles")

    if stats["total_articles"] != len(articles_data):
        logger.warning(f"Count mismatch: SQLite={len(articles_data)}, Supabase={stats['total_articles']}")
    else:
        logger.info("Data integrity verified!")

    # Vectorize articles if Pinecone is configured
    if pinecone.index:
        logger.info("Starting vectorization...")
        await vectorize_articles(supabase, pinecone, embedder)
    else:
        logger.info("Pinecone not configured, skipping vectorization")

    logger.info("Migration complete!")


async def vectorize_articles(
    supabase: SupabaseClient,
    pinecone: PineconeStore,
    embedder: QwenEmbedder
):
    """Vectorize all articles and store in Pinecone."""
    logger.info("Fetching articles for vectorization...")

    page = 1
    page_size = 50
    total_vectorized = 0

    while True:
        result = await supabase.get_articles(page=page, page_size=page_size)
        articles = result.get("items", [])

        if not articles:
            break

        logger.info(f"Vectorizing page {page} ({len(articles)} articles)...")

        # Generate embeddings
        embeddings = await embedder.vectorize_articles(articles, batch_size=10)

        # Add to Pinecone
        if embeddings:
            success = await pinecone.add_vectors(articles, embeddings)
            if success:
                total_vectorized += len(articles)
            else:
                logger.error(f"Failed to add vectors for page {page}")

        page += 1

        # Stop if we've processed all articles
        if len(articles) < page_size:
            break

    logger.info(f"Vectorization complete: {total_vectorized} articles vectorized")

    # Verify vector count
    vector_count = await pinecone.get_vector_count()
    logger.info(f"Pinecone vector count: {vector_count}")


async def export_crawl_logs():
    """Export crawl logs from SQLite (optional)."""
    logger.info("Exporting crawl logs...")

    db_manager = DatabaseManager()

    try:
        with db_manager.get_session() as session:
            from storage.models import CrawlLog
            logs = session.query(CrawlLog).all()
            logger.info(f"Found {len(logs)} crawl logs")

            # Optionally migrate logs to Supabase if table exists
            # For now, just log the count

    except Exception as e:
        logger.error(f"Failed to export crawl logs: {e}")


def main():
    """Main entry point."""
    logger.info("=== SQLite to Supabase Migration ===")
    logger.info(f"Started at: {datetime.now()}")

    # Run async migration
    asyncio.run(migrate_sqlite_to_supabase())

    logger.info(f"Finished at: {datetime.now()}")


if __name__ == "__main__":
    main()
