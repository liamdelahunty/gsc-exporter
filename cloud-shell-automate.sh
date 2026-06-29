#!/usr/bin/env bash
#
# Bash script to automate Google Search Console caching and reporting in Google Cloud Shell.
# Designed to run in shell.cloud.google.com.
# Uses British English and standard project conventions.

set -e

# Define colours for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Colour

# Default options
RUN_REPORTS=false
NON_INTERACTIVE=false
SITES_FILE="site-lists/sites.txt"

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --run-reports) RUN_REPORTS=true ;;
        --non-interactive|-y) NON_INTERACTIVE=true ;;
        --sites-file) SITES_FILE="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo -e "${GREEN}========================================================================${NC}"
echo -e "${GREEN}             GSC EXPORTER - CLOUD SHELL AUTOMATION RUNNER               ${NC}"
echo -e "${GREEN}========================================================================${NC}"

# Navigate to script directory if not already there
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Check Python Environment
echo -e "\n${YELLOW}[1/5] Checking Python Environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "Virtual environment (.venv) not found. Creating one..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies
echo -e "Installing and updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. Check Authentication
echo -e "\n${YELLOW}[2/5] Checking Authentication...${NC}"
if [ ! -f "config/token.json" ]; then
    echo -e "${RED}Authentication token (config/token.json) is missing.${NC}"
    if [ "$NON_INTERACTIVE" = true ]; then
        echo -e "${RED}Error: Cannot authenticate in non-interactive mode. Please run manually first.${NC}"
        exit 1
    fi
    echo -e "Starting the Cloud Shell authentication helper..."
    python utilities/auth-cloud-shell.py
    
    # Check again if successful
    if [ ! -f "config/token.json" ]; then
        echo -e "${RED}Authentication failed. Please run 'python utilities/auth-cloud-shell.py' manually.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Authentication token found.${NC}"
fi

# 3. Determine Sites list
echo -e "\n${YELLOW}[3/5] Determining Sites...${NC}"
if [ ! -f "$SITES_FILE" ]; then
    # Try alternate files or fallback
    if [ "$SITES_FILE" = "site-lists/sites.txt" ] && [ -f "site-lists/test-site.txt" ]; then
        SITES_FILE="site-lists/test-site.txt"
    else
        echo -e "${RED}Error: Site list file not found at $SITES_FILE.${NC}"
        echo -e "Please create $SITES_FILE with your GSC site URLs (one per line)."
        exit 1
    fi
fi

echo -e "Using site list: ${GREEN}$SITES_FILE${NC}"
echo -e "Sites to process:"
grep -v '^#' "$SITES_FILE" | grep -v '^$' | sed 's/^/  - /'

# 4. Fetch and Warm Cache
echo -e "\n${YELLOW}[4/5] Running Cache Warmer...${NC}"
python utilities/cache_warmer.py --file "$SITES_FILE"

# 5. Verify Cache Completeness
echo -e "\n${YELLOW}[5/5] Analysing Cache Completeness...${NC}"
python utilities/generate_cache_inventory.py --sites-file "$SITES_FILE" --format all

# Run monthly reports if requested or prompted
if [ "$RUN_REPORTS" = true ]; then
    echo -e "\n${YELLOW}[+] Running Monthly Reports (Automatic)...${NC}"
    python run-monthly-reports.py --sites-file "$SITES_FILE"
elif [ "$NON_INTERACTIVE" = false ] && [ -t 0 ]; then
    echo -e "\n${YELLOW}[Optional] Generating Reports...${NC}"
    read -p "Do you want to run monthly reports for these sites now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python run-monthly-reports.py --sites-file "$SITES_FILE"
    fi
fi

echo -e "\n${GREEN}========================================================================${NC}"
echo -e "${GREEN}                  AUTOMATION RUN COMPLETED SUCCESSFULLY                 ${NC}"
echo -e "${GREEN}========================================================================${NC}\n"
