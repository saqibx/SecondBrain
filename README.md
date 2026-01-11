# SecondBrain

An AI-powered personal research and email drafting assistant with a self-improving knowledge base. SecondBrain combines web research, RAG (Retrieval-Augmented Generation), and intelligent email composition to help you research companies and draft professional outreach.

## Features

- **Intelligent Research**: Powered by Tavily API for real-time web research
- **Personal Knowledge Base**: ChromaDB vector store for retrieving your stored documents and insights
- **Email Generation**: Draft professional emails based on research and knowledge
- **File Saving**: Automatically save research and drafts to your personal directory
- **RAG System**: Context-aware question answering over your knowledge base
- **Multi-user Support**: Each user has their own isolated knowledge base and session
- **Production Ready**: Rate limiting, security hardening, comprehensive logging, and health checks

## Tech Stack

- **Backend**: Flask with Python 3.11
- **Vector Store**: ChromaDB for embeddings and semantic search
- **LLM Integration**: OpenAI API (GPT-4o-mini) for AI capabilities
- **Search**: Tavily API for web research
- **Database**: MongoDB for user data and persistence
- **Session Store**: Redis for session management and caching
- **Agent Framework**: LangGraph for agentic orchestration
- **Container**: Docker and Docker Compose for deployment

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- MongoDB 6.0+ or access to MongoDB Atlas
- Redis 6.0+
- API Keys:
  - OpenAI API key (https://platform.openai.com/api-keys)
  - Tavily API key (https://tavily.com)

## Quick Start

### Local Development (with Docker Compose)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SecondBrain
   ```

2. **Copy and configure environment**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `TAVILY_API_KEY`: Your Tavily API key
   - `APP_SECRET_KEY`: A strong random key for sessions
   - `MONGO_PASSWORD`: Password for MongoDB admin

3. **Start services with Docker Compose**
   ```bash
   docker-compose up --build
   ```
   
   This will start:
   - MongoDB on port 27017
   - Redis on port 6379
   - SecondBrain API on port 5895

4. **Access the API**
   - API Documentation: http://localhost:5895/api/v1
   - Health Check: http://localhost:5895/health

### Local Development (without Docker)

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up MongoDB and Redis**
   ```bash
   # Using Homebrew on macOS
   brew install mongodb-community redis
   brew services start mongodb-community
   brew services start redis
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

## API Endpoints

### Authentication

- `POST /api/v1/login` - Login with credentials
- `POST /api/v1/register` - Create new account
- `POST /api/v1/logout` - Logout current user
- `GET /api/v1/auth/status` - Check authentication status

### Agent

- `POST /api/v1/chat` - Send message to AI agent
- `GET /api/v1/state` - Get current agent state
- `POST /api/v1/clear` - Clear agent session

### Monitoring

- `GET /health` - Health check endpoint
- `GET /api/v1` - API documentation

## Usage Example

```bash
# Register
curl -X POST http://localhost:5895/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"username":"saqib","password":"mypassword123"}'

# Login
curl -X POST http://localhost:5895/api/v1/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"username":"saqib","password":"mypassword123"}'

# Research a company
curl -X POST http://localhost:5895/api/v1/chat \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"message":"Research TechCrunch and draft an email to their CEO"}'
```

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for all):

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | development | Environment (development, staging, production) |
| `MONGO_URI` | mongodb://localhost:27017 | MongoDB connection string |
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection URL |
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `TAVILY_API_KEY` | Required | Tavily API key |
| `ALLOWED_ORIGINS` | http://localhost:8080 | Comma-separated CORS origins |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `RATELIMIT_ENABLED` | true | Enable API rate limiting |

### Configuration Files

- `config.py` - Flask configuration (environment-specific)
- `logging_config.py` - Structured logging setup
- `.env.example` - Example environment variables
- `Dockerfile` - Container configuration
- `docker-compose.yml` - Local development environment

## Project Structure

```
SecondBrain/
├── app.py                      # Main Flask application
├── config.py                   # Configuration management
├── utils.py                    # Utility functions (CORS, error handling)
├── logging_config.py           # Logging configuration
├── Helper.py                   # Helper functions for document processing
├── TRAG.py                     # RAG (Retrieval-Augmented Generation) system
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment variables
├── .gitignore                  # Git ignore rules
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Docker Compose setup
├── Classes/
│   ├── Users.py               # User model and authentication
│   ├── ChromaDBHandler.py     # Vector store operations
│   └── chroma_db/             # ChromaDB vector store (persisted)
├── Agents/
│   ├── AgentMain.py           # Agentic workflow orchestration
│   └── utils.py               # Agent utilities (tools, research, email)
├── DATA/                       # User data and saved documents
├── logs/                       # Application logs
└── DEPLOYMENT_ANALYSIS.md      # Deployment analysis document
```

## Security Considerations

### Implemented

- ✅ Password hashing with bcrypt (12 rounds)
- ✅ Session-based authentication with Flask-Session
- ✅ JWT token generation for future API expansion
- ✅ Rate limiting on auth endpoints (login: 5/min, register: 3/hour)
- ✅ CORS with configurable allowed origins
- ✅ Input validation and sanitization
- ✅ Structured logging for audit trails
- ✅ MongoDB index on username (unique constraint)
- ✅ Environment-based configuration (no secrets in code)
- ✅ Health checks for dependency monitoring

### Best Practices for Deployment

1. **Use strong `APP_SECRET_KEY`**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Configure HTTPS/TLS**
   - Use a reverse proxy (nginx, HAProxy)
   - Set `ALLOWED_ORIGINS` to your domain

3. **Database Security**
   - Use MongoDB Atlas or secured instance
   - Enable authentication and SSL/TLS
   - Regular backups

4. **API Keys**
   - Use environment variables or secrets manager
   - Rotate keys regularly
   - Monitor API usage

5. **Monitoring and Logging**
   - Collect logs to centralized service (ELK, Datadog)
   - Set up alerts for errors
   - Monitor API rate limits and usage

## Logging

The application uses structured logging with rotation:

- **Console**: All logs printed to stdout
- **File**: `logs/app.log` (rotated when > 10MB)
- **Error File**: `logs/error.log` for errors only

Configure with `LOG_LEVEL` environment variable:
- `DEBUG` - Development and troubleshooting
- `INFO` - General information
- `WARNING` - Important warnings
- `ERROR` - Error conditions only

## Rate Limiting

Built-in rate limiting on sensitive endpoints:

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| `/api/v1/login` | 5/minute | Prevent brute force |
| `/api/v1/register` | 3/hour | Prevent spam |
| `/api/v1/chat` | 30/minute | Prevent DoS |
| General | 100/hour | Default rate limit |

Disable for development by setting `RATELIMIT_ENABLED=false`.

## Deployment

### Docker Deployment

1. **Build image**
   ```bash
   docker build -t secondbrain:latest .
   ```

2. **Run container**
   ```bash
   docker run -p 5895:5895 \
     -e OPENAI_API_KEY=sk-... \
     -e TAVILY_API_KEY=tvly-... \
     -e MONGO_URI=mongodb://... \
     -e REDIS_URL=redis://... \
     secondbrain:latest
   ```

### Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions including:
- Kubernetes deployment
- Environment configuration
- Monitoring and scaling
- Backup and recovery

## Testing

Run tests with pytest:

```bash
pytest tests/ -v --cov=. --cov-report=html
```

## Troubleshooting

### MongoDB Connection Error
```
Error: Failed to connect to MongoDB
```
- Check `MONGO_URI` is correct
- Verify MongoDB is running: `mongosh` should connect
- Check username/password if using authentication

### Redis Connection Error
```
Error: Failed to connect to Redis
```
- Check `REDIS_URL` is correct
- Verify Redis is running: `redis-cli ping` should return PONG
- If disabled, set `SESSION_TYPE=filesystem`

### API Key Errors
```
Error: Missing required environment variables
```
- Copy `.env.example` to `.env`
- Add your API keys: `OPENAI_API_KEY` and `TAVILY_API_KEY`
- Restart the application

### Rate Limit Issues
- Disable rate limiting for local development: `RATELIMIT_ENABLED=false`
- Adjust limits in `.env` if needed
- Check Redis connection if using distributed rate limiting

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review logs in `logs/` directory
3. Check health endpoint: `GET /health`
4. Open an issue on GitHub

---

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Status**: Production Ready ✅
