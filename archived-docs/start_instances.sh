#!/bin/bash
# Start 3 Flask instances for load balancing (Phase 2)

PROJECT_DIR="/Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app"
cd "$PROJECT_DIR"

# Export common environment variables
export DATABASE_URL="postgresql://labeling_user:phase2_password@localhost:5432/labeling_db"
export REDIS_URL="redis://127.0.0.1:6379/0"
export FLASK_ENV="development"
export JWT_SECRET_KEY="dev-jwt-secret-key-phase2"
export SECRET_KEY="dev-secret-key-phase2"

# Activate virtual environment
. venv/bin/activate
cd src

# Start Instance 1 (Port 5001)
echo "🚀 Starting Flask Instance 1 on port 5001..."
export FLASK_PORT=5001
python -c "
import os
os.environ['FLASK_PORT'] = '5001'
from app import create_app
app = create_app()
app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)
" 2>> logs/instance1.log &
PID1=$!
echo "   PID: $PID1"

# Wait a bit for first instance to start
sleep 2

# Start Instance 2 (Port 5002)
echo "🚀 Starting Flask Instance 2 on port 5002..."
export FLASK_PORT=5002
python -c "
import os
os.environ['FLASK_PORT'] = '5002'
from app import create_app
app = create_app()
app.run(host='127.0.0.1', port=5002, debug=False, use_reloader=False)
" 2>> logs/instance2.log &
PID2=$!
echo "   PID: $PID2"

# Wait a bit
sleep 2

# Start Instance 3 (Port 5003)
echo "🚀 Starting Flask Instance 3 on port 5003..."
export FLASK_PORT=5003
python -c "
import os
os.environ['FLASK_PORT'] = '5003'
from app import create_app
app = create_app()
app.run(host='127.0.0.1', port=5003, debug=False, use_reloader=False)
" 2>> logs/instance3.log &
PID3=$!
echo "   PID: $PID3"

echo ""
echo "✅ All instances started:"
echo "   Instance 1: 127.0.0.1:5001 (PID: $PID1)"
echo "   Instance 2: 127.0.0.1:5002 (PID: $PID2)"
echo "   Instance 3: 127.0.0.1:5003 (PID: $PID3)"
echo ""
echo "Waiting for instances to initialize..."
sleep 3

# Check if instances are running
for port in 5001 5002 5003; do
    if curl -s http://127.0.0.1:$port/ > /dev/null; then
        echo "✅ Instance on port $port is responding"
    else
        echo "❌ Instance on port $port is NOT responding"
    fi
done
