#!/bin/bash
# Competitor Intelligence Crawler Runner
# This script triggers the crawler via the API endpoint
# Can be run manually or via cron job

set -e

# Configuration
API_URL="${CRAWLER_API_URL:-http://localhost:8000/api/competitors/crawl}"
PRIORITY="${CRAWLER_PRIORITY:-1}"  # 1=top 5, 2=mid-tier, 3=all
LOG_DIR="${CRAWLER_LOG_DIR:-./logs}"
LOG_FILE="$LOG_DIR/crawler_$(date +%Y%m%d_%H%M%S).log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================" log "Starting Competitor Crawler"
log "API URL: $API_URL"
log "Priority: $PRIORITY"
log "========================================"

# Check if server is running
if ! curl -s -f "${API_URL%/api*}/health" > /dev/null 2>&1; then
    log "ERROR: Server is not responding at ${API_URL%/api*}/health"
    log "Make sure the FastAPI server is running"
    exit 1
fi

log "Server is running ✓"

# Trigger crawl
log "Triggering crawl..."

RESPONSE=$(curl -s -X POST "$API_URL?priority=$PRIORITY" \
    -H "Content-Type: application/json" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    log "Crawl completed successfully ✓"
    log "Response: $BODY"

    # Extract stats from JSON response (requires jq, optional)
    if command -v jq &> /dev/null; then
        EVENTS_CREATED=$(echo "$BODY" | jq -r '.events_created // 0')
        SOURCES_CRAWLED=$(echo "$BODY" | jq -r '.sources_crawled // 0')
        DURATION=$(echo "$BODY" | jq -r '.duration_seconds // 0')

        log "Statistics:"
        log "  - Events created: $EVENTS_CREATED"
        log "  - Sources crawled: $SOURCES_CRAWLED"
        log "  - Duration: ${DURATION}s"
    fi
else
    log "ERROR: Crawl failed with HTTP $HTTP_CODE"
    log "Response: $BODY"
    exit 1
fi

log "========================================" log "Crawl completed"
log "Log saved to: $LOG_FILE"
log "========================================"

# Clean up old logs (keep last 30 days)
find "$LOG_DIR" -name "crawler_*.log" -mtime +30 -delete 2>/dev/null || true

exit 0
