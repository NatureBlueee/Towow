#!/usr/bin/env python
"""Database initialization script.

This script initializes the database schema by creating all tables
defined in the models.

Usage:
    python scripts/init_db.py [--drop]

Options:
    --drop  Drop existing tables before creating new ones.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.connection import Database, db_settings, Base
from database.models import (  # noqa: F401 - needed for table registration
    AgentProfile,
    Demand,
    CollaborationChannel,
    AgentResponse,
)


async def init_database(drop_existing: bool = False) -> None:
    """Initialize the database.

    Args:
        drop_existing: If True, drop existing tables before creating.
    """
    print(f"Connecting to database: {db_settings.url}")

    db = Database(db_settings.url)

    try:
        if drop_existing:
            print("Dropping existing tables...")
            await db.drop_tables()
            print("Tables dropped successfully.")

        print("Creating tables...")
        await db.create_tables()
        print("Tables created successfully!")

        # List all tables
        print("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    finally:
        await db.close()


async def create_sample_data() -> None:
    """Create sample data for development/testing."""
    from database.services import AgentProfileService, DemandService

    print("\nCreating sample data...")

    db = Database(db_settings.url)

    try:
        async with db.session() as session:
            # Create sample agent profiles
            agent_service = AgentProfileService(session)

            # Translation Agent
            await agent_service.create(
                name="Translation Expert",
                agent_type="translator",
                description="Professional translation agent supporting 50+ languages",
                capabilities={
                    "languages": ["en", "zh", "ja", "ko", "es", "fr", "de"],
                    "specializations": ["technical", "legal", "medical"],
                },
                pricing_info={
                    "base_rate": 0.05,
                    "currency": "USD",
                    "unit": "word",
                },
            )
            print("  Created: Translation Expert")

            # Code Review Agent
            await agent_service.create(
                name="Code Reviewer",
                agent_type="developer",
                description="Expert code review agent for multiple programming languages",
                capabilities={
                    "languages": ["python", "javascript", "typescript", "go", "rust"],
                    "frameworks": ["fastapi", "react", "nextjs"],
                },
                pricing_info={
                    "base_rate": 10.0,
                    "currency": "USD",
                    "unit": "review",
                },
            )
            print("  Created: Code Reviewer")

            # Create sample demand
            demand_service = DemandService(session)
            await demand_service.create(
                title="Translate Technical Documentation",
                description="Need to translate API documentation from English to Chinese",
                user_id="sample-user-001",
                requirements={
                    "source_language": "en",
                    "target_language": "zh",
                    "word_count": 5000,
                    "domain": "technical",
                },
                budget={
                    "max_amount": 500,
                    "currency": "USD",
                },
                tags=["translation", "technical", "documentation"],
            )
            print("  Created: Sample demand")

        print("Sample data created successfully!")

    except Exception as e:
        print(f"Error creating sample data: {e}")
        raise
    finally:
        await db.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize the ToWow database."
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating new ones.",
    )
    parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Create sample data after initializing tables.",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("ToWow Database Initialization")
    print("=" * 50)

    asyncio.run(init_database(drop_existing=args.drop))

    if args.sample_data:
        asyncio.run(create_sample_data())

    print("\n" + "=" * 50)
    print("Database initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
