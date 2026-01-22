#!/usr/bin/env python
"""Database initialization script.

This script initializes the database schema by creating all tables
defined in the models.

Usage:
    python scripts/init_db.py [--drop] [--sample-data] [--mock-agents]

Options:
    --drop          Drop existing tables before creating new ones.
    --sample-data   Create sample data after initializing tables.
    --mock-agents   Load mock agent profiles (100 agents).
"""

from __future__ import annotations

import argparse
import asyncio
import os
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


async def load_mock_agents(count: int = 100, seed: int = 42) -> None:
    """Load mock agent profiles into database.

    Args:
        count: Number of mock agents to generate.
        seed: Random seed for reproducibility.
    """
    from scripts.generate_mock_agents import generate_mock_agents, convert_to_db_format

    print(f"\nLoading {count} mock agent profiles...")

    # Generate mock agents
    agents = generate_mock_agents(count=count, seed=seed)
    db_agents = convert_to_db_format(agents)

    db = Database(db_settings.url)

    try:
        async with db.session() as session:
            loaded = 0
            for agent_data in db_agents:
                agent = AgentProfile(
                    id=agent_data["id"],
                    name=agent_data["name"],
                    agent_type=agent_data["agent_type"],
                    description=agent_data.get("description"),
                    capabilities=agent_data.get("capabilities", {}),
                    pricing_info=agent_data.get("pricing_info", {}),
                    config=agent_data.get("config", {}),
                    is_active=agent_data.get("is_active", True),
                    rating=agent_data.get("rating"),
                    total_collaborations=agent_data.get("total_collaborations", 0),
                )
                session.add(agent)
                loaded += 1

                # Progress indicator
                if loaded % 20 == 0:
                    print(f"  Loaded {loaded}/{count} agents...")

        print(f"Successfully loaded {loaded} mock agent profiles!")

    except Exception as e:
        print(f"Error loading mock agents: {e}")
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
    parser.add_argument(
        "--mock-agents",
        action="store_true",
        help="Load 100 mock agent profiles.",
    )
    parser.add_argument(
        "--mock-agents-count",
        type=int,
        default=100,
        help="Number of mock agents to generate (default: 100).",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("ToWow Database Initialization")
    print("=" * 50)
    print(f"Database URL: {db_settings.url}")

    asyncio.run(init_database(drop_existing=args.drop))

    if args.sample_data:
        asyncio.run(create_sample_data())

    if args.mock_agents:
        asyncio.run(load_mock_agents(count=args.mock_agents_count))

    print("\n" + "=" * 50)
    print("Database initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
