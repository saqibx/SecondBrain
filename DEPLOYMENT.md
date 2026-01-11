# Deployment Guide

This guide provides detailed instructions for deploying SecondBrain to production environments.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Preparation](#environment-preparation)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Managed Services](#managed-services)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Backup and Recovery](#backup-and-recovery)
8. [Troubleshooting](#troubleshooting)

## Pre-Deployment Checklist

- [ ] All environment variables configured in production `.env`
- [ ] MongoDB connection tested and credentials verified
- [ ] Redis connection tested and credentials verified
- [ ] OpenAI and Tavily API keys validated
- [ ] Firewall rules configured
- [ ] SSL/TLS certificates obtained
- [ ] Domain registered and DNS configured
- [ ] Backup strategy documented
- [ ] Monitoring and alerting configured
- [ ] Log aggregation set up
- [ ] Rate limiting adjusted for expected load

## Environment Preparation

### 1. Secure Configuration

Create a production `.env` file:

```bash
# Copy and customize
cp .env.example .env.production

# Use strong secrets
FLASK_ENV=production
APP_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Production database URIs
MONGO_URI=mongodb+srv://admin:PASSWORD@cluster.mongodb.net/secondbrain?retryWrites=true&w=majority
REDIS_URL=rediss://user:PASSWORD@redis-host:6380/0

# API Keys (use secrets manager in production)
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# CORS for your domain
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Security
PASSWORD_MIN_LENGTH=10
MAX_LOGIN_ATTEMPTS=3
ACCOUNT_LOCKOUT_DURATION=1800  # 30 minutes

# Performance
RATELIMIT_ENABLED=true
RATELIMIT_DEFAULT=50/hour
RATELIMIT_LOGIN=3/minute
RATELIMIT_REGISTER=1/hour
RATELIMIT_CHAT=20/minute

# Logging
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=5895
```

### 2. Dependencies

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    docker.io \
    docker-compose \
    redis-server \
    curl \
    git

# Verify installations
python3.11 --version
docker --version
redis-cli --version
```

## Docker Deployment

### Single Container Deployment

```bash
# Build image
docker build -t secondbrain:latest .

# Run container with external MongoDB and Redis
docker run -d \
  --name secondbrain \
  --restart unless-stopped \
  -p 5895:5895 \
  -e FLASK_ENV=production \
  -e MONGO_URI=mongodb+srv://... \
  -e REDIS_URL=rediss://... \
  -e OPENAI_API_KEY=sk-... \
  -e TAVILY_API_KEY=tvly-... \
  -v /var/log/secondbrain:/app/logs \
  secondbrain:latest

# Check status
docker ps
docker logs secondbrain

# Health check
curl http://localhost:5895/health
```

### Docker Compose with Reverse Proxy

```yaml
version: '3.8'

services:
  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: secondbrain_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - app
    networks:
      - secondbrain_net

  # MongoDB
  mongodb:
    image: mongo:7.0
    container_name: secondbrain_mongo
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
    volumes:
      - mongo_data:/data/db
    networks:
      - secondbrain_net

  # Redis
  redis:
    image: redis:7.2-alpine
    container_name: secondbrain_redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - secondbrain_net

  # Application
  app:
    build: .
    container_name: secondbrain_app
    environment:
      FLASK_ENV: production
      MONGO_URI: mongodb://admin:${MONGO_PASSWORD}@mongodb:27017
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      TAVILY_API_KEY: ${TAVILY_API_KEY}
      APP_SECRET_KEY: ${APP_SECRET_KEY}
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS}
    volumes:
      - app_logs:/app/logs
      - app_data:/app/DATA
    networks:
      - secondbrain_net
    restart: unless-stopped

volumes:
  mongo_data:
  redis_data:
  app_logs:
  app_data:

networks:
  secondbrain_net:
    driver: bridge
```

## Kubernetes Deployment

### Namespace and Secrets

```bash
# Create namespace
kubectl create namespace secondbrain

# Create secrets from environment file
kubectl create secret generic app-secrets \
  --from-literal=openai-api-key=sk-... \
  --from-literal=tavily-api-key=tvly-... \
  --from-literal=app-secret-key=$(python -c "import secrets; print(secrets.token_hex(32))") \
  -n secondbrain
```

### Deployment Manifest

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: secondbrain
data:
  FLASK_ENV: production
  LOG_LEVEL: INFO
  RATELIMIT_ENABLED: "true"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secondbrain
  namespace: secondbrain
spec:
  replicas: 3
  selector:
    matchLabels:
      app: secondbrain
  template:
    metadata:
      labels:
        app: secondbrain
    spec:
      containers:
      - name: app
        image: secondbrain:latest
        ports:
        - containerPort: 5895
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
        env:
        - name: MONGO_URI
          value: mongodb+srv://admin:password@mongodb-host
        - name: REDIS_URL
          value: rediss://redis-host:6380
        livenessProbe:
          httpGet:
            path: /health
            port: 5895
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5895
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: secondbrain-service
  namespace: secondbrain
spec:
  type: LoadBalancer
  selector:
    app: secondbrain
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5895

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: secondbrain-hpa
  namespace: secondbrain
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: secondbrain
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

Deploy to Kubernetes:

```bash
# Apply manifests
kubectl apply -f deployment.yaml

# Check deployment status
kubectl get deployment -n secondbrain
kubectl get pods -n secondbrain
kubectl get svc -n secondbrain

# Check logs
kubectl logs -n secondbrain deployment/secondbrain -f
```

## Managed Services

### Using MongoDB Atlas

1. Create cluster at https://www.mongodb.com/cloud/atlas
2. Configure IP whitelist
3. Create database user
4. Get connection string
5. Set in `.env`:
   ```
   MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/secondbrain?retryWrites=true&w=majority
   ```

### Using Redis Cloud

1. Create database at https://redis.com/try-free/
2. Get connection URL (with SSL)
3. Set in `.env`:
   ```
   REDIS_URL=rediss://user:password@host:port
   ```

### Using AWS Services

**RDS for MongoDB**:
```
MONGO_URI=mongodb://admin:password@rds-endpoint:27017/secondbrain
```

**ElastiCache for Redis**:
```
REDIS_URL=rediss://endpoint:port
```

## Monitoring and Maintenance

### Health Monitoring

```bash
# Check health endpoint
curl https://yourdomain.com/health

# Response should include:
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

### Log Aggregation (ELK Stack)

Configure Filebeat to ship logs:

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/secondbrain/app.log
    - /var/log/secondbrain/error.log

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

### Metrics (Prometheus)

Add Prometheus monitoring:

```python
# In app.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Request latency')

@app.after_request
def track_metrics(response):
    REQUEST_COUNT.labels(method=request.method, endpoint=request.endpoint).inc()
    return response

@app.route('/metrics')
def metrics():
    return generate_latest()
```

## Backup and Recovery

### MongoDB Backup

```bash
# Full backup
mongodump --uri="mongodb+srv://user:pass@host/secondbrain" --out ./backup

# Restore
mongorestore --uri="mongodb+srv://user:pass@host" ./backup

# Automated daily backup (cron)
0 2 * * * mongodump --uri="mongodb+srv://..." --out /backups/mongodb-$(date +\%Y\%m\%d)
```

### Redis Backup

```bash
# Manual save
redis-cli BGSAVE

# Automated backup
0 3 * * * cp /var/lib/redis/dump.rdb /backups/redis-$(date +\%Y\%m\%d).rdb
```

### Application Data Backup

```bash
# Backup ChromaDB and user files
tar -czf secondbrain-data-$(date +%Y%m%d).tar.gz /app/DATA /app/Classes/chroma_db

# Automated daily backup
0 4 * * * tar -czf /backups/secondbrain-data-$(date +\%Y\%m\%d).tar.gz /app/DATA /app/Classes/chroma_db
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker logs secondbrain

# Common issues:
# 1. Missing environment variables
# 2. Database connection refused
# 3. Redis connection refused
# 4. Port already in use

# Free port if needed
lsof -i :5895
kill -9 <PID>
```

### High Memory Usage

```bash
# Check Redis memory
redis-cli INFO memory

# Check MongoDB memory
mongostat

# Solutions:
# - Increase container limits
# - Implement cache eviction
# - Review large queries
```

### Slow API Responses

```bash
# Enable detailed logging
LOG_LEVEL=DEBUG

# Check:
# - Database query performance (MongoDB explain)
# - LLM API response times
# - Network latency
# - Rate limiting impact

# MongoDB query analysis
db.collection.find(...).explain("executionStats")
```

### Failed Authentication

```bash
# Check user exists in MongoDB
db.users.find({"username":"testuser"})

# Verify password hash format
db.users.findOne()  # Check "password" field format

# Clear sessions (optional)
redis-cli FLUSHDB
```

## Security Hardening Checklist

- [ ] Use HTTPS/TLS only
- [ ] Enable HSTS headers
- [ ] Configure firewall rules
- [ ] Use secrets manager (AWS Secrets Manager, HashiCorp Vault)
- [ ] Enable database encryption at rest
- [ ] Enable database encryption in transit (SSL/TLS)
- [ ] Regular security patches and updates
- [ ] Monitor and limit API key usage
- [ ] Set up intrusion detection
- [ ] Regular penetration testing

## Performance Optimization

### Caching Strategy

```python
# Cache LLM responses
from functools import lru_cache

@lru_cache(maxsize=128)
def get_summary_cached(text: str) -> str:
    return get_summary_fromAI(text)
```

### Connection Pooling

Already configured in `config.py`:
- MongoDB: retryWrites, connection pooling
- Redis: connection pooling
- ChromaDB: single instance per user

### Load Balancing

Use HAProxy or nginx upstream:

```nginx
upstream secondbrain {
    least_conn;
    server app1:5895;
    server app2:5895;
    server app3:5895;
}

server {
    listen 80;
    location / {
        proxy_pass http://secondbrain;
    }
}
```

## Scaling Recommendations

- **Small deployment** (< 100 users): Single instance + external DB/Redis
- **Medium** (100-10k users): 3-5 instances + managed DB/Redis
- **Large** (> 10k users): Kubernetes cluster + multi-region + CDN

---

For production support and questions, refer to the [README.md](README.md).
