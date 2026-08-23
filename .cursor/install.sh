#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m pip install -e ".[dev]"

# Minimal .env with only Settings-backed OPENWORLD_* keys (avoids pydantic extra-field errors).
cat > .env <<'EOF'
OPENWORLD_DATABASE_URL=sqlite:///./openworld.db
OPENWORLD_SECRET_KEY=dev-only-not-for-production-use-32b-minimum-key
OPENWORLD_DEMO_MODE=true
OPENWORLD_ENVIRONMENT=local
OPENWORLD_LOG_LEVEL=INFO
EOF

# Next.js reads env from apps/web; default API URL is localhost:8000.
cat > apps/web/.env.local <<'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

cd apps/web
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
