#!/usr/bin/env bash
# PersonalOS Update Script
# Pulls latest changes and restarts services

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET} $1"; }
info() { echo -e "${BLUE}→${RESET} $1"; }

echo ""
echo "PersonalOS Update"
echo "─────────────────"
echo ""

# Save current version
CURRENT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
info "Current version: $CURRENT"

# Pull latest
info "Pulling latest changes..."
git pull origin main
NEW=$(git rev-parse --short HEAD)

if [[ "$CURRENT" == "$NEW" ]]; then
    echo ""
    echo "Already up to date."
    exit 0
fi

ok "Updated from $CURRENT to $NEW"

# Pull new images
info "Updating Docker images..."
docker compose pull --quiet
ok "Images updated"

# Restart services (zero-downtime rolling restart)
info "Restarting services..."
docker compose up -d --remove-orphans
ok "Services restarted"

# Health check
sleep 3
if curl -sf http://localhost:8080/health &>/dev/null; then
    ok "Health check passed"
else
    echo ""
    echo "⚠️  Health check failed after update."
    echo "   Check logs: docker compose logs api --tail=50"
    exit 1
fi

echo ""
echo "Update complete. PersonalOS is running $NEW."
echo ""
