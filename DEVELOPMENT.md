# Development Guide

## Setup for Development

### Prerequisites
- Python 3.9+
- Git
- Telegram account with bot token from @BotFather

### Local Development Setup

1. Clone the repository:
```bash
git clone <repository_url>
cd bms
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create environment file:
```bash
cp .env.example .env
# Edit .env with your bot token and database settings
```

5. Initialize database:
```bash
python -c "from bot.models.database import init_db; init_db()"
```

6. Run the bot:
```bash
python bot/main.py
```

## Project Structure

```
bms/
├── bot/                       # Main bot package
│   ├── __init__.py
│   ├── main.py               # Entry point with bot initialization
│   ├── handlers/             # Telegram message and callback handlers
│   │   ├── __init__.py
│   │   ├── message_handler.py
│   │   └── callback_handler.py
│   ├── services/             # Business logic layer
│   │   ├── __init__.py
│   │   ├── parser.py         # Text parsing logic
│   │   ├── checklist_manager.py
│   │   ├── business_connection_service.py
│   │   └── user_whitelist_service.py
│   ├── models/               # Database models
│   │   ├── __init__.py
│   │   └── database.py
│   └── utils/                # Utilities and configuration
│       ├── __init__.py
│       └── config.py
├── .env                      # Environment variables (not committed)
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── README.md                 # User documentation
├── CLAUDE.md                 # Project insights and best practices
├── DEVELOPMENT.md            # This file
└── venv/                     # Virtual environment (not committed)
```

## Code Style and Standards

### Python Style Guide
- Follow PEP 8 style guidelines
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use type hints where appropriate (all service layer methods have type hints)

### aiogram Best Practices
- Use routers for modular handler organization (`bot/handlers/`)
- Implement middleware for cross-cutting concerns (`DebugMiddleware`)
- Use filter-based routing (`F.text.startswith()`, `F.text`)
- Separate business message handlers from regular message handlers
- Use `@router.business_connection()` for business connection events
- Use `@router.business_message()` for business messages

### Naming Conventions
- Classes: PascalCase (e.g., `TextParser`)
- Functions and variables: snake_case (e.g., `parse_text`)
- Private members: prefix with underscore (e.g., `_internal_method`)
- Constants: UPPER_SNAKE_CASE (e.g., `BOT_TOKEN`)

### Documentation Standards
- All public functions and classes must have docstrings
- Use Google-style docstrings
- Include type hints in function signatures
- Document complex algorithms in comments

## Testing Guidelines

### Current Testing Status
- **Status**: No automated tests implemented yet
- **Testing Method**: Manual testing through Telegram interface
- **Visibility**: Debug logging provides runtime visibility

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run all tests
pytest

# Run with coverage
pytest --cov=bot --cov-report=html
```

### Recommended Test Structure
```python
# tests/test_parser.py - TextParser class tests
class TestTextParser:
    def test_parse_comma_separated(self):
        """Test comma-separated format"""
        result = TextParser.parse_text("Milk, Bread, Cheese")
        assert result == ["Milk", "Bread", "Cheese"]

    def test_parse_numbered_list(self):
        """Test numbered list format"""
        text = "1. Buy milk\n2. Buy bread"
        result = TextParser.parse_text(text)
        assert result == ["Buy milk", "Buy bread"]

    def test_parse_bulleted_list(self):
        """Test bulleted list format"""
        text = "• Milk\n• Bread\n• Cheese"
        result = TextParser.parse_text(text)
        assert result == ["Milk", "Bread", "Cheese"]

    def test_parse_pipe_separator(self):
        """Test pipe-separated format"""
        result = TextParser.parse_text("Buy milk | Buy bread")
        assert result == ["Buy milk", "Buy bread"]

    def test_parse_russian_and(self):
        """Test Russian 'и' separator"""
        result = TextParser.parse_text("Купить молоко и хлеб")
        assert result == ["Купить молоко", "Купить хлеб"]

    def test_parse_with_brackets(self):
        """Test comma inside brackets is preserved"""
        result = TextParser.parse_text("Buy (milk, bread), cheese")
        assert "Buy (milk, bread)" in result
        assert "cheese" in result

# tests/test_services.py - Service layer tests
class TestUserWhitelistService:
    def test_add_user_username(self):
        """Test adding user by username"""
        service = UserWhitelistService()
        success, msg = service.add_user("@testuser", 12345)
        assert success is True

    def test_is_user_allowed(self):
        """Test whitelist checking"""
        service = UserWhitelistService()
        # Add user then check
        service.add_user("@testuser", 12345)
        assert service.is_user_allowed("testuser") is True

class TestBusinessConnectionService:
    def test_save_connection(self):
        """Test saving business connection"""
        service = BusinessConnectionService()
        connection = service.save_connection("conn_123", 12345)
        assert connection.is_active is True

# tests/test_models.py - Database model tests
class TestChecklistModel:
    def test_create_checklist(self):
        """Test checklist creation"""
        checklist = Checklist(user_id=123, title="Test List")
        assert checklist.title == "Test List"

# tests/conftest.py - Test configuration
import pytest
from bot.models.database import Base, engine

@pytest.fixture(scope="session")
def db_engine():
    """Database engine for tests"""
    return engine

@pytest.fixture
def db_session(db_engine):
    """Database session for tests"""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
```

### Test Coverage Recommendations
- **test_parser.py**: All separator formats, edge cases (empty input, single item, special characters)
- **test_services.py**: Whitelist operations, business connection lifecycle, checklist CRUD
- **test_handlers.py**: Command handlers, business message flow, reaction handling
- **test_models.py**: Database schema, relationships, query performance

## Database Operations

### Adding New Models
1. Define model in `bot/models/database.py`
2. Import and add to Base.metadata in `init_db()`
3. Create migration if using Alembic

### Database Sessions
Always use the context manager for database sessions:
```python
from bot.models.database import get_db

def create_checklist(data):
    db = next(get_db())
    try:
        # Database operations
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

## Debugging

### Debug Mode
The bot includes debug middleware that logs all incoming updates. To add more debugging:

```python
# Add custom logging
logger = logging.getLogger(__name__)
logger.debug("Debug information: %s", variable)
```

## Service Layer Architecture

### Available Services
- `TextParser` - Parses various text formats into task lists
- `ChecklistManager` - CRUD operations for checklists and tasks
- `BusinessConnectionService` - Manages business connection state
- `UserWhitelistService` - Manages allowed users for business accounts

### Service Usage Pattern
```python
# Services manage their own database sessions
service = BusinessConnectionService()
connection_id = service.get_active_connection()

# Services return structured data
info = service.get_connection_info()  # Returns dict or None
```

## Debugging

### Debug Mode
The bot includes debug middleware that logs all incoming updates. To add more debugging:

```python
# Add custom logging
logger = logging.getLogger(__name__)
logger.debug("Debug information: %s", variable)
```

### Common Debugging Scenarios

1. **Bot not receiving messages**:
   - Check bot token is correct
   - Verify bot is running
   - Check Telegram Bot API status

2. **Business connection not working**:
   - Verify bot is connected to business account
   - Check `/business` command response
   - Review business connection in database
   - Ensure user is in whitelist

3. **Checklist not being created**:
   - Verify message has at least 2 tasks
   - Check if user is in whitelist
   - Review debug logs for parser output
   - Verify business connection is active

4. **Database issues**:
   - Verify DATABASE_URL in .env
   - Check database file permissions
   - Review SQLAlchemy logs

5. **Parser not working**:
   - Test parser in isolation
   - Check regex patterns
   - Verify input sanitization

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch:
```bash
git checkout -b feature/new-feature
```

3. Make your changes following the coding standards
4. Add tests for new functionality
5. Run tests and ensure they pass:
```bash
pytest
```

6. Commit your changes:
```bash
git commit -m "feat: add new feature description"
```

7. Push to your fork:
```bash
git push origin feature/new-feature
```

8. Create a pull request

### Commit Message Format
Use conventional commits format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for refactoring
- `test:` for adding tests
- `chore:` for maintenance tasks

Example:
```
feat: add checklist sharing functionality

- Add sharing endpoint in handlers
- Implement permission checking
- Update database schema
```

## Deployment

### Production Deployment Checklist

1. **Environment Setup**
   - [ ] Set production environment variables
   - [ ] Use production database (PostgreSQL recommended)
   - [ ] Set up SSL certificates if using webhooks

2. **Database**
   - [ ] Run database migrations
   - [ ] Set up regular backups
   - [ ] Configure connection pooling

3. **Monitoring**
   - [ ] Set up logging aggregation
   - [ ] Configure error alerts
   - [ ] Monitor bot uptime

4. **Security**
   - [ ] Review and restrict bot permissions
   - [ ] Set up rate limiting
   - [ ] Validate all inputs

### Docker Deployment

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot/main.py"]
```

Create a `docker-compose.yml`:
```yaml
version: '3.8'

services:
  bot:
    build: .
    env_file:
      - .env
    restart: unless-stopped

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: checklist_bot
      POSTGRES_USER: bot_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Performance Optimization

### Database Optimization
- Use indexes on frequently queried columns
- Implement connection pooling
- Consider read replicas for high traffic

### Bot Optimization
- Implement caching for frequent operations
- Use async/await consistently
- Limit message processing time

### Monitoring
- Track response times
- Monitor error rates
- Set up alerts for unusual activity