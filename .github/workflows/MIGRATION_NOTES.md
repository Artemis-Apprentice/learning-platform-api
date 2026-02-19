# GitHub Actions Migration Notes

## Date: 2026-02-19

## Summary
Migrated from self-hosted runner + Pipenv deployment to GitHub-hosted runner + Docker deployment.

## Removed Workflows

### 1. `main.yml` - Digital Ocean Build and Deploy
- **Purpose:** Deploy application using self-hosted runner
- **Approach:** Pipenv + systemd service restart
- **Trigger:** Push to main branch
- **Replaced by:** `deploy.yml` (Docker-based deployment)

### 2. `collectstatic.yml` - Collect Django static files
- **Purpose:** Manually collect static files
- **Approach:** Pipenv command on self-hosted runner
- **Trigger:** Manual (workflow_dispatch)
- **Replaced by:** Automatic collectstatic in `deploy.yml` deployment step

### 3. `seed.yml` - Run fixtures for data
- **Purpose:** Seed database with fixtures
- **Approach:** Pipenv command on self-hosted runner
- **Trigger:** Manual (workflow_dispatch)
- **Replacement:** Can be run manually via SSH:
  ```bash
  ssh deploy@your-droplet-ip
  cd /var/www/learning-platform-api
  docker-compose -f docker-compose.prod.yml exec web python manage.py loaddata fixtures/complete_backup.json
  ```

## New Workflow

### `deploy.yml` - Deploy to Digital Ocean
- **Purpose:** Complete deployment pipeline
- **Approach:** SSH-based Docker Compose deployment
- **Trigger:** Push to main branch + manual
- **Features:**
  - Automated .env file creation from GitHub Secrets
  - Docker image building
  - Database migrations
  - Static file collection
  - Health check verification
  - Automatic cleanup

## Migration Checklist

- [x] Create `docker-compose.prod.yml`
- [x] Create new `deploy.yml` workflow
- [x] Remove old workflows (main.yml, collectstatic.yml, seed.yml)
- [ ] Configure GitHub Secrets (see docs/deploy.md)
- [ ] Setup new droplet with Docker
- [ ] Test deployment with new workflow
- [ ] Decommission self-hosted runner
- [ ] Remove systemd service from old server

## Manual Operations

Some operations that were automated workflows are now manual:

### Collect Static Files (if needed separately)
```bash
ssh deploy@your-droplet-ip
cd /var/www/learning-platform-api
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### Seed Database
```bash
ssh deploy@your-droplet-ip
cd /var/www/learning-platform-api
docker-compose -f docker-compose.prod.yml exec web python manage.py loaddata fixtures/complete_backup.json
```

### Run Migrations (if needed separately)
```bash
ssh deploy@your-droplet-ip
cd /var/www/learning-platform-api
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

## Benefits of New Approach

1. **No self-hosted runner maintenance** - Uses GitHub-hosted runners
2. **Containerized deployment** - Consistent environment across dev/prod
3. **Automated environment management** - .env file created from secrets
4. **Better security** - Secrets managed in GitHub, not on server
5. **Zero-downtime deployments** - Docker container orchestration
6. **Health checks** - Automatic verification after deployment
7. **Easier rollback** - Git-based version control

## Documentation

See `docs/deploy.md` for complete deployment guide.
