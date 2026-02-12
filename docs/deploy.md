# Digital Ocean Deployment Plan

## Overview

This document outlines the deployment strategy for the Learning Platform API to Digital Ocean using GitHub Actions for automated deployment.

**Project:** Django REST API with PostgreSQL database
**Deployment Target:** Dedicated Digital Ocean Droplet (API + Database)
**Deployment Method:** GitHub Actions (automated on push to main)
**Database:** PostgreSQL in Docker container (same droplet as API)
**Web Server:** Gunicorn + Nginx
**Architecture:** Dedicated API droplet separate from frontend

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Droplet Setup](#droplet-setup)
4. [Environment Configuration](#environment-configuration)
5. [GitHub Actions Workflow](#github-actions-workflow)
6. [Deployment Process](#deployment-process)
7. [Monitoring Setup (Optional)](#monitoring-setup-optional)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting](#troubleshooting)
10. [Rollback Strategy](#rollback-strategy)
11. [Scaling Considerations](#scaling-considerations)

---

## Architecture Overview

### Chosen Architecture: Dedicated API Droplet

This deployment uses a **dedicated droplet for the API and database**, separate from the frontend application.

```
┌─────────────────────────────────────────┐
│   Frontend Droplet (Existing)          │
│   - React/Next.js Application           │
│   - learning.nss.team                   │
└─────────────────┬───────────────────────┘
                  │
                  │ HTTPS API Calls
                  │
┌─────────────────▼───────────────────────┐
│   API Droplet (New)                     │
│   ┌─────────────────────────────────┐   │
│   │  Nginx (Reverse Proxy + SSL)    │   │
│   └──────────────┬──────────────────┘   │
│                  │                       │
│   ┌──────────────▼──────────────────┐   │
│   │  Django API (Gunicorn)          │   │
│   │  - Port 8000                     │   │
│   │  - Docker Container              │   │
│   └──────────────┬──────────────────┘   │
│                  │                       │
│   ┌──────────────▼──────────────────┐   │
│   │  PostgreSQL Database            │   │
│   │  - Docker Container              │   │
│   │  - Persistent Volume             │   │
│   └─────────────────────────────────┘   │
│                                          │
│   Optional:                              │
│   ┌─────────────────────────────────┐   │
│   │  Prometheus + Grafana           │   │
│   │  - Monitoring Stack              │   │
│   └─────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

### Why This Architecture?

**✅ Advantages:**
- **Resource Isolation:** API and frontend don't compete for resources
- **Independent Scaling:** Scale API independently based on load
- **Clearer Separation:** Easier to debug and maintain
- **Cost-Effective:** Database on same droplet as API (no network latency)
- **Simple Management:** All API components in one place
- **Easy Migration Path:** Can move to managed database later if needed

**📊 Recommended Droplet Specifications:**

| Component | Minimum | Recommended | High Traffic |
|-----------|---------|-------------|--------------|
| RAM | 2GB | 4GB | 8GB |
| vCPUs | 1 | 2 | 4 |
| Storage | 50GB | 80GB | 160GB |
| Monthly Cost | ~$12 | ~$24 | ~$48 |

**Start with 2GB RAM droplet** and monitor resource usage. Digital Ocean allows easy upgrades without downtime.

### Database Hosting Decision

**Running PostgreSQL in Docker on the API droplet is ideal for:**
- ✅ Small to medium traffic applications (< 1000 concurrent users)
- ✅ Cost-conscious deployments
- ✅ Applications where database and API are tightly coupled
- ✅ Development and staging environments

**Consider migrating to a separate database when:**
- ⚠️ Consistent high CPU usage (>80%) on the droplet
- ⚠️ Database queries slowing down API responses
- ⚠️ Need for high availability (99.99% uptime)
- ⚠️ Database size exceeds 50GB
- ⚠️ Multiple applications need to access the same database

See [Scaling Considerations](#scaling-considerations) for migration guidance.

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

**Note:** The `.env` file is automatically created and updated by the GitHub Actions workflow during deployment. You don't need to manually create it.

The workflow uses the GitHub Secrets configured above to generate the `.env` file on the droplet with proper permissions. This ensures:
- ✅ Secrets are never committed to the repository
- ✅ Environment variables stay in sync with GitHub Secrets
- ✅ No manual file creation needed on the server
- ✅ Proper file permissions are automatically set

If you need to update environment variables, simply update the GitHub Secrets and redeploy.

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

      - name: Create environment file
        env:
          DROPLET_HOST: ${{ secrets.DROPLET_HOST }}
          DROPLET_USER: ${{ secrets.DROPLET_USER }}
        run: |
          ssh $DROPLET_USER@$DROPLET_HOST << 'ENDSSH'
            set -e
            
            # Create .env file with all required environment variables
            cat > /var/www/learning-platform-api/.env << 'EOF'
          # Database Configuration
          LEARN_OPS_DB=${{ secrets.LEARN_OPS_DB }}
          LEARN_OPS_USER=${{ secrets.LEARN_OPS_USER }}
          LEARN_OPS_PASSWORD=${{ secrets.LEARN_OPS_PASSWORD }}
          LEARN_OPS_HOST=db
          LEARN_OPS_PORT=${{ secrets.LEARN_OPS_PORT }}

          # Django Configuration
          LEARN_OPS_DJANGO_SECRET_KEY=${{ secrets.LEARN_OPS_DJANGO_SECRET_KEY }}
          LEARN_OPS_ALLOWED_HOSTS=${{ secrets.LEARN_OPS_ALLOWED_HOSTS }}
          DEBUG=False
          DEVELOPMENT_MODE=False

          # GitHub OAuth
          LEARN_OPS_CLIENT_ID=${{ secrets.LEARN_OPS_CLIENT_ID }}
          LEARN_OPS_SECRET_KEY=${{ secrets.LEARN_OPS_SECRET_KEY }}
          LEARNING_GITHUB_CALLBACK=${{ secrets.LEARNING_GITHUB_CALLBACK }}

          # Superuser
          LEARN_OPS_SUPERUSER_NAME=${{ secrets.LEARN_OPS_SUPERUSER_NAME }}
          LEARN_OPS_SUPERUSER_PASSWORD=${{ secrets.LEARN_OPS_SUPERUSER_PASSWORD }}

          # Python
          PYTHONUNBUFFERED=1
          PYTHONDONTWRITEBYTECODE=1
          EOF
            
            # Set proper permissions
            chmod 600 /var/www/learning-platform-api/.env
            chown deploy:deploy /var/www/learning-platform-api/.env
            
            echo "✅ Environment file created successfully"
          ENDSSH

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

## Scaling Considerations

### When to Scale Up Your Droplet

Monitor these metrics to determine when to upgrade:

**CPU Usage:**
```bash
# Check current CPU usage
top
# or
docker stats
```
- **Action needed if:** Consistently >80% CPU usage
- **Solution:** Upgrade to next droplet size (e.g., 2GB → 4GB)

**Memory Usage:**
```bash
# Check memory usage
free -h
docker stats
```
- **Action needed if:** Consistently >85% memory usage or frequent swapping
- **Solution:** Upgrade RAM (e.g., 2GB → 4GB → 8GB)

**Database Performance:**
```bash
# Check database connections
docker-compose exec db psql -U $LEARN_OPS_USER -d $LEARN_OPS_DB -c "SELECT count(*) FROM pg_stat_activity;"

# Check slow queries (add to Django settings)
# Enable query logging in PostgreSQL
```
- **Action needed if:** Query response times >500ms consistently
- **Solution:** Optimize queries first, then consider database scaling

### Migration Path: Database to Separate Infrastructure

If you outgrow the single-droplet setup, here's the migration path:

#### Option 1: Digital Ocean Managed Database (Recommended)

**Advantages:**
- Automated backups and point-in-time recovery
- Automatic failover and high availability
- Automated updates and security patches
- Connection pooling built-in
- Easy scaling

**Migration Steps:**

1. **Create Managed Database:**
   - Go to Digital Ocean Dashboard → Databases
   - Create PostgreSQL cluster (start with Basic plan)
   - Note connection details

2. **Backup Current Database:**
   ```bash
   docker-compose exec db pg_dump -U $LEARN_OPS_USER $LEARN_OPS_DB > backup.sql
   ```

3. **Restore to Managed Database:**
   ```bash
   psql -h managed-db-host -U doadmin -d defaultdb < backup.sql
   ```

4. **Update Environment Variables:**
   ```bash
   LEARN_OPS_HOST=managed-db-host.db.ondigitalocean.com
   LEARN_OPS_PORT=25060
   LEARN_OPS_USER=doadmin
   # Update password and SSL settings
   ```

5. **Update docker-compose.prod.yml:**
   - Remove `db` service
   - Update `web` service to use external database
   - Add SSL connection parameters

6. **Test and Deploy:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

#### Option 2: Dedicated Database Droplet

**When to use:** Need more control than managed database offers

**Migration Steps:**

1. Create new droplet for database
2. Install PostgreSQL directly (not in Docker for better performance)
3. Configure PostgreSQL for remote connections
4. Set up firewall rules (only allow API droplet IP)
5. Migrate data using pg_dump/pg_restore
6. Update API droplet environment variables

### Horizontal Scaling (Multiple API Instances)

When a single API droplet isn't enough:

1. **Add Load Balancer:**
   - Digital Ocean Load Balancer
   - Distribute traffic across multiple API droplets

2. **Deploy Multiple API Droplets:**
   - Clone your API droplet
   - All connect to same database
   - Load balancer distributes requests

3. **Session Management:**
   - Use database-backed sessions (already configured in Django)
   - Or use Redis for session storage

4. **Static Files:**
   - Move to Digital Ocean Spaces (S3-compatible)
   - Update `STATIC_URL` in settings

### Cost Optimization Tips

**Current Setup (Single Droplet):**
- 2GB Droplet: ~$12/month
- Backups: ~$2.40/month (20% of droplet cost)
- **Total: ~$14.40/month**

**With Managed Database:**
- 2GB API Droplet: ~$12/month
- Basic Managed DB: ~$15/month
- **Total: ~$27/month**

**Cost Saving Strategies:**
- Use snapshots instead of automated backups (manual, but cheaper)
- Start with smallest droplet and scale up only when needed
- Monitor with Prometheus to identify optimization opportunities
- Optimize database queries before scaling hardware
- Use CDN for static files (Digital Ocean Spaces + CDN)

### Performance Monitoring Checklist

Set up alerts for:
- [ ] CPU usage >80% for 5 minutes
- [ ] Memory usage >85%
- [ ] Disk usage >80%
- [ ] API response time >1 second
- [ ] Database connection pool exhaustion
- [ ] Error rate >1%

Use Prometheus + Grafana (optional monitoring setup) to track these metrics automatically.

---

*Last Updated: 2026-02-12*
