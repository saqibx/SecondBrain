# Self-Hosted Server Deployment Guide

A quick guide to deploying SecondBrain on your own server (VPS, dedicated server, or on-premise).

---

## 🚀 Quick Start (5-10 minutes)

### Prerequisites
- Ubuntu/Debian server (20.04 LTS or newer recommended)
- SSH access to your server
- Domain name (optional but recommended)
- Basic command line knowledge

### Step 1: Connect to Your Server
```bash
ssh root@your_server_ip
# or: ssh user@your_server_ip (if not root)
```

### Step 2: Install Docker & Dependencies
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install -y docker-compose

# Verify installations
docker --version
docker-compose --version

# Add your user to docker group (optional, avoids sudo)
sudo usermod -aG docker $USER
newgrp docker
```

### Step 3: Clone Your Project
```bash
# Navigate to deployment directory
cd /opt
# or: cd /home/yourusername

# Clone repository
git clone https://github.com/saqibx/SecondBrain.git
cd SecondBrain
```

### Step 4: Configure Environment Variables
```bash
# Copy example to production
cp .env.example .env.production

# Edit with your settings
nano .env.production
```

Edit these critical values:
```bash
FLASK_ENV=production
APP_SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_hex(32))">
MONGO_URI=mongodb+srv://admin:YOUR_PASSWORD@cluster.mongodb.net/secondbrain
REDIS_URL=rediss://default:YOUR_PASSWORD@redis-host:6380
OPENAI_API_KEY=sk-...your key...
TAVILY_API_KEY=tvly-...your key...
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
PASSWORD_MIN_LENGTH=10
```

### Step 5: Deploy with Docker Compose
```bash
# Build and start services
docker-compose -f docker-compose.yml --env-file .env.production up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

### Step 6: Verify Deployment
```bash
# Test health check
curl http://localhost:5895/health

# Should return:
# {"status": "healthy", "database": "connected", "cache": "connected"}
```

### Step 7: Setup Nginx Reverse Proxy (Recommended)
```bash
# Install Nginx
sudo apt-get install -y nginx

# Create Nginx config
sudo nano /etc/nginx/sites-available/secondbrain
```

Paste this configuration:
```nginx
upstream secondbrain {
    server 127.0.0.1:5895;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL certificates (get free ones from Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    
    # Proxy settings
    location / {
        proxy_pass http://secondbrain;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }
}
```

Enable and test:
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/secondbrain /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 8: Get SSL Certificate (Free with Let's Encrypt)
```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is set up automatically
sudo systemctl enable certbot.timer
```

---

## 📋 Full Deployment Options

### Option A: Simple Docker (Recommended for Most)

**Best for**: Single server, small to medium traffic

```bash
# 1. Go to your project directory
cd /opt/SecondBrain

# 2. Create .env.production with your settings
cp .env.example .env.production
nano .env.production

# 3. Start services
docker-compose -f docker-compose.yml --env-file .env.production up -d

# 4. View logs
docker-compose logs -f app

# 5. Access at http://your_server_ip:5895/health
```

**Start/Stop/Restart**:
```bash
docker-compose -f docker-compose.yml --env-file .env.production up -d     # Start
docker-compose -f docker-compose.yml --env-file .env.production down      # Stop
docker-compose -f docker-compose.yml --env-file .env.production restart   # Restart
```

---

### Option B: Docker + Nginx + SSL (Production Ready)

**Best for**: Public facing, needs HTTPS

**Step-by-step**:

1. **Setup Docker** (see Step 2 above)

2. **Deploy app**:
```bash
cd /opt/SecondBrain
cp .env.example .env.production
nano .env.production
docker-compose -f docker-compose.yml --env-file .env.production up -d
```

3. **Install and configure Nginx** (see Step 7 above)

4. **Get SSL certificate** (see Step 8 above)

5. **Verify**: `https://yourdomain.com/health`

---

### Option C: Direct Installation (No Docker)

**Best for**: Custom deployments, development

```bash
# 1. Install dependencies
sudo apt-get install -y python3.11 python3.11-venv python3-pip
sudo apt-get install -y redis-server mongodb

# 2. Clone and setup
cd /opt/SecondBrain
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Create .env.production
cp .env.example .env.production
nano .env.production

# 4. Run with Gunicorn
gunicorn --workers 4 --bind 0.0.0.0:5895 app:app

# 5. Setup systemd service (see Option C section below)
```

**Create systemd service** (`/etc/systemd/system/secondbrain.service`):
```ini
[Unit]
Description=SecondBrain Flask Application
After=network.target redis.service

[Service]
Type=notify
User=secondbrain
WorkingDirectory=/opt/SecondBrain
Environment="PATH=/opt/SecondBrain/venv/bin"
ExecStart=/opt/SecondBrain/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:5895 app:app
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable secondbrain
sudo systemctl start secondbrain
sudo systemctl status secondbrain
```

---

### Option D: Systemd Service with Docker

**Best for**: Simplified management with systemd

Create `/etc/systemd/system/secondbrain-docker.service`:
```ini
[Unit]
Description=SecondBrain Docker Application
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/SecondBrain
ExecStart=/usr/bin/docker-compose -f docker-compose.yml --env-file .env.production up
ExecStop=/usr/bin/docker-compose -f docker-compose.yml --env-file .env.production down
Restart=on-failure
RestartSec=10s
User=root

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable secondbrain-docker
sudo systemctl start secondbrain-docker
sudo systemctl status secondbrain-docker
```

---

## 🔧 Configuration Checklist

### Environment Variables Required
```bash
# Core
FLASK_ENV=production
APP_SECRET_KEY=<32-char hex string>
DEBUG=False

# Database
MONGO_URI=mongodb+srv://admin:password@cluster.mongodb.net/db
REDIS_URL=rediss://user:password@host:6380

# APIs
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Security
ALLOWED_ORIGINS=https://yourdomain.com
PASSWORD_MIN_LENGTH=10
MAX_LOGIN_ATTEMPTS=3
ACCOUNT_LOCKOUT_DURATION=1800

# Rate Limiting
RATELIMIT_ENABLED=true
RATELIMIT_DEFAULT=50/hour
RATELIMIT_LOGIN=3/minute
RATELIMIT_REGISTER=1/hour
RATELIMIT_CHAT=20/minute

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/secondbrain/app.log

# Server
HOST=0.0.0.0
PORT=5895
```

### Database Setup

**MongoDB Atlas (Cloud - Recommended)**:
1. Go to https://www.mongodb.com/cloud/atlas
2. Create cluster
3. Get connection string
4. Set in `MONGO_URI`

**MongoDB Local**:
```bash
docker-compose up -d mongodb
# Connection: mongodb://admin:password@localhost:27017
```

**Redis Cloud (Recommended)**:
1. Go to https://redis.com/try-free/
2. Create database
3. Get connection string
4. Set in `REDIS_URL`

**Redis Local**:
```bash
docker-compose up -d redis
# Connection: redis://:password@localhost:6379
```

---

## 📊 Monitoring & Maintenance

### View Logs
```bash
# Docker
docker-compose logs -f app
docker-compose logs --tail 100 app

# Systemd
sudo journalctl -u secondbrain -f
sudo journalctl -u secondbrain --tail 100
```

### Check Health
```bash
curl https://yourdomain.com/health
# Should return: {"status": "healthy", "database": "connected", "cache": "connected"}
```

### Restart Service
```bash
# Docker
docker-compose restart app

# Systemd
sudo systemctl restart secondbrain
```

### Update Application
```bash
cd /opt/SecondBrain
git pull origin main
docker-compose build
docker-compose restart app
```

### Backup Data
```bash
# Backup MongoDB
docker-compose exec -T mongodb mongodump --username admin --password $MONGO_PASSWORD --out /backup

# Backup Redis
docker-compose exec -T redis redis-cli SAVE
docker cp secondbrain_redis:/data/dump.rdb ./redis_backup.rdb
```

---

## 🔐 Security Best Practices

### 1. Firewall Configuration
```bash
# Ubuntu/Debian with ufw
sudo ufw enable
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw deny 5895/tcp    # Don't expose app port directly
```

### 2. Use Strong Secrets
```bash
# Generate secure keys
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Enable SSL/TLS (Mandatory)
```bash
# Use Let's Encrypt (free)
sudo certbot certonly --nginx -d yourdomain.com
```

### 4. Regular Updates
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d
```

### 5. Monitor for Intrusions
```bash
# Install fail2ban
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
```

---

## 🆘 Troubleshooting

### App won't start
```bash
# Check logs
docker-compose logs app

# Verify .env.production is correct
cat .env.production

# Restart
docker-compose restart app
```

### Health check fails
```bash
# Check database connection
docker-compose exec -T app curl http://localhost:5895/health

# Check individual services
docker-compose ps
docker-compose logs mongodb
docker-compose logs redis
```

### High memory usage
```bash
# Restart services
docker-compose restart

# Check disk space
df -h

# Check memory
free -h
```

### Database connection timeout
```bash
# Verify MONGO_URI is correct
echo $MONGO_URI

# Test connection manually
docker-compose exec -T mongodb mongosh --username admin --password $MONGO_PASSWORD
```

### Port already in use
```bash
# Find what's using port 5895
sudo lsof -i :5895

# Change port in docker-compose.yml
# ports: - "5896:5895"
```

---

## 📚 Next Steps

1. ✅ Deploy application (see Quick Start above)
2. ✅ Configure domain and SSL certificate
3. ✅ Setup monitoring and alerting
4. ✅ Configure backups
5. ✅ Test everything works
6. ✅ Document your setup

---

## 💡 Tips

- **Use docker-compose for simplicity** - Manages all services
- **Get free SSL from Let's Encrypt** - Never use HTTP in production
- **Monitor logs regularly** - Catch issues early
- **Backup regularly** - Automate with cron jobs
- **Update regularly** - Security patches are important
- **Test deployments** - Use staging first

---

## Quick Reference Commands

```bash
# View status
docker-compose ps

# View logs (real-time)
docker-compose logs -f app

# Restart app
docker-compose restart app

# Stop all services
docker-compose down

# Start all services
docker-compose up -d

# Update and deploy
git pull && docker-compose build && docker-compose up -d

# Check health
curl https://yourdomain.com/health

# SSH into container
docker-compose exec app bash

# View environment variables
docker-compose exec -T app env | grep FLASK
```

---

## Support Resources

- **Docker docs**: https://docs.docker.com
- **Docker Compose**: https://docs.docker.com/compose
- **Nginx**: https://nginx.org/en/docs
- **Let's Encrypt**: https://letsencrypt.org
- **MongoDB Atlas**: https://www.mongodb.com/cloud/atlas
- **Redis Cloud**: https://redis.com/try-free

Good luck with your deployment! 🚀
