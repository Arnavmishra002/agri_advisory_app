# Docker Setup for Agri-Advisory App

This document provides instructions for running the Agri-Advisory App using Docker and Docker Compose.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

## Quick Start

### Development Environment

1. **Clone the repository and navigate to the project directory:**
   ```bash
   cd agri_advisory_app
   ```

2. **Start the development environment:**
   ```bash
   docker-compose up --build
   ```

3. **Run database migrations:**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

4. **Create a superuser (optional):**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

5. **Access the application:**
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/schema/swagger-ui/

### Production Environment

1. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your production values
   ```

2. **Start the production environment:**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

3. **Run database migrations:**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
   ```

4. **Collect static files:**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
   ```

## Services

### Web Application (`web`)
- **Port:** 8000
- **Description:** Django application server
- **Dependencies:** Database, Redis

### Database (`db`)
- **Port:** 5432
- **Description:** PostgreSQL database
- **Environment Variables:**
  - `POSTGRES_DB`: Database name
  - `POSTGRES_USER`: Database user
  - `POSTGRES_PASSWORD`: Database password

### Redis (`redis`)
- **Port:** 6379
- **Description:** Redis cache and message broker for Celery
- **Usage:** Session storage, caching, Celery task queue

### Celery Worker (`celery`)
- **Description:** Background task processor
- **Dependencies:** Redis, Database
- **Tasks:** Weather updates, market data updates, notifications

### Celery Beat (`celery-beat`)
- **Description:** Periodic task scheduler
- **Dependencies:** Redis, Database
- **Schedule:** Hourly weather updates, daily market updates

### Nginx (`nginx`) - Production Only
- **Ports:** 80, 443
- **Description:** Reverse proxy and static file server
- **Features:** Load balancing, SSL termination, static file serving

## Environment Variables

### Required Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | - |
| `POSTGRES_PASSWORD` | Database password | - |
| `SENTRY_DSN` | Sentry error tracking DSN | - |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | 1 |
| `ALLOWED_HOSTS` | Allowed hosts | localhost,127.0.0.1 |
| `WEATHER_API_KEY` | Weather API key | - |
| `MARKET_API_KEY` | Market data API key | - |
| `SMS_API_KEY` | SMS service API key | - |
| `IVR_API_KEY` | IVR service API key | - |

## Commands

### Development Commands

```bash
# Start all services
docker-compose up

# Start services in background
docker-compose up -d

# Rebuild and start services
docker-compose up --build

# Stop all services
docker-compose down

# View logs
docker-compose logs

# View logs for specific service
docker-compose logs web

# Execute commands in running container
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic

# Access database shell
docker-compose exec db psql -U postgres -d agri_advisory
```

### Production Commands

```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# Stop production environment
docker-compose -f docker-compose.prod.yml down

# View production logs
docker-compose -f docker-compose.prod.yml logs

# Scale services
docker-compose -f docker-compose.prod.yml up --scale celery=3
```

## Troubleshooting

### Common Issues

1. **Port conflicts:**
   - Ensure ports 8000, 5432, 6379, 80, 443 are not in use
   - Change ports in docker-compose.yml if needed

2. **Database connection issues:**
   - Check if PostgreSQL container is running
   - Verify database credentials in environment variables

3. **Redis connection issues:**
   - Check if Redis container is running
   - Verify Redis URL in environment variables

4. **Permission issues:**
   - Ensure Docker has proper permissions
   - Check file ownership in volumes

### Logs and Debugging

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs celery
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f web

# Check container status
docker-compose ps

# Inspect container
docker-compose exec web bash
```

## Data Persistence

- **Database data:** Stored in `postgres_data` volume
- **Static files:** Stored in `static_volume` volume
- **Media files:** Stored in `media_volume` volume

## Security Considerations

1. **Change default passwords** in production
2. **Use environment variables** for sensitive data
3. **Enable SSL/TLS** in production
4. **Restrict database access** to application containers only
5. **Use secrets management** for production deployments

## Scaling

### Horizontal Scaling

```bash
# Scale Celery workers
docker-compose -f docker-compose.prod.yml up --scale celery=5

# Scale web application (with load balancer)
docker-compose -f docker-compose.prod.yml up --scale web=3
```

### Vertical Scaling

- Increase memory and CPU limits in docker-compose.yml
- Use resource constraints for production deployments

## Monitoring

### Health Checks

```bash
# Check service health
docker-compose ps

# Check application health
curl http://localhost:8000/health/

# Check database connectivity
docker-compose exec web python manage.py dbshell
```

### Log Monitoring

- Use centralized logging solutions (ELK stack, Fluentd)
- Monitor application logs for errors
- Set up alerts for critical failures

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec db pg_dump -U postgres agri_advisory > backup.sql

# Restore backup
docker-compose exec -T db psql -U postgres agri_advisory < backup.sql
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v agri_advisory_app_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```
