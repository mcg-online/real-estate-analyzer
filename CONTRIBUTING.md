# Contributing to Real Estate Analyzer

Thank you for your interest in contributing to Real Estate Analyzer! This guide will help you set up your development environment, understand our contribution process, and maintain code quality standards.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Development Workflow](#development-workflow)
- [Code Style & Quality](#code-style--quality)
- [Testing Requirements](#testing-requirements)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Commit Message Format](#commit-message-format)
- [Getting Help](#getting-help)

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9+** (backend)
- **Node.js 18+** (frontend; v24 compatible with NODE_OPTIONS flag)
- **MongoDB 6+** (local development)
- **Redis 7+** (optional for testing caching/rate limiting)
- **Git** for version control

## Local Development Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/real-estate-analyzer.git
cd real-estate-analyzer
```

### Step 2: Backend Setup

```bash
cd backend

# Create and activate Python virtual environment
python3.9 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify setup
python -c "from app import app; print('OK')"
```

### Step 3: Frontend Setup

```bash
cd frontend

# Install dependencies with legacy peer deps flag
npm install --legacy-peer-deps

# Verify Node.js compatibility (for Node v24)
# If using Node v24, set NODE_OPTIONS when building:
export NODE_OPTIONS=--openssl-legacy-provider
```

### Step 4: Environment Configuration

Create a `.env` file in the `backend/` directory:

```bash
cd backend
touch .env
```

Add the following (adjust as needed for your environment):

```env
# Database
DATABASE_URL=mongodb://localhost:27017/realestate

# JWT
JWT_SECRET=your_secret_key_at_least_32_chars_long
JWT_EXPIRY_SECONDS=3600

# CORS (for local development)
CORS_ORIGINS=http://localhost:3000

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Flask
FLASK_ENV=development
FLASK_DEBUG=true
```

### Step 5: Start Services (Optional)

If you prefer using Docker Compose:

```bash
docker-compose up -d
```

This starts:
- MongoDB on `localhost:27017`
- Redis on `localhost:6379`
- Flask backend on `localhost:5000`
- React frontend on `localhost:3000`

If running locally without Docker:

```bash
# Terminal 1 - MongoDB
mongod --dbpath ./data

# Terminal 2 - Backend
cd backend
source venv/bin/activate
python -m flask run

# Terminal 3 - Frontend
cd frontend
npm start
```

## Development Workflow

### 1. Create a Feature Branch

Use descriptive branch names following this pattern:

```bash
git checkout -b feature/short-description
git checkout -b bugfix/issue-number-short-description
git checkout -b docs/what-you-documented
```

Examples:
- `feature/property-comparison-tool`
- `bugfix/jwt-expiration-handling`
- `docs/deployment-guide`

### 2. Make Your Changes

- Keep changes focused and atomic
- Update related tests as you go
- Follow the code style guidelines (see below)
- Commit frequently with clear messages

### 3. Write or Update Tests

Every feature and bug fix must include tests:

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

For new features:
- Add unit tests in `tests/test_*.py` files
- Ensure all existing tests still pass
- Aim for high code coverage in your changes

### 4. Run Code Quality Checks

```bash
cd backend
source venv/bin/activate

# Check code style with ruff
ruff check .

# Run full test suite
pytest tests/ -v
```

### 5. Commit and Push

```bash
git add .
git commit -m "type(scope): description"
git push origin feature/your-branch-name
```

See [Commit Message Format](#commit-message-format) below for details.

## Code Style & Quality

### Python (Backend)

We use **Ruff** for code quality checks:

```bash
cd backend
source venv/bin/activate
ruff check .
ruff format .  # Auto-format code
```

Style guidelines:
- Follow PEP 8 conventions
- Use meaningful variable and function names
- Keep functions small and focused (< 50 lines)
- Add docstrings to public functions
- Use type hints where applicable

Example:

```python
def calculate_roi(
    initial_investment: float,
    annual_profit: float,
    years: int
) -> float:
    """
    Calculate return on investment percentage.

    Args:
        initial_investment: Starting capital in dollars
        annual_profit: Average yearly profit in dollars
        years: Investment holding period in years

    Returns:
        ROI percentage (0-100)
    """
    if initial_investment <= 0:
        return 0.0
    return ((annual_profit * years) / initial_investment) * 100
```

### JavaScript/React (Frontend)

We use **ESLint** via react-scripts:

```bash
cd frontend
npm run lint
```

Style guidelines:
- Use functional components with hooks
- Follow React best practices (see [React docs](https://react.dev))
- Use meaningful component and variable names
- Keep components focused and reusable
- Add JSDoc comments for complex logic

Example:

```javascript
/**
 * PropertyCard displays a single property with key metrics.
 *
 * @param {Object} property - The property data object
 * @param {string} property.id - Property ID
 * @param {string} property.address - Full address
 * @param {number} property.price - List price
 * @returns {JSX.Element} Rendered property card
 */
export function PropertyCard({ property }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="property-card">
      <h3>{property.address}</h3>
      {/* Card content */}
    </div>
  );
}
```

## Testing Requirements

### Backend Tests

The backend test suite includes 687 tests covering:
- Model operations (create, read, update, delete)
- API endpoints and route handlers
- Authentication and authorization
- Financial calculations
- Market analysis aggregations
- Error handling and validation

Run tests:

```bash
cd backend
source venv/bin/activate

# Run all tests with verbose output
pytest tests/ -v

# Run tests for a specific module
pytest tests/test_routes.py -v

# Run with coverage report
pytest tests/ --cov=routes --cov=services --cov=models
```

### Guidelines for New Tests

1. **Test file naming**: Use `test_*.py` pattern
2. **Test function naming**: Use `test_*` prefix
3. **Mocking**: Mock external dependencies (database, Redis, HTTP calls)
4. **Assertions**: Use `pytest.approx()` for floating-point comparisons

Example test:

```python
def test_calculate_cap_rate():
    """Test cap rate calculation with valid inputs."""
    cap_rate = calculate_cap_rate(
        annual_noi=50000,
        purchase_price=500000
    )
    assert cap_rate == pytest.approx(0.10, abs=0.01)  # 10%


def test_calculate_cap_rate_zero_price():
    """Test cap rate guards against zero purchase price."""
    cap_rate = calculate_cap_rate(
        annual_noi=50000,
        purchase_price=0
    )
    assert cap_rate == 0.0
```

### Frontend Tests

Frontend testing setup is available (React Testing Library installed) but not yet extensively implemented. Contributions to frontend test coverage are welcome!

## Pull Request Guidelines

### Before Submitting

1. **Ensure all tests pass**:
   ```bash
   cd backend && pytest tests/ -v
   ```

2. **Check code style**:
   ```bash
   cd backend && ruff check .
   ```

3. **Update documentation** if your changes affect:
   - API behavior (update `API.md`)
   - Architecture (update `ARCHITECTURE.md`)
   - Deployment (update `DEPLOYMENT.md`)
   - Configuration (update this guide or `README.md`)

4. **Update CHANGELOG.md** with your changes (see [versioning](CHANGELOG.md))

### PR Title Format

Use the same format as commit messages:

```
type(scope): description

Examples:
- feat(properties): add property comparison feature
- fix(auth): resolve JWT token expiration bug
- docs(deployment): update Docker configuration
```

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## Changes Made
- Item 1
- Item 2
- Item 3

## Testing Done
- [ ] All existing tests pass (`pytest tests/ -v`)
- [ ] Added new tests for this change
- [ ] Manual testing completed (describe below)

## Manual Testing
Description of how you tested this change locally.

## Screenshots (if applicable)
Add screenshots for UI changes.

## Related Issues
Closes #issue-number

## Checklist
- [ ] Code follows style guidelines (ruff for Python, ESLint for JS)
- [ ] Documentation updated (README, API.md, DEPLOYMENT.md, etc.)
- [ ] Tests added/updated
- [ ] CHANGELOG.md updated
- [ ] No breaking changes (or documented if breaking)
```

## Commit Message Format

We follow the Conventional Commits specification for consistent commit history and automated changelog generation.

### Format

```
type(scope): description

[optional body]

[optional footer]
```

### Type

Must be one of:

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation changes
- **test**: Test additions or modifications
- **refactor**: Code refactoring without feature/fix changes
- **perf**: Performance improvements
- **ci**: CI/CD configuration changes
- **chore**: Maintenance tasks, dependency updates

### Scope

The area of the codebase affected (optional but recommended):

- `auth`: Authentication/authorization
- `properties`: Property routes/models
- `analysis`: Analysis services and routes
- `market`: Market aggregation
- `scheduler`: Background jobs
- `frontend`: React components/pages
- `docker`: Docker/deployment
- `tests`: Test suite
- `docs`: Documentation

### Description

- Use imperative mood ("add feature" not "added feature")
- Don't capitalize first letter
- No period at the end
- Keep it concise (50 chars or less)

### Body (Optional)

Explain the motivation for the change and contrast with previous behavior:

```
add property ownership validation

Properties are now associated with the user who created them.
PUT and DELETE operations enforce ownership, returning 403 Forbidden
if the authenticated user is not the property owner.

Legacy properties without user_id remain readable to all authenticated users.
```

### Footer (Optional)

Reference issues and breaking changes:

```
Closes #123
Breaking-change: The /api/old-endpoint has been removed
```

### Examples

```
feat(properties): add property comparison feature

Users can now select multiple properties and view a side-by-side
comparison of key financial metrics and risk factors.

Closes #45
```

```
fix(auth): reset JWT token expiration on login

Previously, JWT tokens maintained the same expiration regardless
of login frequency. Now tokens are refreshed with each login.

Fixes #78
```

```
docs(deployment): update Docker environment variables

Added missing REDIS_URL and JWT_EXPIRY_SECONDS to deployment docs.
```

## Getting Help

- **Issues & Questions**: Use GitHub Issues for bugs, features, or questions
- **Discussions**: GitHub Discussions for broader conversations
- **Security**: See [SECURITY.md](SECURITY.md) for vulnerability reporting
- **Documentation**: Check [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [API.md](API.md)

## Code of Conduct

By participating in this project, you agree to be respectful and constructive in all interactions. We welcome contributors from all backgrounds and experience levels.

## Additional Resources

- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](API.md)
- [Security Policy](SECURITY.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Architecture Decision Records](docs/adr/)

Happy coding!
