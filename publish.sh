#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# publish.sh — Build and publish Cloudjack to PyPI
#
# Usage:
#   ./publish.sh              # publish current version in pyproject.toml
#   ./publish.sh 0.2.0        # bump to 0.2.0, tag, build, publish
#   ./publish.sh patch        # auto-bump patch  (0.1.0 → 0.1.1)
#   ./publish.sh minor        # auto-bump minor  (0.1.0 → 0.2.0)
#   ./publish.sh major        # auto-bump major  (0.1.0 → 1.0.0)
#
# Environment:
#   PYPI_TOKEN    — PyPI API token  (required)
#   TEST_PYPI=1   — publish to TestPyPI instead of production PyPI
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TOML="$ROOT/pyproject.toml"

# ── helpers ──────────────────────────────────────────────────────────

red()   { printf '\033[1;31m%s\033[0m\n' "$*"; }
green() { printf '\033[1;32m%s\033[0m\n' "$*"; }
info()  { printf '\033[1;34m→ %s\033[0m\n' "$*"; }

die() { red "ERROR: $*" >&2; exit 1; }

current_version() {
    grep -m1 '^version' "$TOML" | sed 's/.*"\(.*\)".*/\1/'
}

set_version() {
    local new="$1"
    sed -i "s/^version = \".*\"/version = \"$new\"/" "$TOML"
    green "Version set to $new"
}

bump_version() {
    local cur="$1" part="$2"
    IFS='.' read -r major minor patch <<< "$cur"
    case "$part" in
        major) major=$((major + 1)); minor=0; patch=0 ;;
        minor) minor=$((minor + 1)); patch=0 ;;
        patch) patch=$((patch + 1)) ;;
        *)     die "Unknown bump part: $part" ;;
    esac
    echo "${major}.${minor}.${patch}"
}

# ── pre-flight checks ───────────────────────────────────────────────

command -v uv >/dev/null 2>&1 || die "uv is not installed"

if [[ -z "${PYPI_TOKEN:-}" ]]; then
    die "PYPI_TOKEN env var is not set. Get one at https://pypi.org/manage/account/token/"
fi

# ── version handling ─────────────────────────────────────────────────

CUR_VERSION="$(current_version)"
info "Current version: $CUR_VERSION"

if [[ $# -ge 1 ]]; then
    ARG="$1"
    case "$ARG" in
        major|minor|patch)
            NEW_VERSION="$(bump_version "$CUR_VERSION" "$ARG")"
            ;;
        [0-9]*)
            NEW_VERSION="$ARG"
            ;;
        *)
            die "Invalid version argument: $ARG  (use major|minor|patch or a semver string)"
            ;;
    esac
    set_version "$NEW_VERSION"
else
    NEW_VERSION="$CUR_VERSION"
fi

info "Publishing version: $NEW_VERSION"

# ── run tests ────────────────────────────────────────────────────────

info "Running tests …"
uv run pytest tests/ -q --tb=short || die "Tests failed — aborting publish"

# ── clean previous builds ───────────────────────────────────────────

info "Cleaning dist/ …"
rm -rf "$ROOT/dist"

# ── build ────────────────────────────────────────────────────────────

info "Building sdist + wheel …"
uv build || die "Build failed"

ls -lh "$ROOT/dist/"

# ── publish ──────────────────────────────────────────────────────────

if [[ "${TEST_PYPI:-}" == "1" ]]; then
    REPO_URL="https://test.pypi.org/simple/"
    PUBLISH_URL="https://test.pypi.org/legacy/"
    info "Publishing to TestPyPI …"
    # Pass the token via UV_PUBLISH_TOKEN rather than as a CLI argument so
    # it doesn't appear in process listings / shell history.
    UV_PUBLISH_TOKEN="$PYPI_TOKEN" uv publish --publish-url "$PUBLISH_URL"
    green "✓ Published to TestPyPI"
    green "  Install:  pip install -i $REPO_URL cloudjack==$NEW_VERSION"
else
    info "Publishing to PyPI …"
    UV_PUBLISH_TOKEN="$PYPI_TOKEN" uv publish
    green "✓ Published to PyPI"
    green "  Install:  pip install cloudjack==$NEW_VERSION"
fi

# ── git tag ──────────────────────────────────────────────────────────

if git rev-parse "v$NEW_VERSION" >/dev/null 2>&1; then
    info "Tag v$NEW_VERSION already exists — skipping"
else
    info "Creating git tag v$NEW_VERSION …"
    git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
    git push origin "v$NEW_VERSION"
    green "✓ Tag v$NEW_VERSION pushed"
fi

green "Done 🎉"
