
# Docker Configuration Guide

This project now has separate Docker configurations for different environments:


## Configuration Files

### Development Environment

- **File**: `docker-compose.dev.yml`
- **Dockerfile**: `Dockerfile.dev`
- **Purpose**: Local development with live code reloading

### Production Environment

- **File**: `docker-compose.apps.yml` (renamed from production)
- **Dockerfile**: `Dockerfile.prod`
- **Purpose**: Production deployment with optimized performance

### Services Only

- **File**: `docker-compose.services.yml`
- **Purpose**: Run only PostgreSQL with pgvector and supporting services


## Usage

### Development Mode

Start development environment with live reloading:

```bash
# Start all services including database
docker-compose -f docker/docker-compose.dev.yml up -d

# Or start only the app (if services are already running)
docker-compose -f docker/docker-compose.dev.yml up -d app

# View logs
docker-compose -f docker/docker-compose.dev.yml logs -f app

# Stop development environment
docker-compose -f docker/docker-compose.dev.yml down
```


### Production Mode

Start production environment:

```bash
# Start services first
docker-compose -f docker/docker-compose.services.yml up -d

# Start production app
docker-compose -f docker/docker-compose.apps.yml up -d

# Stop production environment
docker-compose -f docker/docker-compose.apps.yml down
docker-compose -f docker/docker-compose.services.yml down
```


### Services Only

Start only database and supporting services:

```bash
# Start services
docker-compose -f docker/docker-compose.services.yml up -d

# Stop services
docker-compose -f docker/docker-compose.services.yml down
```


## Key Differences

### Development Configuration

- **Live Code Reloading**: Source code is mounted as volumes, changes reflect immediately
- **Flask Development Server**: Uses Flask's built-in development server with auto-reload
- **Debug Mode**: Enabled for better error messages and debugging
- **Separate Volumes**: Development uses separate database volumes to avoid conflicts
- **Test Mode**: Enables mock mode for faster development

### Production Configuration

- **Optimized Build**: Code is copied into container, no live mounting
- **Gunicorn Server**: Uses production-grade WSGI server with multiple workers
- **Security**: Files are set to read-only for security
- **Performance**: Optimized for production workloads


## Environment Variables

The development environment automatically sets:

- `FLASK_ENV=development`
- `FLASK_DEBUG=1`
- `TEST_MODE=True`

The production environment sets:

- `FLASK_ENV=production`


## Network Configuration

All configurations use the `combiphar-network` bridge network for inter-service communication.


## Volume Management

### Development Volumes

- `db_data_dev`: Development PostgreSQL data with pgvector
- `pgadmin_data_dev`: Development PgAdmin configuration
- `app_cache`, `app_app_cache`: Python cache volumes

### Production Volumes

- `db_data`: Production PostgreSQL data with pgvector
- `pgadmin_data`: Production PgAdmin configuration


## Tips for Development

1. **Quick Start for Development**:

   ```bash
   docker-compose -f docker/docker-compose.dev.yml up -d
   ```

2. **Rebuild After Dependency Changes**:

   ```bash
   docker-compose -f docker/docker-compose.dev.yml up --build -d
   ```

3. **View Application Logs**:

   ```bash
   docker-compose -f docker/docker-compose.dev.yml logs -f app
   ```

4. **Access Services**:

   - Application: [http://localhost:8070](http://localhost:8070)
   - PostgreSQL: localhost:5432
   - PgAdmin: [http://localhost:5050](http://localhost:5050)

5. **Cleanup Everything**:

   ```bash
   docker-compose -f docker/docker-compose.dev.yml down -v
   ```
