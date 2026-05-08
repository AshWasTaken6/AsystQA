# AsystQA Documentation

## Overview

AsystQA is a multi-agent AI-powered software quality assurance platform designed to automate code review, testing recommendations, security analysis, and comprehensive reporting. The system leverages specialized AI agents working in concert to provide thorough analysis of source code across multiple programming languages.

## Architecture

### Backend Architecture

The backend is built using FastAPI and follows a modular architecture with the following components:

#### Core Components
- **FastAPI Application** (`main.py`): Main application entry point with CORS configuration
- **Configuration Management** (`core/config.py`): Environment-based settings for app configuration
- **Logging System** (`utils/logger.py`): Structured logging with configurable levels
- **API Layer** (`api/routes.py`): REST API endpoints for client interaction

#### Agent System
The platform employs five specialized agents that work together in a pipeline:

1. **Planner Agent** (`agents/planner.py`)
   - Analyzes code structure and complexity
   - Creates execution plans based on language and code metrics
   - Identifies main execution paths and dependencies

2. **Reviewer Agent** (`agents/reviewer.py`)
   - Performs code quality analysis
   - Checks for maintainability issues (line length, TODO markers)
   - Identifies language-specific anti-patterns

3. **Security Agent** (`agents/security.py`)
   - Scans for security vulnerabilities
   - Detects unsafe code patterns (eval, exec, hardcoded secrets)
   - Identifies potential XSS and injection risks

4. **Tester Agent** (`agents/tester.py`)
   - Generates test recommendations
   - Suggests test coverage improvements
   - Provides language-specific testing strategies

5. **Reporter Agent** (`agents/reporter.py`)
   - Aggregates findings from all agents
   - Calculates overall quality score (0-100)
   - Generates comprehensive summary reports

#### Pipeline Flow
```
Input (code + language) → Planner → Parallel Analysis (Reviewer/Security/Tester) → Reporter → Output
```

### Data Models

#### Request Schema (`schemas/request.py`)
```python
class AnalyzeRequest(BaseModel):
    code: str  # Source code to analyze (required, min_length=1)
    language: str  # Programming language (required, min_length=1)
```

#### Response Schema (`schemas/response.py`)
```python
class Report(BaseModel):
    score: int  # Quality score (0-100)
    summary: str  # Consolidated findings summary

class AnalyzeResponse(BaseModel):
    planner: List[str]      # Planning steps
    reviewer: List[str]     # Code quality findings
    security: List[str]     # Security issues
    tester: List[str]       # Test recommendations
    reporter: Report        # Final report
```

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AsystQA
   ```

2. **Create virtual environment**
   ```bash
   cd backend
   python -m venv .venv
   ```

3. **Activate virtual environment**
   ```bash
   # Windows
   .\.venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Start the development server**
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`

## API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### POST /analyze
Analyzes source code using the multi-agent pipeline.

**Request Body:**
```json
{
  "code": "def hello():\n    print('Hello, World!')",
  "language": "python"
}
```

**Response:**
```json
{
  "planner": [
    "Analyze the submitted python code for quality, safety, and test coverage.",
    "Inspect 2 non-empty lines to identify the main execution path and dependencies.",
    "Prepare consolidated findings for reviewer, security, and tester agents.",
    "Check imports, function boundaries, and exception handling patterns."
  ],
  "reviewer": [
    "Consider replacing ad-hoc print statements with structured logging."
  ],
  "security": [
    "No obvious high-risk patterns were detected by the security stub."
  ],
  "tester": [
    "Add a happy-path test that validates the expected primary behavior.",
    "Add at least one failure-path test for invalid or empty input.",
    "Use pytest parametrization to cover multiple input variants quickly."
  ],
  "reporter": {
    "score": 95,
    "summary": "Planner produced 4 steps. Reviewer found 1 item(s). Security found 1 item(s). Tester suggested 3 test improvement(s)."
  }
}
```

**Supported Languages:**
- Python
- JavaScript
- TypeScript
- Other languages (generic analysis)

## Agent Details

### Planner Agent
**Purpose:** Creates a structured analysis plan based on code characteristics.

**Logic:**
- Counts non-empty lines
- Identifies language-specific patterns
- Generates step-by-step analysis roadmap

### Reviewer Agent
**Purpose:** Identifies code quality and maintainability issues.

**Checks:**
- Line length (>100 characters)
- TODO/FIXME markers
- Debug statements (print/console.log)
- Language-specific anti-patterns

### Security Agent
**Purpose:** Scans for security vulnerabilities and unsafe patterns.

**Checks:**
- Dynamic code execution (eval, exec)
- Hardcoded sensitive data
- XSS vulnerabilities (innerHTML)
- Unsafe code patterns

### Tester Agent
**Purpose:** Provides testing recommendations and coverage suggestions.

**Suggestions:**
- Happy path and failure path tests
- Language-specific testing frameworks
- Edge case coverage
- Integration testing recommendations

### Reporter Agent
**Purpose:** Consolidates all findings into a final report.

**Scoring Logic:**
- Base score: 100
- Deductions: 5 points per finding
- Minimum score: 0

## Configuration

### Environment Variables
- `APP_NAME`: Application name (default: "AsystQA Backend")
- `API_PREFIX`: API route prefix (default: "")
- `ALLOWED_ORIGINS`: CORS allowed origins (default: "http://localhost:5173")

### Logging
- Configurable log levels
- Structured format: `timestamp | level | module | message`
- Default level: INFO

## Development

### Project Structure
```
AsystQA/
└── backend/
    ├── main.py              # FastAPI application
    ├── requirements.txt     # Python dependencies
    ├── agents/              # AI agent implementations
    ├── api/                 # API routes
    ├── core/                # Core functionality
    ├── schemas/             # Pydantic models
    └── utils/               # Utilities
```

### Adding New Agents
1. Create agent file in `agents/` directory
2. Implement agent function with signature: `def run_agent(code: str, language: str) -> List[str]`
3. Add agent to pipeline in `core/pipeline.py`
4. Update response schema in `schemas/response.py`

### Extending Language Support
1. Add language detection logic in agents
2. Implement language-specific checks
3. Update documentation

## Testing

### Running Tests
```bash
# Install test dependencies
pip install pytest

# Run tests
pytest
```

### API Testing
Use tools like Postman, curl, or the FastAPI interactive documentation at `/docs`

## Deployment

### Production Deployment
1. Set environment variables for production
2. Use production ASGI server (e.g., gunicorn + uvicorn workers)
3. Configure reverse proxy (nginx)
4. Set up monitoring and logging

### Docker Deployment (Future)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Contributing

### Code Style
- Follow PEP 8 for Python code
- Use type hints
- Add docstrings for functions
- Keep functions focused and testable

### Pull Request Process
1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Update documentation
6. Submit pull request

## License

MIT License - Copyright (c) 2026 Ashath Shaikh

## Future Enhancements

- Advanced AI models for deeper analysis
- Integration with CI/CD pipelines
- Support for additional programming languages
- Custom rule configuration
- Historical analysis tracking
- Team collaboration features