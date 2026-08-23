#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  cat > .env <<'EOF'
OPENWORLD_DATABASE_URL=sqlite:///./openworld.db
OPENWORLD_SECRET_KEY=dev-only-not-for-production-use-32b-minimum-key
OPENWORLD_DEMO_MODE=true
OPENWORLD_ENVIRONMENT=local
OPENWORLD_LOG_LEVEL=INFO
EOF
fi

if [[ ! -f apps/web/.env.local ]]; then
  echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > apps/web/.env.local
fi

echo "OpenWorld environment ready (SQLite demo mode)."
