#!/usr/bin/env bash
# PersonalOS Setup Script
# Supports: macOS (Intel + Apple Silicon), Linux (Ubuntu/Debian/Arch), WSL2
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
# Detect OS
# ─────────────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
    Linux*)
        # Detect distro family for package manager
        if command -v apt-get &>/dev/null; then
            PKG_MANAGER="apt"
        elif command -v pacman &>/dev/null; then
            PKG_MANAGER="pacman"
        elif command -v dnf &>/dev/null; then
            PKG_MANAGER="dnf"
        else
            PKG_MANAGER="unknown"
        fi
        ;;
    Darwin*)
        PKG_MANAGER="brew"
        ;;
    *)
        fail "Unsupported OS: $OS. On Windows, run this inside WSL2."
        ;;
esac

# Portable in-place sed: sed_inplace 's/foo/bar/g' file
sed_inplace() {
    local expr="$1"
    local file="$2"
    if [[ "$OS" == "Darwin"* ]]; then
        sed -i '' "$expr" "$file"
    else
        sed -i "$expr" "$file"
    fi
}

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
echo "  https://github.com/krishnatejaganesh/personalos"
echo ""
echo "  This setup takes about 10 minutes."
echo "  You'll need: OpenRouter API key + Telegram bot token"
hr

# ─────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────
info "Checking system requirements..."

# Root check
if [[ "$EUID" -eq 0 ]]; then
    warn "Running as root. This works but consider creating a non-root user for production."
fi

# RAM check — OS-specific
if [[ "$OS" == "Darwin"* ]]; then
    RAM_BYTES=$(sysctl -n hw.memsize)
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
elif command -v free &>/dev/null; then
    RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
else
    RAM_GB=99  # can't detect, skip the warning
fi

if [[ "$RAM_GB" -lt 2 ]]; then
    warn "Less than 2GB RAM detected. PersonalOS may run slowly. 4GB recommended."
fi

ok "System checks passed"
hr

# ─────────────────────────────────────────────
# Install dependencies
# ─────────────────────────────────────────────
info "Checking dependencies (Docker, Python)..."

# ── Docker ──────────────────────────────────
if ! command -v docker &>/dev/null; then
    if [[ "$OS" == "Darwin"* ]]; then
        echo ""
        echo "  Docker Desktop is not installed."
        echo "  Download it from: https://www.docker.com/products/docker-desktop/"
        echo "  Install it, start it, then re-run this script."
        echo ""
        fail "Docker Desktop required on macOS. Install it and re-run."
    elif [[ "$PKG_MANAGER" == "apt" ]]; then
        info "Installing Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable --now docker 2>/dev/null || true
        ok "Docker installed"
    elif [[ "$PKG_MANAGER" == "pacman" ]]; then
        info "Installing Docker..."
        pacman -Sy --noconfirm docker
        systemctl enable --now docker
        ok "Docker installed"
    elif [[ "$PKG_MANAGER" == "dnf" ]]; then
        info "Installing Docker..."
        dnf install -y docker
        systemctl enable --now docker
        ok "Docker installed"
    else
        fail "Docker not found. Install it from https://docs.docker.com/get-docker/ and re-run."
    fi
else
    ok "Docker found ($(docker --version | cut -d' ' -f3 | tr -d ','))"
fi

# Make sure Docker daemon is running
if ! docker info &>/dev/null; then
    if [[ "$OS" == "Darwin"* ]]; then
        fail "Docker Desktop is installed but not running. Start it from your Applications folder, then re-run."
    else
        fail "Docker daemon is not running. Try: sudo systemctl start docker"
    fi
fi

# ── Docker Compose ───────────────────────────
if ! docker compose version &>/dev/null 2>&1; then
    if [[ "$OS" == "Darwin"* ]]; then
        # Docker Desktop ships Compose — if it's missing something is wrong
        fail "Docker Compose not found. Reinstall Docker Desktop from https://www.docker.com/products/docker-desktop/"
    elif [[ "$PKG_MANAGER" == "apt" ]]; then
        info "Installing Docker Compose plugin..."
        apt-get install -y docker-compose-plugin
    elif [[ "$PKG_MANAGER" == "pacman" ]]; then
        pacman -Sy --noconfirm docker-compose
    elif [[ "$PKG_MANAGER" == "dnf" ]]; then
        dnf install -y docker-compose-plugin
    else
        fail "Docker Compose not found. Install it from https://docs.docker.com/compose/install/"
    fi
fi
ok "Docker Compose ready"

# ── Python ───────────────────────────────────
if ! command -v python3 &>/dev/null; then
    if [[ "$OS" == "Darwin"* ]]; then
        if command -v brew &>/dev/null; then
            info "Installing Python via Homebrew..."
            brew install python3
        else
            fail "Python3 not found. Install Homebrew first (https://brew.sh) or install Python from https://python.org"
        fi
    elif [[ "$PKG_MANAGER" == "apt" ]]; then
        apt-get install -y python3 python3-pip
    elif [[ "$PKG_MANAGER" == "pacman" ]]; then
        pacman -Sy --noconfirm python python-pip
    elif [[ "$PKG_MANAGER" == "dnf" ]]; then
        dnf install -y python3 python3-pip
    else
        fail "Python3 required. Install it from https://python.org and re-run."
    fi
fi
ok "Python $(python3 --version | cut -d' ' -f2) ready"

hr

# ─────────────────────────────────────────────
# Interactive configuration
# ─────────────────────────────────────────────
SKIP_CONFIG=false

if [[ -f .env ]]; then
    warn ".env file already exists."
    read -rp "  Overwrite it? (y/N): " overwrite
    if [[ "${overwrite,,}" != "y" ]]; then
        info "Keeping existing .env. Skipping configuration questions."
        SKIP_CONFIG=true
    fi
fi

if [[ "$SKIP_CONFIG" != "true" ]]; then
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
    echo "    Asia/Kolkata      |  Australia/Sydney     |  Asia/Tokyo"
    read -rp "  Your timezone [UTC]: " USER_TZ
    USER_TZ="${USER_TZ:-UTC}"

    # Location
    read -rp "  Your city and country []: " USER_LOCATION
    USER_LOCATION="${USER_LOCATION:-}"

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
    sed_inplace "s|sk-or-your-key-here|${OPENROUTER_KEY}|g"        .env
    sed_inplace "s|your-bot-token-here|${TG_TOKEN}|g"              .env
    sed_inplace "s|your-user-id-here|${TG_USER_ID}|g"              .env
    sed_inplace "s|YOUR_NAME=Alex|YOUR_NAME=${USER_NAME}|g"        .env
    sed_inplace "s|TIMEZONE=Europe/London|TIMEZONE=${USER_TZ}|g"   .env
    sed_inplace "s|LOCATION=London, UK|LOCATION=${USER_LOCATION}|g" .env
    sed_inplace "s|PERSONA=default|PERSONA=${PERSONA}|g"           .env
    sed_inplace "s|change-this-to-a-random-string|${SECRET}|g"     .env

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
echo "  Documentation: https://github.com/krishnatejaganesh/personalos/tree/main/docs"
echo "  Community: https://discord.gg/personalos"
echo ""
