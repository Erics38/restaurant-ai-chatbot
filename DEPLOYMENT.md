# Restaurant AI - Deployment Guide

Complete guide to deploying Restaurant AI to production environments.

---

## Table of Contents

1. [Quick Deploy Options](#quick-deploy-options)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Platform Guides](#cloud-platform-guides)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Production Checklist](#production-checklist)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Quick Deploy Options

### Option 1: One-Click Deploy with Docker (Recommended)

**Requirements**: Any server with Docker installed

```bash
# Clone the repository
git clone https://github.com/Erics38/Tobi-the-local-server-serfing-server.git
cd Tobi-the-local-server-serfing-server

# Download AI model (one-time, optional for template mode)
mkdir -p models
curl -L -o models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf \
  https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf

# Start with AI mode
docker-compose up -d

# OR start with template mode (faster, no AI model needed)
USE_LOCAL_AI=false docker-compose up -d
```

**Access**: http://your-server-ip:8000

### Option 2: Use Pre-built Docker Image

**Requirements**: Docker only

```bash
# Pull latest image from GitHub Container Registry
docker pull ghcr.io/erics38/tobi-the-local-server-serfing-server:latest

# Run it
docker run -d \
  --name restaurant-ai \
  -p 8000:8000 \
  -e USE_LOCAL_AI=false \
  ghcr.io/erics38/tobi-the-local-server-serfing-server:latest
```

**Access**: http://your-server-ip:8000

---

## Docker Deployment

### Basic Docker Compose Setup

**docker-compose.yml** (Template Mode):
```yaml
version: '3.8'

services:
  app:
    image: ghcr.io/erics38/tobi-the-local-server-serfing-server:latest
    container_name: restaurant-ai
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - ENVIRONMENT=production
      - USE_LOCAL_AI=false
      - RESTAURANT_NAME=The Common House
      - SECRET_KEY=your-secret-key-here
    restart: unless-stopped
```

**docker-compose.yml** (AI Mode):
```yaml
version: '3.8'

services:
  app:
    image: ghcr.io/erics38/tobi-the-local-server-serfing-server:latest
    container_name: restaurant-ai
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./models:/app/models:ro
    environment:
      - ENVIRONMENT=production
      - USE_LOCAL_AI=true
      - LLAMA_SERVER_URL=http://llama-server:8080
      - RESTAURANT_NAME=The Common House
      - SECRET_KEY=your-secret-key-here
    restart: unless-stopped
    networks:
      - restaurant-network

  llama-server:
    image: ghcr.io/ggerganov/llama.cpp:server
    container_name: restaurant-ai-llama
    ports:
      - "8080:8080"
    volumes:
      - ./models:/models:ro
    command: >
      -m /models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf
      --host 0.0.0.0
      --port 8080
      --ctx-size 4096
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
    restart: unless-stopped
    networks:
      - restaurant-network

networks:
  restaurant-network:
    driver: bridge
```

### Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Update to latest version
docker-compose pull
docker-compose up -d

# View resource usage
docker stats
```

---

## Cloud Platform Guides

### DigitalOcean (Droplet)

**Cost**: $12-24/month (Template mode: 2GB, AI mode: 4GB)

**Steps**:

1. **Create Droplet**:
   - Image: Docker on Ubuntu 24.04
   - Size: Basic ($24/month for 4GB RAM for AI mode, or $12/month for 2GB for template mode)
   - Region: Closest to your users
   - Authentication: SSH keys recommended

2. **SSH into Droplet**:
   ```bash
   ssh root@your-droplet-ip
   ```

3. **Deploy**:
   ```bash
   # Clone repository
   git clone https://github.com/Erics38/Tobi-the-local-server-serfing-server.git
   cd Tobi-the-local-server-serfing-server

   # For AI mode, download model
   mkdir -p models
   curl -L -o models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf \
     https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf

   # Configure environment
   cp .env.example .env
   nano .env  # Edit configuration

   # Start services
   docker-compose up -d

   # Set up firewall
   ufw allow 8000/tcp
   ufw allow 22/tcp
   ufw enable
   ```

4. **Access**: http://your-droplet-ip:8000

### AWS EC2

**Cost**: ~$30/month (t3.medium for AI mode, t3.micro for template mode)

**Steps**:

1. **Launch EC2 Instance**:
   - AMI: Ubuntu Server 24.04 LTS
   - Instance Type: t3.medium (AI mode) or t3.micro (template mode)
   - Storage: 20GB gp3
   - Security Group: Allow ports 22 (SSH), 8000 (HTTP)

2. **Connect via SSH**:
   ```bash
   ssh -i your-key.pem ubuntu@your-instance-ip
   ```

3. **Install Docker**:
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose-v2
   sudo systemctl enable docker
   sudo systemctl start docker
   sudo usermod -aG docker ubuntu
   ```

4. **Deploy** (same as DigitalOcean steps above)

5. **Optional - Set up domain with Route 53**:
   - Create hosted zone
   - Add A record pointing to EC2 instance IP
   - Update CORS settings in .env

### Google Cloud Platform (GCP)

**Cost**: ~$25/month (e2-medium for AI mode)

**Steps**:

1. **Create Compute Engine VM**:
   - Machine type: e2-medium (AI mode) or e2-small (template mode)
   - Boot disk: Ubuntu 24.04 LTS, 20GB
   - Firewall: Allow HTTP traffic

2. **SSH and Deploy** (same as AWS steps)

3. **Configure firewall**:
   ```bash
   gcloud compute firewall-rules create allow-restaurant-ai \
     --allow=tcp:8000 \
     --source-ranges=0.0.0.0/0 \
     --description="Allow Restaurant AI traffic"
   ```

### Hetzner Cloud (Cheapest Option!)

**Cost**: €4.90/month (CX22 for AI mode: 4GB RAM, 2 vCPU)

**Steps**:

1. **Create Server**:
   - Location: Closest to users
   - Image: Docker CE on Ubuntu 24.04
   - Type: CX22 (AI mode) or CX11 (template mode: €3.79/month)

2. **Deploy** (same steps as DigitalOcean)

**Why Hetzner:**
- 50% cheaper than competitors
- Good performance
- EU-based for GDPR compliance

### Railway.app (One-Click Deploy)

**Cost**: $5-20/month (usage-based)

**Steps**:

1. Click: [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/restaurant-ai)

2. Configure environment variables:
   - `USE_LOCAL_AI`: false (template mode)
   - `RESTAURANT_NAME`: Your restaurant name
   - `SECRET_KEY`: Generate a secure key

3. Deploy automatically!

**Limitations**: AI mode requires 4GB RAM ($20+/month)

### Render.com

**Cost**: $7/month (Starter)

**Steps**:

1. Connect your forked repository
2. Create new Web Service
3. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment: Set USE_LOCAL_AI=false

4. Deploy

### Fly.io

**Cost**: $5-15/month

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch app (in your repo directory)
fly launch

# Deploy
fly deploy

# Scale for AI mode
fly scale memory 4096
```

---

## Kubernetes Deployment

### Basic Kubernetes Manifests

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: restaurant-ai
spec:
  replicas: 2
  selector:
    matchLabels:
      app: restaurant-ai
  template:
    metadata:
      labels:
        app: restaurant-ai
    spec:
      containers:
      - name: restaurant-ai
        image: ghcr.io/erics38/tobi-the-local-server-serfing-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: USE_LOCAL_AI
          value: "false"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: restaurant-ai-secrets
              key: secret-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: restaurant-ai
spec:
  selector:
    app: restaurant-ai
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

**Deploy**:
```bash
kubectl apply -f deployment.yaml
kubectl get pods
kubectl get svc restaurant-ai
```

---

## Environment Configuration

### Required Environment Variables

```bash
# Server
ENVIRONMENT=production        # production, staging, or development
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./data/orders.db

# Restaurant
RESTAURANT_NAME=The Common House

# Security
SECRET_KEY=your-secret-key-here  # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"

# AI Settings
USE_LOCAL_AI=false              # false for template mode, true for AI mode
LLAMA_SERVER_URL=http://llama-server:8080

# Features
ENABLE_MAGIC_PASSWORD=true
MAGIC_PASSWORD=i'm on yelp

# CORS (adjust for your domain)
ALLOWED_ORIGINS=*

# Logging
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
```

### Generating Secrets

```bash
# Generate secure SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Production Checklist

### Security

- [ ] Generate and set unique `SECRET_KEY`
- [ ] Configure `ALLOWED_ORIGINS` to specific domains (not *)
- [ ] Use HTTPS with SSL certificate (Let's Encrypt recommended)
- [ ] Set up firewall (UFW/iptables)
- [ ] Keep Docker images updated
- [ ] Review security scan results in GitHub Actions

### Performance

- [ ] Enable gzip compression (handled by uvicorn)
- [ ] Set up CDN for static files (optional)
- [ ] Configure appropriate resource limits
- [ ] Monitor memory usage (4GB minimum for AI mode)

### Monitoring

- [ ] Set up logging (check logs/app.log)
- [ ] Configure health check endpoint monitoring
- [ ] Set up alerts for downtime
- [ ] Monitor disk space (orders.db grows over time)

### Backup

- [ ] Schedule regular backups of data/orders.db
- [ ] Store models directory securely
- [ ] Document recovery procedures

### SSL/HTTPS Setup

**Using Let's Encrypt with Nginx**:

```bash
# Install Nginx and Certbot
sudo apt install nginx certbot python3-certbot-nginx

# Configure Nginx proxy
sudo nano /etc/nginx/sites-available/restaurant-ai
```

**nginx config**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/restaurant-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is enabled by default
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Manual health check
curl http://your-server-ip:8000/health

# Expected response
{"status":"healthy"}
```

### Logging

```bash
# View application logs
docker-compose logs -f app

# View AI server logs (if using AI mode)
docker-compose logs -f llama-server

# Check log file directly
tail -f logs/app.log
```

### Database Maintenance

```bash
# Backup database
cp data/orders.db data/orders.db.backup

# View database size
du -h data/orders.db

# Clean old orders (if needed)
# TODO: Implement cleanup script
```

### Updates

```bash
# Update to latest version
cd Tobi-the-local-server-serfing-server
git pull origin main
docker-compose pull
docker-compose up -d

# Verify health
curl http://localhost:8000/health
```

---

## Troubleshooting

### Container Won't Start

**Symptom**: `docker-compose up` fails

**Solutions**:
```bash
# Check logs
docker-compose logs

# Remove old containers
docker-compose down -v

# Rebuild
docker-compose up --build -d
```

### Port Already in Use

**Symptom**: "Address already in use"

**Solutions**:
```bash
# Find process using port 8000
sudo lsof -i :8000
# OR on Windows
netstat -ano | findstr :8000

# Kill process
sudo kill -9 <PID>

# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Map to different external port
```

### AI Server Not Responding

**Symptom**: Slow or no responses in AI mode

**Solutions**:
```bash
# Check if llama-server is running
docker-compose ps

# Check logs
docker-compose logs llama-server

# Verify model file exists
ls -lh models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf

# Restart AI server
docker-compose restart llama-server

# Check memory
docker stats llama-server
# Requires 4GB minimum
```

### Database Locked

**Symptom**: "database is locked" errors

**Solutions**:
```bash
# Stop all containers
docker-compose down

# Remove lock file if exists
rm data/orders.db-journal

# Restart
docker-compose up -d
```

### High Memory Usage

**Symptom**: Server running out of RAM

**Solutions**:
1. Template mode uses ~200MB, AI mode uses ~4GB
2. If using AI mode on small server, switch to template mode:
   ```bash
   # Edit docker-compose.yml
   USE_LOCAL_AI=false

   # Restart
   docker-compose up -d
   ```

### Slow Performance

**Solutions**:
- AI mode: First response takes 30-60s (model loading), then 2-10s per request
- Template mode: <10ms per request
- Check server resources with `docker stats`
- Consider upgrading server if using AI mode

---

## Cost Comparison

| Platform | Template Mode | AI Mode | Notes |
|----------|--------------|---------|-------|
| **Hetzner** | €3.79/mo | €4.90/mo | Cheapest, EU-based |
| **DigitalOcean** | $12/mo | $24/mo | Easy to use, good docs |
| **AWS EC2** | $5/mo (t3.micro) | $30/mo (t3.medium) | Flexible, powerful |
| **GCP** | $5/mo | $25/mo | Good integration |
| **Railway** | $5/mo | $20+/mo | Automatic deploys |
| **Render** | $7/mo | Not recommended | Limited memory |
| **Fly.io** | $5/mo | $15/mo | Global edge network |

**Recommendation**:
- **Development**: Use Docker locally (free!)
- **Production (Template Mode)**: Hetzner CX11 (€3.79/mo)
- **Production (AI Mode)**: Hetzner CX22 (€4.90/mo)

---

## Support

- **Documentation**: [README.md](README.md), [SETUP.md](SETUP.md), [CICD.md](CICD.md)
- **GitHub Issues**: https://github.com/Erics38/Tobi-the-local-server-serfing-server/issues
- **API Documentation**: http://your-server:8000/api/docs

---

Your restaurant AI is ready for production.
