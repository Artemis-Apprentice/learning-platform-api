# Digital Ocean Deployment Plan

## Overview

This document outlines the deployment strategy for the Learning Platform API to Digital Ocean using GitHub Actions for automated deployment.

**Project:** Django REST API with PostgreSQL database  
**Deployment Target:** Digital Ocean Droplet  
**Deployment Method:** GitHub Actions (automated on push to main)  
**Database:** PostgreSQL in Docker container  
**Web Server:** Gunicorn + Nginx

---

## Table of Contents

1. [Architecture Options](#architecture-options)
2. [Prerequisites](#prerequisites)
3. [Droplet Setup](#droplet-setup)
4. [Environment Configuration](#environment-configuration)
5. [GitHub Actions Workflow](#github-actions-workflow)
6. [Deployment Process](#deployment-process)
7. [Monitoring Setup (Optional)](#monitoring-setup-optional)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting](#troubleshooting)
10. [Rollback Strategy](#rollback-strategy)

---

## Architecture Options

### Option A: Shared Droplet (Backend + Frontend)

**Pros:**
- Lower cost (single droplet)
- Simpler infrastructure management
- Shared resources

**Cons:**
- Resource contention between frontend and backend
- Single point of failure
- More complex nginx configuration

**Recommended Droplet Size:** 4GB RAM / 2 vCPUs minimum

### Option B: Dedicated API Droplet (Recommended)

**Pros:**
- Better resource isolation
- Independent scaling
- Clearer separation of concerns
- Easier to debug and monitor

**Cons:**
- Higher cost (additional droplet)
- Slightly more complex networking

**Recommended Droplet Size:** 2GB RAM / 1 vCPU minimum (can scale up)

---

## Prerequisites

### 1. Digital Ocean Setup

- [ ] Digital Ocean account with billing enabled
- [ ] Droplet created (Ubuntu 22.04 LTS recommended)
- [ ] SSH key added to Digital Ocean account
- [ ] Domain/subdomain configured (e.g., `api.learning.nss.team` or `learningapi.nss.team`)
- [ ] DNS A record pointing to droplet IP

### 2. GitHub Repository Setup

- [ ] Repository secrets configured (see [Environment Configuration](#environment-configuration))
- [ ] SSH deploy key generated and added

### 3. Local Development

- [ ] Docker and Docker Compose installed
- [ ] Application tested locally with [`docker-compose.yml`](../docker-compose.yml)
- [ ] All environment variables documented

---

## Droplet Setup

### Initial Server Configuration

```bash
# SSH into your droplet
ssh root@your-droplet-ip

# Update system packages
apt update && apt upgrade -y

# Install required packages
apt install -y \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    ufw

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Create deployment user
useradd -m -s /bin/bash deploy
usermod -aG docker deploy
mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh

# Create application directory
mkdir -p /var/www/learning-platform-api
chown -R deploy:deploy /var/www/learning-platform-api

# Create logs directory
mkdir -p /var/www/learning-platform-api/logs
chown -R deploy:deploy /var/www/learning-platform-api/logs
```

### Firewall Configuration

```bash
# Configure UFW firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw enable
```

### Nginx Configuration

Create `/etc/nginx/sites-available/learning-api`:

```nginx
upstream django_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.learning.nss.team learningapi.nss.team;

    client_max_body_size 10M;

    # Logging
    access_log /var/log/nginx/learning-api-access.log;
    error_log /var/log/nginx/learning-api-error.log;

    # Static files
    location /static/ {
        alias /var/www/learning.nss.team/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Prometheus metrics (optional - restrict access)
    location /metrics {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Restrict access to monitoring tools only
        allow 127.0.0.1;
        deny all;
    }

    # API endpoints
    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://django_app;
        access_log off;
    }
}
```

Enable the site:

```bash
ln -s /etc/nginx/sites-available/learning-api /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### SSL Certificate Setup

```bash
# Install SSL certificate with Let's Encrypt
certbot --nginx -d api.learning.nss.team -d learningapi.nss.team

# Auto-renewal is configured by default
# Test renewal:
certbot renew --dry-run
```

---

## Environment Configuration

### GitHub Secrets

Configure the following secrets in your GitHub repository (`Settings > Secrets and variables > Actions`):

#### Required Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `DROPLET_HOST` | Droplet IP address or domain | `123.45.67.89` |
| `DROPLET_USER` | SSH user (deploy) | `deploy` |
| `DROPLET_SSH_KEY` | Private SSH key for deployment | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `LEARN_OPS_DB` | Database name | `learnops` |
| `LEARN_OPS_USER` | Database user | `learnops_user` |
| `LEARN_OPS_PASSWORD` | Database password | `secure_password_here` |
| `LEARN_OPS_PORT` | Database port | `5432` |
| `LEARN_OPS_DJANGO_SECRET_KEY` | Django secret key | Generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'` |
| `LEARN_OPS_CLIENT_ID` | GitHub OAuth Client ID | From GitHub OAuth App |
| `LEARN_OPS_SECRET_KEY` | GitHub OAuth Secret | From GitHub OAuth App |
| `LEARN_OPS_ALLOWED_HOSTS` | Comma-separated allowed hosts | `api.learning.nss.team,learningapi.nss.team` |
| `LEARN_OPS_SUPERUSER_NAME` | Django superuser username | `admin` |
| `LEARN_OPS_SUPERUSER_PASSWORD` | Django superuser password | `secure_admin_password` |
| `LEARNING_GITHUB_CALLBACK` | GitHub OAuth callback URL | `https://learning.nss.team/auth/github` |

#### Optional Secrets (for monitoring)

| Secret Name | Description | Example |
|------------|-------------|---------|
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password | `secure_grafana_password` |

### Server Environment File

Create `/var/www/learning-platform-api/.env` on the droplet:

```bash
# Database Configuration
LEARN_OPS_DB=learnops
LEARN_OPS_USER=learnops_user
LEARN_OPS_PASSWORD=your_secure_password
LEARN_OPS_HOST=db
LEARN_OPS_PORT=5432

# Django Configuration
LEARN_OPS_DJANGO_SECRET_KEY=your_django_secret_key
LEARN_OPS_ALLOWED_HOSTS=api.learning.nss.team,learningapi.nss.team,127.0.0.1,localhost
DEBUG=False
DEVELOPMENT_MODE=False

# GitHub OAuth
LEARN_OPS_CLIENT_ID=your_github_client_id
LEARN_OPS_SECRET_KEY=your_github_secret
LEARNING_GITHUB_CALLBACK=https://learning.nss.team/auth/github

# Superuser
LEARN_OPS_SUPERUSER_NAME=admin
LEARN_OPS_SUPERUSER_PASSWORD=your_admin_password

# Python
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

**Important:** Set proper permissions:
```bash
chmod 600 /var/www/learning-platform-api/.env
chown deploy:deploy /var/www/learning-platform-api/.env
```

---

## GitHub Actions Workflow

### Deployment Workflow File

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Digital Ocean

on:
  push:
    branches:
      - main
  workflow_dispatch:  # Allow manual triggering

jobs:
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.8.0
        with:
          ssh-private-key: ${{ secrets.DROPLET_SSH_KEY }}

      - name: Add server to known hosts
        run: |
          mkdir -p ~/.ssh
          ssh-keyscan -H ${{ secrets.DROPLET_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy to droplet
        env:
          DROPLET_HOST: ${{ secrets.DROPLET_HOST }}
          DROPLET_USER: ${{ secrets.DROPLET_USER }}
        run: |
          ssh $DROPLET_USER@$DROPLET_HOST << 'ENDSSH'
            set -e
            
            # Navigate to application directory
            cd /var/www/learning-platform-api
            
            # Pull latest code
            echo "📥 Pulling latest code..."
            git pull origin main
            
            # Build new Docker images
            echo "🔨 Building Docker images..."
            docker-compose build --no-cache web
            
            # Stop existing containers
            echo "🛑 Stopping existing containers..."
            docker-compose down
            
            # Start containers with new images
            echo "🚀 Starting containers..."
            docker-compose up -d
            
            # Wait for database to be ready
            echo "⏳ Waiting for database..."
            sleep 10
            
            # Run migrations
            echo "🔄 Running database migrations..."
            docker-compose exec -T web python manage.py migrate --noinput
            
            # Collect static files
            echo "📦 Collecting static files..."
            docker-compose exec -T web python manage.py collectstatic --noinput
            
            # Check container health
            echo "🏥 Checking container health..."
            docker-compose ps
            
            # Cleanup old images
            echo "🧹 Cleaning up old Docker images..."
            docker image prune -f
            
            echo "✅ Deployment completed successfully!"
          ENDSSH

      - name: Verify deployment
        env:
          DROPLET_HOST: ${{ secrets.DROPLET_HOST }}
        run: |
          echo "🔍 Verifying deployment..."
          sleep 5
          curl -f https://api.learning.nss.team/health || exit 1
          echo "✅ Health check passed!"

      - name: Notify on failure
        if: failure()
        run: |
          echo "❌ Deployment failed! Check the logs above for details."
```

### SSH Key Setup

Generate an SSH key pair for deployment:

```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_key

# Add public key to droplet
ssh root@your-droplet-ip
cat >> /home/deploy/.ssh/authorized_keys << EOF
[paste public key here]
EOF
chmod 600 /home/deploy/.ssh/authorized_keys
chown deploy:deploy /home/deploy/.ssh/authorized_keys

# Add private key to GitHub Secrets as DROPLET_SSH_KEY
cat ~/.ssh/github_deploy_key  # Copy this to GitHub
```

---

## Deployment Process

### Initial Deployment

1. **Clone repository on droplet:**

```bash
ssh deploy@your-droplet-ip
cd /var/www/learning-platform-api
git clone https://github.com/your-org/learning-platform-api.git .
```

2. **Create production docker-compose file:**

Create `/var/www/learning-platform-api/docker-compose.prod.yml`:

```yaml
services:
  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=${LEARN_OPS_DB}
      - POSTGRES_USER=${LEARN_OPS_USER}
      - POSTGRES_PASSWORD=${LEARN_OPS_PASSWORD}
    volumes:
      - lp_data:/var/lib/postgresql/data
      - ./init-db.sh:/docker-entrypoint-initdb.d/01-init.sh:ro
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${LEARN_OPS_USER} -d ${LEARN_OPS_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  web:
    build: .
    working_dir: /app
    environment:
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      - LEARN_OPS_DB=${LEARN_OPS_DB}
      - LEARN_OPS_USER=${LEARN_OPS_USER}
      - LEARN_OPS_PASSWORD=${LEARN_OPS_PASSWORD}
      - LEARN_OPS_HOST=db
      - LEARN_OPS_PORT=${LEARN_OPS_PORT}
      - LEARN_OPS_CLIENT_ID=${LEARN_OPS_CLIENT_ID}
      - LEARN_OPS_SECRET_KEY=${LEARN_OPS_SECRET_KEY}
      - LEARN_OPS_DJANGO_SECRET_KEY=${LEARN_OPS_DJANGO_SECRET_KEY}
      - LEARN_OPS_ALLOWED_HOSTS=${LEARN_OPS_ALLOWED_HOSTS}
      - LEARN_OPS_SUPERUSER_NAME=${LEARN_OPS_SUPERUSER_NAME}
      - LEARN_OPS_SUPERUSER_PASSWORD=${LEARN_OPS_SUPERUSER_PASSWORD}
      - LEARNING_GITHUB_CALLBACK=${LEARNING_GITHUB_CALLBACK}
      - DEBUG=False
      - DEVELOPMENT_MODE=False
    volumes:
      - static_volume:/var/www/learning.nss.team/static
      - ./logs:/app/logs
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: always
    command: >
      bash -c "
        /app/django-entrypoint.sh &&
        gunicorn LearningPlatform.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60 --access-logfile - --error-logfile -
      "
    networks:
      - app-network

volumes:
  lp_data:
  static_volume:

networks:
  app-network:
    driver: bridge
```

3. **Update requirements.txt to include Gunicorn:**

Add to [`requirements.txt`](../requirements.txt):
```
gunicorn==21.2.0
```

4. **Initial deployment:**

```bash
cd /var/www/learning-platform-api
docker-compose -f docker-compose.prod.yml up -d
```

### Automated Deployments

After initial setup, deployments are automatic:

1. Push code to `main` branch
2. GitHub Actions workflow triggers
3. Code is pulled on droplet
4. Docker images are rebuilt
5. Containers are restarted
6. Migrations run automatically
7. Static files collected
8. Health check verifies deployment

### Manual Deployment

If needed, deploy manually:

```bash
ssh deploy@your-droplet-ip
cd /var/www/learning-platform-api
git pull origin main
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

---

## Monitoring Setup (Optional)

### Add Monitoring to Production

Update `docker-compose.prod.yml` to include Prometheus and Grafana:

```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "127.0.0.1:9090:9090"
    depends_on:
      - web
    restart: always
    networks:
      - app-network

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://grafana.learning.nss.team
    ports:
      - "127.0.0.1:3001:3000"
    depends_on:
      - prometheus
    restart: always
    networks:
      - app-network

volumes:
  prometheus_data:
  grafana_data:
```

### Nginx Configuration for Monitoring

Add to nginx config for Grafana access:

```nginx
server {
    listen 80;
    server_name grafana.learning.nss.team;

    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then run:
```bash
certbot --nginx -d grafana.learning.nss.team
```

---

## Security Considerations

### 1. Environment Variables

- ✅ Never commit `.env` files to Git
- ✅ Use GitHub Secrets for sensitive data
- ✅ Rotate secrets regularly (every 90 days)
- ✅ Use strong, unique passwords

### 2. Database Security

- ✅ Database not exposed to public internet (127.0.0.1 only)
- ✅ Strong database passwords
- ✅ Regular backups (see backup strategy below)

### 3. Application Security

- ✅ `DEBUG=False` in production
- ✅ `ALLOWED_HOSTS` properly configured
- ✅ HTTPS enforced via nginx
- ✅ CORS properly configured in [`settings.py`](../LearningPlatform/settings.py)

### 4. Server Security

- ✅ UFW firewall enabled
- ✅ SSH key authentication only (disable password auth)
- ✅ Regular system updates
- ✅ Fail2ban for brute force protection (optional)

### 5. Docker Security

- ✅ Run containers as non-root user
- ✅ Regular image updates
- ✅ Scan images for vulnerabilities

### Backup Strategy

Create backup script `/var/www/learning-platform-api/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/learning-platform"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker-compose -f /var/www/learning-platform-api/docker-compose.prod.yml exec -T db \
  pg_dump -U $LEARN_OPS_USER $LEARN_OPS_DB | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/db_backup_$DATE.sql.gz"
```

Add to crontab:
```bash
crontab -e
# Add: Daily backup at 2 AM
0 2 * * * /var/www/learning-platform-api/backup.sh >> /var/log/backup.log 2>&1
```

---

## Troubleshooting

### Common Issues

#### 1. Container won't start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs web
docker-compose -f docker-compose.prod.yml logs db

# Check container status
docker-compose -f docker-compose.prod.yml ps
```

#### 2. Database connection errors

```bash
# Verify database is running
docker-compose -f docker-compose.prod.yml exec db pg_isready -U $LEARN_OPS_USER

# Check environment variables
docker-compose -f docker-compose.prod.yml exec web env | grep LEARN_OPS
```

#### 3. Static files not loading

```bash
# Recollect static files
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Check nginx static file path
ls -la /var/www/learning.nss.team/static/
```

#### 4. GitHub Actions deployment fails

- Verify SSH key is correct in GitHub Secrets
- Check droplet is accessible: `ssh deploy@your-droplet-ip`
- Review GitHub Actions logs for specific error
- Ensure deploy user has Docker permissions: `groups deploy`

#### 5. SSL certificate issues

```bash
# Renew certificate
certbot renew --force-renewal

# Check certificate status
certbot certificates
```

### Logs Location

- **Nginx logs:** `/var/log/nginx/learning-api-*.log`
- **Application logs:** `/var/www/learning-platform-api/logs/`
- **Docker logs:** `docker-compose logs [service]`
- **System logs:** `/var/log/syslog`

### Health Checks

```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Test API endpoint
curl https://api.learning.nss.team/health

# Check nginx status
systemctl status nginx

# Check disk space
df -h

# Check memory usage
free -h

# Check Docker resource usage
docker stats
```

---

## Rollback Strategy

### Quick Rollback

If deployment fails, rollback to previous version:

```bash
ssh deploy@your-droplet-ip
cd /var/www/learning-platform-api

# Find previous commit
git log --oneline -n 5

# Rollback to previous commit
git reset --hard <previous-commit-hash>

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Database Rollback

If migrations cause issues:

```bash
# Restore from backup
gunzip < /var/backups/learning-platform/db_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T db \
  psql -U $LEARN_OPS_USER $LEARN_OPS_DB
```

### Automated Rollback in GitHub Actions

Add to workflow (optional):

```yaml
      - name: Rollback on failure
        if: failure()
        env:
          DROPLET_HOST: ${{ secrets.DROPLET_HOST }}
          DROPLET_USER: ${{ secrets.DROPLET_USER }}
        run: |
          ssh $DROPLET_USER@$DROPLET_HOST << 'ENDSSH'
            cd /var/www/learning-platform-api
            git reset --hard HEAD~1
            docker-compose -f docker-compose.prod.yml up -d
          ENDSSH
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing locally
- [ ] Environment variables documented
- [ ] Database migrations tested
- [ ] Static files collected successfully
- [ ] Docker build succeeds locally
- [ ] Code reviewed and approved

### Initial Setup

- [ ] Droplet created and configured
- [ ] SSH keys set up
- [ ] Nginx installed and configured
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] GitHub Secrets configured
- [ ] Repository cloned on droplet
- [ ] `.env` file created on server
- [ ] Initial deployment successful

### Post-Deployment

- [ ] Health check endpoint responding
- [ ] API endpoints accessible
- [ ] Static files loading correctly
- [ ] Database migrations applied
- [ ] Admin panel accessible
- [ ] GitHub OAuth working
- [ ] Logs being written correctly
- [ ] Monitoring dashboards accessible (if enabled)
- [ ] Backup script configured and tested

### Ongoing Maintenance

- [ ] Monitor application logs regularly
- [ ] Review security updates weekly
- [ ] Test backup restoration monthly
- [ ] Rotate secrets quarterly
- [ ] Review and optimize database quarterly
- [ ] Update dependencies regularly

---

## Additional Resources

- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Digital Ocean Docker Documentation](https://docs.digitalocean.com/products/droplets/how-to/use-docker/)
- [Nginx Configuration Best Practices](https://www.nginx.com/blog/nginx-best-practices/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

---

## Support and Contacts

- **Repository:** [learning-platform-api](https://github.com/your-org/learning-platform-api)
- **Documentation:** [`README.md`](../README.md)
- **Related Projects:** Frontend deployment at `learning.nss.team`

---

*Last Updated: 2026-02-12*
