#!/bin/bash
# Run Celery workers for the Daily Challenge application

# Change to the project directory
cd "$(dirname "$0")/.."

# Load environment variables
set -a
source .env
set +a

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Default values
WORKER_CONCURRENCY=${WORKER_CONCURRENCY:-2}
WORKER_LOGLEVEL=${WORKER_LOGLEVEL:-info}

# Command to run workers
run_workers() {
    echo "Starting Celery workers with Redis broker at ${REDIS_URL}..."
    celery -A app.core.celery_app.celery_app worker \
        --loglevel=${WORKER_LOGLEVEL} \
        --concurrency=${WORKER_CONCURRENCY} \
        --queues=default,emails,content \
        --hostname=worker@%h
}

# Command to run the Flower monitoring tool
run_flower() {
    echo "Starting Flower monitoring on http://localhost:5555..."
    celery -A app.core.celery_app.celery_app flower \
        --port=5555 \
        --broker=${REDIS_URL}
}

# Command to run a scheduled beat process
run_beat() {
    echo "Starting Celery beat scheduler..."
    celery -A app.core.celery_app.celery_app beat \
        --loglevel=${WORKER_LOGLEVEL}
}

# Parse arguments
case "$1" in
    worker)
        run_workers
        ;;
    flower)
        run_flower
        ;;
    beat)
        run_beat
        ;;
    all)
        # Run both worker and flower in background
        run_workers &
        run_flower
        ;;
    *)
        echo "Usage: $0 {worker|flower|beat|all}"
        echo "  worker: Run Celery workers"
        echo "  flower: Run Flower monitoring dashboard"
        echo "  beat:   Run Celery beat scheduler"
        echo "  all:    Run both workers and flower"
        exit 1
        ;;
esac
