# ToWow - AI Agent Collaboration Network

ToWow is an AI-powered agent collaboration platform built on OpenAgents.

## Project Structure

```
towow/
├── openagents/          # OpenAgent related code
│   ├── agents/          # Agent implementations
│   └── config.py        # OpenAgent configuration
├── api/                 # FastAPI backend
│   ├── main.py          # Application entry point
│   ├── routers/         # API routes
│   └── services/        # Business logic
├── database/            # Database layer
│   ├── models.py        # SQLAlchemy models
│   ├── connection.py    # Database connection
│   └── migrations/      # Alembic migrations
├── prompts/             # Prompt templates storage
├── tests/               # Test suite
└── scripts/             # Utility scripts
```

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- OpenAgents runtime

### Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# For development:
pip install -r requirements-dev.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the server:
```bash
uvicorn api.main:app --reload
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
ruff check .
mypy .
```

## License

MIT
