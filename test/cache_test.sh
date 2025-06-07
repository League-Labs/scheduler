#!/bin/bash
# Test script for GitHub Teams cache functionality

# Determine script location and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

# Source the .env file if it exists
if [[ -f "$ENV_FILE" ]]; then
    echo "Loading environment variables from $ENV_FILE"
    source "$ENV_FILE"
else
    echo "Warning: .env file not found at $ENV_FILE"
fi

# Ensure we exit on error
set -e

# Check if GITHUB_TOKEN is set
if [[ -z "$GITHUB_TOKEN" ]]; then
    echo "Error: GITHUB_TOKEN environment variable not set"
    echo "Please set GITHUB_TOKEN to proceed"
    exit 1
fi

# Check if GITHUB_TEAM is set
if [[ -z "$GITHUB_TEAM" ]]; then
    echo "Warning: GITHUB_TEAM environment variable not set"
    echo "Some tests may fail without a specific team to test with"
    HAS_TEAM=0
else
    HAS_TEAM=1
fi

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running GitHub Teams Cache Tests${NC}"
echo "-----------------------------------"

# Test 1: Show cache status
echo -e "${YELLOW}Test 1: Show cache status${NC}"
echo "Expected: Should display cache status without errors"
python cli.py cache --status
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Test 1 passed: Cache status displayed successfully${NC}"
else
    echo -e "${RED}Test 1 failed: Could not display cache status${NC}"
    exit 1
fi
echo ""

# If we have a team set, run more specific tests
if [ $HAS_TEAM -eq 1 ]; then
    # Parse org and team from GITHUB_TEAM
    GITHUB_TEAM_URL=$GITHUB_TEAM
    # Extract org and team using Python helper
    ORG_TEAM=$(python -c "from gh_api import parse_team_url; org, team = parse_team_url('$GITHUB_TEAM_URL'); print(f'{org}/{team}' if org and team else '')")
    
    if [[ -z "$ORG_TEAM" ]]; then
        echo -e "${RED}Could not parse org/team from GITHUB_TEAM: $GITHUB_TEAM${NC}"
        exit 1
    fi
    
    ORG=$(echo $ORG_TEAM | cut -d'/' -f1)
    TEAM=$(echo $ORG_TEAM | cut -d'/' -f2)
    
    echo "Using organization: $ORG"
    echo "Using team: $TEAM"
    
    # Test 2: Refresh cache for team
    echo -e "${YELLOW}Test 2: Refresh cache for team${NC}"
    echo "Expected: Should cache team members without errors"
    python cli.py cache --refresh --org $ORG --team $TEAM
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Test 2 passed: Cache refreshed successfully${NC}"
    else
        echo -e "${RED}Test 2 failed: Could not refresh cache${NC}"
        exit 1
    fi
    echo ""
    
    # Test 3: Verify cache status after refresh
    echo -e "${YELLOW}Test 3: Verify cache status after refresh${NC}"
    echo "Expected: Should show the team we just cached"
    python cli.py cache --status | grep -q "$ORG/$TEAM"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Test 3 passed: Team found in cache${NC}"
    else
        echo -e "${RED}Test 3 failed: Team not found in cache${NC}"
        exit 1
    fi
    echo ""
    
    # Test 4: Invalidate specific team cache
    echo -e "${YELLOW}Test 4: Invalidate specific team cache${NC}"
    echo "Expected: Should invalidate the cache for our team"
    python cli.py cache --invalidate --org $ORG --team $TEAM
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Test 4 passed: Cache invalidated successfully${NC}"
    else
        echo -e "${RED}Test 4 failed: Could not invalidate cache${NC}"
        exit 1
    fi
    echo ""
    
    # Test 5: Verify cache status after invalidation
    echo -e "${YELLOW}Test 5: Verify cache status after invalidation${NC}"
    echo "Expected: Should not show the team we just invalidated"
    python cli.py cache --status | grep -q "$ORG/$TEAM"
    if [ $? -ne 0 ]; then
        echo -e "${GREEN}Test 5 passed: Team not found in cache after invalidation${NC}"
    else
        echo -e "${RED}Test 5 failed: Team still found in cache after invalidation${NC}"
        exit 1
    fi
    echo ""
fi

# Test 6: Refresh and invalidate all
echo -e "${YELLOW}Test 6: Testing full invalidation${NC}"
echo "Expected: Should invalidate all caches"

# First refresh a team if we have one (to ensure there's something to invalidate)
if [ $HAS_TEAM -eq 1 ]; then
    python cli.py cache --refresh --org $ORG --team $TEAM >/dev/null 2>&1
fi

# Now invalidate all
python cli.py cache --invalidate
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Test 6 passed: All cache invalidated successfully${NC}"
else
    echo -e "${RED}Test 6 failed: Could not invalidate all cache${NC}"
    exit 1
fi

# Final status check
echo -e "${YELLOW}Final cache status:${NC}"
python cli.py cache --status

echo ""
echo -e "${GREEN}All tests passed successfully!${NC}"
