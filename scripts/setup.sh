#!/usr/bin/env bash
# PersonalOS Setup Script
# Tested on: Ubuntu 22.04, Ubuntu 24.04, Debian 12
# Run as: ./scripts/setup.sh

set -euo pipefail

# ─────────────────────────────────────────────
# Colours
# ─────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET} $1"; }
info() { echo -e "${BLUE}→${RESET} $1"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $1"; }
fail() { echo -e "${RED}✗${RESET} $1"; exit 1; }
hr()   { echo -e "\n${BOLD}────────────────────────────────────────────────${RESET}\n"; }

# ─────────────────────────────────────────────
# Welcome
# ─────────────────────────────────────────────
clear
echo -e "${BOLD}"
cat << 'EOF'
  ____                                 _  ___  ____
 |  _ \ ___ _ __ ___  ___  _ __   __ _| |/ _ \/ ___|
 | |_) / _ \ '__/ __|/ _ \| '_ \ / _` | | | | \___ \
 |  __/  __/ |  \__ \ (_) | | | | (_| | | |_| |___) |
 |_|   \___|_|  |___/\___/|_| |_|\__,_|_|\___/|____/

EOF
echo -e "${RESET}"
echo "  Your model-agnostic personal AI operating system."
echo "  https://github.com/personalos/personalos"
echo ""
echo "  This setup takes about 10 minutes."
echo "  You'll need: OpenRouter API key + Telegram bot token"
hr

# ─────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────
info "Checking system requirements..."

# OS check
if [[ "$(uname -s)" != "Linux" ]] && [[ "$(uname -s)" != "Darwin" ]]; then
    fail "PersonalOS currently supports Linux and macOS. Windows users: use WSL2."
fi

# Root check (not required but common on fresh VPS)
if [[ "$EUID" -eq 0 ]]; then
    warn "Running as root. This works but consider creating a non-root user for production."
fi

# RAM check
RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
if [[ "$RAM_GB" -lt 2 ]]; then
    warn "Less than 2GB RAM detected. PersonalOS may run slowly. 4GB recommended."
fi

ok "System checks passed"
hr

# ─────────────────────────────────────────────
# Install dependencies
# ─────────────────────────────────────────────
info "Installing dependencies (Docker, Python, PostgreSQL client)..."

if ! command -v docker &>/dev/null; then
    info "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker 2>/dev/null || true
    ok "Docker installed"
else
    ok "Docker already installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
fi

if ! command -v docker compose &>/dev/null; then
    info "Installing Docker Compose plugin..."
    apt-get install -y docker-compose-plugin 2>/dev/null || \
    pip3 install docker-compose 2>/dev/null || \
    warn "Could not auto-install Docker Compose. Install manually: https://docs.docker.com/compose/install/"
fi

if ! command -v python3 &>/dev/null; then
    apt-get install -y python3 python3-pip 2>/dev/null || \
    brew install python3 2>/dev/null || \
    fail "Python3 is required. Install it and re-run this script."
fi

ok "Dependencies ready"
hr

# ─────────────────────────────────────────────
# Interactive configuration
# ─────────────────────────────────────────────

if [[ -f .env ]]; then
    warn ".env file already exists."
    read -rp "  Overwrite it? (y/N): " overwrite
    if [[ "${overwrite,,}" != "y" ]]; then
        info "Keeping existing .env. Skipping configuration questions."
        SKIP_CONFIG=true
    fi
fi

if [[ "${SKIP_CONFIG:-false}" != "true" ]]; then
    echo -e "${BOLD}Let's configure PersonalOS.${RESET}"
    echo "Press Enter to skip any optional field."
    echo ""

    # Name
    read -rp "  Your name: " USER_NAME
    USER_NAME="${USER_NAME:-User}"

    # Timezone
    echo ""
    echo "  Common timezones:"
    echo "    America/New_York  |  America/Los_Angeles  |  Europe/London"
    echo "    Europe/Berlin     |  Asia/Dubai           |  Asia/Singapore"
    read -rp "  Your timezone [Europe/London]: " USER_TZ
    USER_TZ="${USER_TZ:-Europe/London}"

    # Location
    read -rp "  Your city and country [London, UK]: " USER_LOCATION
    USER_LOCATION="${USER_LOCATION:-London, UK}"

    echo ""
    echo -e "${BOLD}Now the API keys.${RESET}"
    echo ""
    echo "  OpenRouter key → https://openrouter.ai/keys"
    read -rp "  OpenRouter API key (sk-or-...): " OPENROUTER_KEY

    echo ""
    echo "  Telegram bot token → message @BotFather → /newbot"
    read -rp "  Telegram bot token: " TG_TOKEN

    echo ""
    echo "  Telegram user ID → message @userinfobot"
    read -rp "  Your Telegram user ID: " TG_USER_ID

    echo ""
    echo -e "${BOLD}Which persona fits you best?${RESET}"
    echo "  1) solo-founder  — running businesses, products, projects"
    echo "  2) freelancer    — client work, proposals, invoicing"
    echo "  3) student       — studying, research, deadlines"
    echo "  4) ecommerce     — store, ads, inventory"
    echo "  5) default       — general purpose"
    read -rp "  Choose [5]: " PERSONA_CHOICE
    case "${PERSONA_CHOICE:-5}" in
        1) PERSONA="solo-founder" ;;
        2) PERSONA="freelancer" ;;
        3) PERSONA="student" ;;
        4) PERSONA="ecommerce" ;;
        *) PERSONA="default" ;;
    esac

    # Generate secret key
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # Write .env
    cp .env.example .env
    sed -i "s|sk-or-your-key-here|${OPENROUTER_KEY}|g" .env
    sed -i "s|your-bot-token-here|${TG_TOKEN}|g" .env
    sed -i "s|your-user-id-here|${TG_USER_ID}|g" .env
    sed -i "s|YOUR_NAME=Alex|YOUR_NAME=${USER_NAME}|g" .env
    sed -i "s|TIMEZONE=Europe/London|TIMEZONE=${USER_TZ}|g" .env
    sed -i "s|LOCATION=London, UK|LOCATION=${USER_LOCATION}|g" .env
    sed -i "s|PERSONA=default|PERSONA=${PERSONA}|g" .env
    sed -i "s|change-this-to-a-random-string|${SECRET}|g" .env

    ok ".env configured"
fi

hr

# ─────────────────────────────────────────────
# Start services
# ─────────────────────────────────────────────
info "Starting PersonalOS services..."

docker compose pull --quiet
docker compose up -d

# Wait for Postgres to be ready
info "Waiting for database..."
for i in {1..30}; do
    if docker compose exec -T db pg_isready -U personalos &>/dev/null; then
        ok "Database ready"
        break
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
        fail "Database didn't start in time. Run: docker compose logs db"
    fi
done

# Run migrations
info "Initialising database schema..."
docker compose exec -T db psql -U personalos -d personalos -f /docker-entrypoint-initdb.d/init.sql &>/dev/null
ok "Database schema ready"

hr

# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────
info "Running health checks..."

sleep 3
if curl -sf http://localhost:8080/health &>/dev/null; then
    ok "PersonalOS API is running"
else
    warn "API health check failed — services may still be starting. Check: docker compose logs api"
fi

hr

# ─────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────
echo -e "${GREEN}${BOLD}PersonalOS is running!${RESET}"
echo ""
echo "  What to do next:"
echo ""
echo "  1. Message your Telegram bot to test it:"
echo "     → Send it: 'Hello, are you there?'"
echo ""
echo "  2. Tell PersonalOS about yourself (copy and paste into the bot):"
echo "     → 'Remember: I work on [your business/project]. My priorities are [...]'"
echo ""
echo "  3. Connect your email (in the bot or Hermes desktop):"
echo "     → '/skill load google-workspace'"
echo ""
echo "  4. View logs:         docker compose logs -f"
echo "  5. Stop services:     docker compose down"
echo "  6. Update:            ./scripts/update.sh"
echo ""
echo "  Documentation: https://github.com/personalos/personalos/tree/main/docs"
echo "  Community: https://discord.gg/personalos"
echo ""
