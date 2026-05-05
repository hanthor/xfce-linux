#!/bin/bash
# XFCE Linux BuildStream — Build Monitoring Script
# Tracks build progress and alerts on status changes

set -euo pipefail

PROJECT_DIR="~/dev/xfce-linux"
LOG_FILE="/tmp/xfce-build-full.log"
STATUS_FILE="/tmp/xfce-build-status.txt"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Initialize status
LAST_LINE_COUNT=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  XFCE Linux OCI Build — Progress Monitor                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Monitoring: $LOG_FILE"
echo "Started: $(date)"
echo ""

while true; do
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}[$(date '+%H:%M:%S')] Waiting for build to start...${NC}"
        sleep 10
        continue
    fi
    
    # Get current line count and file size
    CURRENT_LINES=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
    FILE_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    
    # Show progress
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} Build log: $FILE_SIZE | Lines: $CURRENT_LINES"
    
    # Extract key metrics
    if grep -q "Resolving elements" "$LOG_FILE"; then
        echo -e "${GREEN}  ✓ Elements resolved${NC}"
    fi
    
    if grep -q "Initializing remote caches" "$LOG_FILE"; then
        echo -e "${GREEN}  ✓ Remote caches initialized${NC}"
    fi
    
    if grep -q "Query cache" "$LOG_FILE"; then
        echo -e "${GREEN}  ✓ Cache queried${NC}"
    fi
    
    # Count currently building elements
    BUILDING=$(grep -o "built\|building\|cached" "$LOG_FILE" 2>/dev/null | sort | uniq -c | tail -5 || echo "")
    if [ -n "$BUILDING" ]; then
        echo -e "${YELLOW}  Build status:${NC}"
        echo "$BUILDING" | sed 's/^/    /'
    fi
    
    # Check for errors
    if grep -qi "ERROR\|FAILURE\|failed" "$LOG_FILE"; then
        echo -e "${RED}  ⚠ ERRORS DETECTED!${NC}"
        grep -i "error\|failure\|failed" "$LOG_FILE" | tail -3 | sed 's/^/    /'
    fi
    
    # Check for completion
    if grep -q "BUILD SUCCESS\|Build complete" "$LOG_FILE"; then
        echo -e "${GREEN}✓ BUILD COMPLETED SUCCESSFULLY!${NC}"
        tail -20 "$LOG_FILE" | grep -E "SUCCESS|Pipeline Summary|Total|processed" 
        break
    fi
    
    if grep -q "BUILD FAILURE" "$LOG_FILE"; then
        echo -e "${RED}✗ BUILD FAILED!${NC}"
        tail -30 "$LOG_FILE"
        break
    fi
    
    # Check if process still running
    if ps aux | grep -q "bst.*build.*oci/xfce-linux" | grep -v grep; then
        echo -e "${GREEN}  Build process running...${NC}"
    else
        # Check if container still exists
        if podman ps -a --format "{{.Names}}" 2>/dev/null | grep -q "bst2\|funny_jemison"; then
            echo -e "${YELLOW}  Container still exists...${NC}"
        else
            echo -e "${RED}  Build process not found!${NC}"
            echo -e "  Last 30 lines of log:"
            tail -30 "$LOG_FILE" | sed 's/^/    /'
            break
        fi
    fi
    
    echo ""
    sleep 30
done

echo ""
echo -e "${BLUE}Build monitoring completed at $(date)${NC}"
