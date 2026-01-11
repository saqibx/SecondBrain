# SecondBrain - Quick Reference

## 🚀 Quick Start (30 seconds)

```bash
# 1. Setup
bash setup.sh

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Run locally
docker-compose up

# 4. Test
curl http://localhost:5895/health
```

## 📋 Key Files

| File | Purpose |
|------|---------|
| `app.py` | Main Flask application |
| `config.py` | Environment-specific configuration |
| `logging_config.py` | Structured logging setup |
| `utils.py` | Decorators, error handling, CORS |
| `Classes/Users.py` | User authentication & database |
| `Agents/AgentMain.py` | AI agent orchestration |
| `TRAG.py` | RAG system for knowledge base |
| `Helper.py` | Document processing & summarization |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |
| `Dockerfile` | Container configuration |
| `docker-compose.yml` | Local development setup |
| `README.md` | Full documentation |
| `DEPLOYMENT.md` | Deployment instructions |

## 🔑 Environment Variables

**Required for all environments:**
```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
APP_SECRET_KEY=<strong-random-key>
MONGO_URI=mongodb://...
MONGODB_CLIENT=secondbrain
MONGODB_COLLECTION=users
REDIS_URL=redis://...
```

**Optional (with defaults):**
```
FLASK_ENV=development        # development, staging, production
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
ALLOWED_ORIGINS=http://localhost:8080
RATELIMIT_ENABLED=true
PASSWORD_MIN_LENGTH=8
```

See `.env.example` for all options.

## 🏃 Running the App

### Docker Compose (Recommended)
```bash
docker-compose up --build
# App runs on http://localhost:5895
# MongoDB on localhost:27017
# Redis on localhost:6379
```

### Local Development
```bash
# Start services
brew services start mongodb-community
brew services start redis

# Install & run
pip install -r requirements.txt
python app.py
```

### Docker (Production)
```bash
docker build -t secondbrain .
docker run -p 5895:5895 \
  -e OPENAI_API_KEY=sk-... \
  -e TAVILY_API_KEY=tvly-... \
  secondbrain
```

## 🧪 Testing

```bash
# Unit tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html

# Integration tests
pytest tests/ -v -m "integration"
```

## 📊 API Quick Reference

### Authentication
```bash
# Register
POST /api/v1/register
{"username": "user", "password": "pass"}

# Login
POST /api/v1/login
{"username": "user", "password": "pass"}

# Status
GET /api/v1/auth/status
```

### Agent
```bash
# Chat
POST /api/v1/chat
{"message": "Research XYZ company"}

# Get state
GET /api/v1/state

# Clear session
POST /api/v1/clear
```

### Health
```bash
# Health check
GET /health

# API docs
GET /api/v1
```

## 🔍 Debugging

### Check Logs
```bash
# View logs
tail -f logs/app.log
tail -f logs/error.log

# All at once
tail -f logs/*.log
```

### Check Services
```bash
# MongoDB
mongosh

# Redis
redis-cli ping

# API
curl http://localhost:5895/health
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Port 5895 in use | `lsof -i :5895` then `kill -9 <PID>` |
| MongoDB won't connect | Check `MONGO_URI` in .env |
| Redis won't connect | Check `REDIS_URL` in .env, ensure Redis running |
| Missing API key error | Run `setup.sh` and edit .env |
| Rate limit exceeded | Disable with `RATELIMIT_ENABLED=false` (dev only) |

## 📦 Dependencies Check

```bash
# Check all requirements installed
pip check

# Update dependencies
pip install --upgrade -r requirements.txt
```

## 🐳 Docker Commands

```bash
# Build image
docker build -t secondbrain:latest .

# Run container
docker run -it -p 5895:5895 secondbrain:latest

# Check logs
docker logs -f <container-id>

# Compose up
docker-compose up --build

# Compose down
docker-compose down -v
```

## 📈 Performance Tips

1. **Enable Redis caching**: Already configured
2. **Connection pooling**: Already configured in MongoDB/Redis
3. **Rate limiting**: Adjust `RATELIMIT_*` vars in .env
4. **Logging**: Set `LOG_LEVEL=WARNING` for production
5. **Multiple instances**: Use docker-compose with replicas

## 🔐 Security Checklist

- [ ] Strong `APP_SECRET_KEY` set
- [ ] API keys in `.env` (not in code)
- [ ] `.env` file in `.gitignore`
- [ ] HTTPS/TLS enabled (production)
- [ ] `ALLOWED_ORIGINS` set correctly
- [ ] Rate limiting enabled
- [ ] Password min length set
- [ ] Backups configured

## 📚 Documentation Links

- **Full Setup**: See [README.md](README.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Changes Made**: See [PRODUCTION_READY.md](PRODUCTION_READY.md)
- **Analysis**: See [DEPLOYMENT_ANALYSIS.md](DEPLOYMENT_ANALYSIS.md)

## 🆘 Getting Help

1. Check logs: `tail -f logs/app.log`
2. Check health: `curl http://localhost:5895/health`
3. Check docs: Review [README.md](README.md)
4. Check issues: Search GitHub issues
5. Check troubleshooting: See [DEPLOYMENT.md#troubleshooting](DEPLOYMENT.md#troubleshooting)

## 🎯 Before Production

1. ✅ Test locally: `docker-compose up`
2. ✅ Run tests: `pytest tests/`
3. ✅ Check security: Review security section in README
4. ✅ Configure monitoring: Set up health checks + logging
5. ✅ Plan backups: Database + data backups
6. ✅ Prepare deployment: Follow DEPLOYMENT.md
7. ✅ Load test: Test with production traffic levels

---

**Version**: 1.0.0  
**Status**: ✅ Production Ready  
**Last Updated**: January 10, 2026
