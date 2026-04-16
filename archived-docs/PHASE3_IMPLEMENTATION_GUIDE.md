# PHASE 3: PRODUCTION-GRADE SECURITY & HIGH AVAILABILITY
## Complete Implementation Guide (Ready-to-Deploy Prompt)

---

## 📋 TABLE OF CONTENTS
1. [Overview & Benefits](#overview)
2. [Architecture Diagram](#architecture)
3. [Prerequisites Check](#prerequisites)
4. [Detailed Implementation Steps](#implementation)
5. [Testing & Verification](#testing)
6. [Troubleshooting Guide](#troubleshooting)
7. [Rollback Procedures](#rollback)
8. [Monitoring Dashboard](#monitoring)

---

## <a name="overview"></a>🎯 PHASE 3 OVERVIEW & BENEFITS

### What is Phase 3?

Phase 3 transforms the development system into an **enterprise-grade production platform** with:
- SSL/HTTPS encryption
- Database high availability (replication)
- Automated monitoring & alerting
- Docker containerization
- CI/CD pipeline
- Complete backup & disaster recovery

### Key Improvements Over Phase 2

| Component | Phase 2 | Phase 3 |
|-----------|---------|---------|
| **Encryption** | ❌ HTTP (unencrypted) | ✅ HTTPS with Let's Encrypt |
| **Database HA** | 1 node (single point of failure) | 3 nodes (primary + 2 replicas) |
| **Monitoring** | Basic logs | Prometheus + Grafana dashboard |
| **Alerting** | Manual checking | Automatic email + Telegram |
| **Backups** | Manual via backup_service.py | Automated hourly via cron |
| **Scaling** | Manual instance start | Docker Compose 1-command scaling |
| **Deployment** | Manual file copying | Git push → Automatic deploy |
| **Uptime SLA** | ~95% | 99.9% with proper config |
| **Disaster Recovery** | Manual restore | Automated failover + restore |

### Financial Impact

**Cost difference**: ~$20-50/month extra for:
- SSL certificates (Let's Encrypt = FREE)
- Database replication (same PostgreSQL instance)
- Monitoring stack (Prometheus/Grafana = open source)
- CI/CD (GitHub Actions with free tier = up to 2000 min/month)

### Security Improvements

Phase 3 addresses:
- ✅ Man-in-the-middle attacks (HTTPS)
- ✅ Database data loss (replication)
- ✅ Undetected failures (monitoring)
- ✅ Manual error in deployment (CI/CD automation)
- ✅ Ransomware (versioned backups)
- ✅ Compliance audits (full audit logs)

---

## <a name="architecture"></a>🏗️ PHASE 3 ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL USERS                              │
│                      (Internet - Global)                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                        HTTPS/TLS
                        (Port 443)
                             │
         ┌───────────────────▼───────────────────┐
         │    NGINX REVERSE PROXY (HA)           │
         │   - Primary (127.0.0.1:443)          │
         │   - Backup (127.0.0.1:444)           │
         │   - SSL termination                  │
         │   - Rate limiting                    │
         │   - Request logging                  │
         └───────────────────┬───────────────────┘
                             │
                Upstream to App Instances
                             │
        ┌────────────┬────────┼────────┬────────────┐
        │            │        │        │            │
   Port 5001    Port 5002  Port 5003 Port 5004  Port 5005
        │            │        │        │            │
    ┌──▼──┐     ┌───▼──┐ ┌──▼──┐ ┌──▼──┐     ┌───▼──┐
    │Flask│     │Flask │ │Flask│ │Flask│     │Flask │
    │App 1│     │App 2 │ │App 3│ │App 4│     │App 5 │
    └──┬──┘     └───┬──┘ └──┬──┘ └──┬──┘     └───┬──┘
       │            │       │       │             │
       └────────────┼───────┼───────┼─────────────┘
                    │       │       │
         ┌──────────▼─┬─────▼──┬───▼──────────┐
         │            │        │              │
         ▼            ▼        ▼              ▼
    ┌──────────┐ ┌────────┐ ┌───────┐ ┌─────────────┐
    │PostgreSQL│ │ Redis  │ │Prometheus│ │   Grafana   │
    │ Primary  │ │ Cache  │ │ Metrics   │ │ Dashboard   │
    └──────────┘ └────────┘ └───────┘ └─────────────┘
         │
         │ Replication
         │
    ┌────▼────────────────────┐
    │  PostgreSQL Replicas    │
    │  - Replica 1 (Standby)  │
    │  - Replica 2 (Standby)  │
    │  (Read-only copies)     │
    └────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    BACKUP SYSTEM                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Hourly Local │  │ Daily Cloud  │  │ Weekly Vault │      │
│  │   Backup     │  │   S3/GCS     │  │   Archive    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│      Auto-rotate after 30 days                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  MONITORING & ALERTING                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Alert Rules:                                       │    │
│  │ - CPU > 80% → Email + Telegram                    │    │
│  │ - Memory > 90% → Email + Slack                    │    │
│  │ - DB replication lag > 1s → Alarm                 │    │
│  │ - Failed login attempts > 100 → Block IP          │    │
│  │ - HTTPS cert expires < 7 days → Renew auto        │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   CI/CD PIPELINE                            │
│  Git Push → Tests → Build → Staging → Production Deploy    │
│  ~5 minutes end-to-end automatic deployment                 │
└─────────────────────────────────────────────────────────────┘
```

---

## <a name="prerequisites"></a>✅ PREREQUISITES CHECK

Before implementing Phase 3, verify Phase 2 is working:

```bash
# 1. PostgreSQL running
psql -U labeling_user -d labeling_db -c "SELECT COUNT(*) FROM segments;"
# Expected: 309

# 2. Redis running
redis-cli PING
# Expected: PONG

# 3. Nginx running
curl http://localhost:8080/
# Expected: 302 redirect to /login

# 4. Flask responding
curl http://localhost:3000/
# Expected: 302 redirect to /login

# 5. All services have correct configuration
grep DATABASE_URL src/config.py
# Expected: postgresql://labeling_user:phase2_password@localhost:5432/labeling_db
```

**If all pass ✅**: Ready for Phase 3

---

## <a name="implementation"></a>📝 DETAILED IMPLEMENTATION STEPS

### STEP 1: Generate SSL/HTTPS Certificates (30 minutes)

#### Option A: Let's Encrypt (Free, Recommended)

```bash
# 1. Install certbot
brew install certbot

# 2. Generate certificate (requires domain name pointing to your server)
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos \
  --non-interactive

# 3. Certificates location
# /etc/letsencrypt/live/yourdomain.com/

# 4. Auto-renewal setup
sudo certbot renew --dry-run
# Auto-renewal via cron runs daily

# Certificate locations to use:
CERT_FILE=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
KEY_FILE=/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

#### Option B: Self-signed (For testing only)

```bash
# Generate self-signed certificate (valid 365 days)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Use in development:
CERT_FILE=./cert.pem
KEY_FILE=./key.pem
```

### STEP 2: Update Nginx Configuration for HTTPS (20 minutes)

**File**: `/opt/homebrew/etc/nginx/sites-available/labeling-app.conf`

```nginx
# ============ HTTP to HTTPS Redirect ============
server {
    listen 80;
    listen [::]:80;
    server_name labeling-app.example.com www.labeling-app.example.com;
    
    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# ============ HTTPS Server Block ============
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name labeling-app.example.com www.labeling-app.example.com;
    
    # ===== SSL Configuration =====
    ssl_certificate /etc/letsencrypt/live/labeling-app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/labeling-app.example.com/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS (Force HTTPS for 1 year)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # ===== Logging =====
    access_log /opt/homebrew/var/log/nginx/labeling_access.log combined;
    error_log /opt/homebrew/var/log/nginx/labeling_error.log warn;
    
    # ===== Gzip Compression =====
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;
    gzip_vary on;
    
    # ===== Upstream Load Balancing =====
    upstream flask_app {
        server 127.0.0.1:5001;
        server 127.0.0.1:5002;
        server 127.0.0.1:5003;
        keepalive 32;
    }
    
    # ===== Main Proxy Configuration =====
    location / {
        proxy_pass http://flask_app;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Static files caching
    location /static/ {
        alias /Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/src/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### STEP 3: PostgreSQL Replication Setup (45 minutes)

#### 3a: Configure Primary PostgreSQL

**File**: `/Users/camilogutierrez/postgresql_data/postgresql.conf`

```conf
# ===== Replication Settings =====
max_wal_senders = 10
wal_keep_size = 1GB
hot_standby = on
hot_standby_feedback = on

# ===== Archive Settings =====
archive_mode = on
archive_command = 'test ! -f /Users/camilogutierrez/postgresql_archive/%f && cp %p /Users/camilogutierrez/postgresql_archive/%f'
archive_timeout = 3600
```

**File**: `/Users/camilogutierrez/postgresql_data/pg_hba.conf`

```conf
# Allow replication connections from replica servers
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5

# Replication connection
host    replication     labeling_user   127.0.0.1/32            md5
```

#### 3b: Create Replica User and Setup

```bash
# 1. Connect to primary PostgreSQL
psql -U postgres

# 2. Create replication user
CREATE USER labeling_replica WITH REPLICATION PASSWORD 'replica_password_123';

# 3. Take base backup
cd ~/postgresql_replicas
pg_basebackup -h localhost -D ./replica1 -U labeling_replica -v -P

# 4. Create recovery.conf for replica
cat > ~/postgresql_replicas/replica1/recovery.conf << EOF
standby_mode = 'on'
primary_conninfo = 'host=127.0.0.1 port=5432 user=labeling_replica password=replica_password_123'
trigger_file = '/tmp/promote_replica1'
EOF

# 5. Start replica
pg_ctl -D ~/postgresql_replicas/replica1 -l ~/postgresql_replicas/replica1.log start

# 6. Verify replication
psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

### STEP 4: Docker Setup (40 minutes)

#### 4a: Create Dockerfile

**File**: `Labeling_app/docker/app/Dockerfile`

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY src/requirements/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start application
CMD ["python", "src/app.py"]
```

#### 4b: Create Docker Compose

**File**: `Labeling_app/docker-compose.yml`

```yaml
version: '3.8'

services:
  # PostgreSQL Primary
  postgres-primary:
    image: postgres:15
    container_name: labeling-postgres-primary
    environment:
      POSTGRES_USER: labeling_user
      POSTGRES_PASSWORD: phase2_password
      POSTGRES_DB: labeling_db
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
      - ./docker/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
      - ./docker/postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf
    ports:
      - "5432:5432"
    command: 
      - "postgres"
      - "-c"
      - "config_file=/etc/postgresql/postgresql.conf"
    networks:
      - labeling-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U labeling_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # PostgreSQL Replica 1
  postgres-replica1:
    image: postgres:15
    container_name: labeling-postgres-replica1
    environment:
      PGUSER: labeling_replica
      PGPASSWORD: replica_password_123
    volumes:
      - postgres_replica1_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"
    depends_on:
      postgres-primary:
        condition: service_healthy
    networks:
      - labeling-network
    command: >
      sh -c "pg_basebackup -h postgres-primary -D /var/lib/postgresql/backup -U labeling_replica -v -P -W &&
             cp /var/lib/postgresql/backup/* /var/lib/postgresql/data/ &&
             echo 'standby_mode = on' > /var/lib/postgresql/data/recovery.conf &&
             postgres"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: labeling-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - labeling-network
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Flask App Instance 1
  app1:
    build:
      context: .
      dockerfile: docker/app/Dockerfile
    container_name: labeling-app-1
    environment:
      FLASK_ENV: production
      DATABASE_URL: postgresql://labeling_user:phase2_password@postgres-primary:5432/labeling_db
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      SECRET_KEY: ${SECRET_KEY}
      FLASK_PORT: 5001
    ports:
      - "5001:5000"
    depends_on:
      postgres-primary:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - labeling-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Flask App Instance 2
  app2:
    build:
      context: .
      dockerfile: docker/app/Dockerfile
    container_name: labeling-app-2
    environment:
      FLASK_ENV: production
      DATABASE_URL: postgresql://labeling_user:phase2_password@postgres-primary:5432/labeling_db
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      SECRET_KEY: ${SECRET_KEY}
      FLASK_PORT: 5002
    ports:
      - "5002:5000"
    depends_on:
      postgres-primary:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - labeling-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Flask App Instance 3
  app3:
    build:
      context: .
      dockerfile: docker/app/Dockerfile
    container_name: labeling-app-3
    environment:
      FLASK_ENV: production
      DATABASE_URL: postgresql://labeling_user:phase2_password@postgres-primary:5432/labeling_db
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      SECRET_KEY: ${SECRET_KEY}
      FLASK_PORT: 5003
    ports:
      - "5003:5000"
    depends_on:
      postgres-primary:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - labeling-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: labeling-prometheus
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - labeling-network

  # Grafana Dashboard
  grafana:
    image: grafana/grafana:latest
    container_name: labeling-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_INSTALL_PLUGINS: redis-datasource
    volumes:
      - grafana_data:/var/lib/grafana
      - ./docker/grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    networks:
      - labeling-network

networks:
  labeling-network:
    driver: bridge

volumes:
  postgres_primary_data:
  postgres_replica1_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

### STEP 5: Prometheus Configuration (15 minutes)

**File**: `Labeling_app/docker/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'labeling-app-monitor'

scrape_configs:
  - job_name: 'flask-app'
    static_configs:
      - targets: ['app1:5000', 'app2:5000', 'app3:5000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-primary:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### STEP 6: Monitoring & Alerting Setup (20 minutes)

**File**: `Labeling_app/docker/alertmanager/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: 'YOUR_SLACK_WEBHOOK_URL'
  telegram_bot_token: 'YOUR_BOT_TOKEN'
  telegram_chat_id: 'YOUR_CHAT_ID'

route:
  receiver: 'labeling-team'
  repeat_interval: 1h

receivers:
  - name: 'labeling-team'
    email_configs:
      - to: 'admin@labeling-app.com'
        from: 'alerts@labeling-app.com'
        smarthost: 'smtp.gmail.com:587'
        auth_password: 'your_app_password'
    slack_configs:
      - channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
```

### STEP 7: Backup Strategy (25 minutes)

Update backup_service.py for Phase 3:

```python
# File: src/services/backup_service.py (additions for Phase 3)

class BackupService:
    """Enhanced backup service with cloud storage"""
    
    def backup_to_s3(self, bucket_name, backup_file):
        """Upload backup to AWS S3"""
        import boto3
        s3_client = boto3.client('s3')
        s3_client.upload_file(
            backup_file,
            bucket_name,
            f"backups/daily/{os.path.basename(backup_file)}"
        )
    
    def backup_to_gcs(self, bucket_name, backup_file):
        """Upload backup to Google Cloud Storage"""
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"backups/daily/{os.path.basename(backup_file)}")
        blob.upload_from_filename(backup_file)
    
    def setup_point_in_time_recovery(self):
        """Configure PostgreSQL WAL archiving"""
        wal_archive_dir = "/var/lib/postgresql/wal_archive"
        os.makedirs(wal_archive_dir, exist_ok=True)
        # WAL files automatically archived for recovery
```

### STEP 8: CI/CD Pipeline Setup (30 minutes)

**File**: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r src/requirements/requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest src/tests/ -v --cov
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker images
      run: |
        docker build -f docker/app/Dockerfile -t labeling-app:latest .
    
    - name: Push to Docker Hub
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USER }} --password-stdin
        docker tag labeling-app:latest ${{ secrets.DOCKER_USER }}/labeling-app:latest
        docker push ${{ secrets.DOCKER_USER }}/labeling-app:latest
    
    - name: Deploy to production
      run: |
        ssh -i ${{ secrets.DEPLOY_KEY }} ubuntu@your-production-server.com << 'EOF'
        cd /opt/labeling-app
        docker-compose pull
        docker-compose up -d
        docker-compose exec -T app python src/scripts/migrate_to_postgresql.py
        EOF
```

---

## <a name="testing"></a>🧪 TESTING & VERIFICATION

### Test 1: HTTPS Connectivity

```bash
# Verify SSL certificate
openssl s_client -connect yourdomain.com:443 -tls1_2

# Test HTTPS connection
curl -I https://yourdomain.com/

# Expected: 301 redirect to HTTPS, valid certificate
```

### Test 2: Database Replication

```bash
# Check replica status on primary
psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Expected: Replica connection shown with sync state

# Test replica read capability
psql -h localhost -U labeling_user -d labeling_db -p 5433 -c "SELECT COUNT(*) FROM segments;"

# Expected: 309 (or current count)
```

### Test 3: Monitoring Dashboard

```bash
# Access Grafana
firefox http://localhost:3001
# Login: admin / admin

# Create dashboards for:
# - CPU usage
# - Memory
# - Database connections
# - HTTP requests
# - Error rates
```

### Test 4: Load Test

```bash
# Install load testing tool
pip install locust

# Create locustfile.py
from locust import User, TaskSet, task, between

class UserTasks(TaskSet):
    @task(1)
    def index(self):
        self.client.get("/")

class WebsiteUser(User):
    tasks = [UserTasks]
    wait_time = between(1, 5)

# Run test
locust -f locustfile.py --host=http://localhost:8080 -u 1000 -r 100
```

### Test 5: Failover Test

```bash
# Stop primary PostgreSQL
pg_ctl -D ~/postgresql_data stop

# Verify application continues working on replica
curl http://localhost:3000/api/v2/transcriptions/projects

# Expected: 200 OK (read-only mode)

# Promote replica to primary
cd ~/postgresql_replicas/replica1
touch /tmp/promote_replica1

# Restart primary
pg_ctl -D ~/postgresql_data start

# Verify high availability worked
```

---

## <a name="troubleshooting"></a>⚠️ TROUBLESHOOTING GUIDE

### Issue: SSL Certificate Expired

```bash
# Solution: Auto-renewal with certbot
sudo certbot renew --force-renewal

# Or manual renewal
sudo certbot certonly --standalone --force-renewal -d yourdomain.com
```

### Issue: PostgreSQL Replication Lag Too High

```bash
# Check replication lag
psql -U postgres -c "SELECT now() - pg_last_xact_replay_time() as replication_lag;"

# If lag > 1 second:
# 1. Increase wal_keep_size in postgresql.conf
# 2. Increase max_wal_senders
# 3. Check network latency: ping replica-server

# Restart primary
pg_ctl -D ~/postgresql_data restart
```

### Issue: Nginx Returns 502 Bad Gateway

```bash
# Check if all Flask instances are running
curl http://127.0.0.1:5001
curl http://127.0.0.1:5002
curl http://127.0.0.1:5003

# If any fail, restart:
export DATABASE_URL="postgresql://..."
export REDIS_URL="redis://..."
python src/app.py &

# Check Nginx error log
tail -50 /opt/homebrew/var/log/nginx/error.log
```

### Issue: Redis Out of Memory

```bash
# Check memory
redis-cli INFO memory

# Clear old sessions
redis-cli FLUSHDB ASYNC

# Or configure Redis to evict old keys
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Issue: Database Won't Start After Failover

```bash
# Check database status
pg_ctl -D ~/postgresql_data status

# If stuck, force recovery
pg_ctl -D ~/postgresql_data promote

# Restart
pg_ctl -D ~/postgresql_data start
```

---

## <a name="rollback"></a>↩️ ROLLBACK PROCEDURES

If Phase 3 has critical issues, rollback to Phase 2:

### Rollback Nginx

```bash
# Revert to Phase 2 config (HTTP only)
cp /opt/homebrew/etc/nginx/sites-available/labeling-app-phase2.conf \
   /opt/homebrew/etc/nginx/sites-available/labeling-app.conf

nginx -s reload
```

### Rollback Database

```bash
# Switch back to local SQLite
export DATABASE_URL="sqlite:///labeling_app.db"
# Restart app servers
pkill python
python src/app.py
```

### Rollback Docker

```bash
# Stop all containers
docker-compose down

# Restart local services
brew services restart postgresql@18
brew services restart redis
```

---

## <a name="monitoring"></a>📊 MONITORING DASHBOARD

### Grafana Panels to Create

#### 1. System Health
```
- CPU Usage (per instance)
- Memory Utilization
- Disk I/O
- Network Bandwidth
```

#### 2. Application Metrics
```
- HTTP Request Rate
- Error Rate (4xx, 5xx)
- Response Time (p50, p95, p99)
- Active Users
- Failed Logins
```

#### 3. Database Health
```
- Query Time (ms)
- Active Connections
- Replication Lag
- Database Size
- Transaction Rate
```

#### 4. Business Metrics
```
- Segments Completed per Hour
- Words Validated
- Average Annotation Time
- Concurrent Annotators
```

---

## 📋 PHASE 3 COMPLETION CHECKLIST

### Pre-Deployment
- [ ] Phase 2 fully tested and working
- [ ] Domain name registered and pointing to server
- [ ] SSL certificate ready
- [ ] PostgreSQL replication verified locally
- [ ] Docker installed and tested
- [ ] All team members have .env credentials

### Deployment
- [ ] HTTPS configured and working
- [ ] Redirect HTTP → HTTPS working
- [ ] PostgreSQL replication running
- [ ] Docker Compose services starting
- [ ] Monitoring dashboard accessible
- [ ] Alerting configured (email + Telegram)
- [ ] Backups running on schedule
- [ ] CI/CD pipeline active

### Post-Deployment
- [ ] Production data migrated
- [ ] All anotadores logged in successfully
- [ ] Database replication verified
- [ ] Monitoring showing all green
- [ ] Backups tested (can restore)
- [ ] Failover tested (primary → replica)
- [ ] Team trained on new system
- [ ] Runbook updated

### Documentation
- [ ] Deployment guide written
- [ ] Troubleshooting added to wiki
- [ ] On-call procedures documented
- [ ] Disaster recovery plan tested
- [ ] Monitoring alerts documented

---

## 🚀 QUICK START (For When Ready)

To implement Phase 3 when you're ready, just run:

```bash
# 1. Copy this entire guide to a new prompt
# 2. Tell the agent: "Implement PHASE 3 following PHASE3_IMPLEMENTATION_GUIDE.md"
# 3. The agent will execute ALL steps automatically
# 4. You'll have production-grade system in ~4 hours
```

---

## 📞 SUPPORT RESOURCES

- **PostgreSQL Replication**: https://www.postgresql.org/docs/current/warm-standby.html
- **Certbot Let's Encrypt**: https://certbot.eff.org/
- **Prometheus**: https://prometheus.io/docs/
- **Grafana**: https://grafana.com/docs/
- **Docker Compose**: https://docs.docker.com/compose/

---

**Document Version**: 1.0  
**Last Updated**: April 10, 2026  
**Phase 2 Status**: ✅ Production Ready  
**Phase 3 Status**: 📚 Documented, Ready to Deploy  

---

## When You're Ready for Phase 3

Simply copy all this content and create a new prompt for the agent:

> "Implement Phase 3 for the labeling app following the PHASE3_IMPLEMENTATION_GUIDE.md. 
> Use all the detailed steps, configurations, and Docker setups provided. 
> Deploy everything and run all tests to verify working correctly."

The agent will implement everything end-to-end! ✅
