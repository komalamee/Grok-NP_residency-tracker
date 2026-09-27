#!/usr/bin/env bash
# Nomad Pro – UK Residency Tracker: install or update the engine on this machine.
#
#   bash install.sh            # install, or update to the latest published version
#   bash install.sh --check    # only compare the installed VERSION with the published one
#                              #   exit 0 = up to date, 10 = update available, 1 = could not check
#
# Can be run again and again (idempotent). Never needs sudo. Installs into a fixed folder:
#   ~/nomad-pro-engine   (override with NOMAD_PRO_ENGINE_DIR)
#
# How it gets the engine, in order:
#   1. existing git checkout  -> git pull --ff-only (refuses if tracked files were edited locally)
#   2. no folder yet + git    -> git clone --depth 1 (branch main)
#   3. otherwise / on failure -> tarball of branch main via curl from the GitHub archive URL
# Then: pip install --user the Python requirements if missing, run the test suite, print the version.
#
# Environment overrides (mainly for testing or mirrors):
#   NOMAD_PRO_ENGINE_DIR    install folder (default ~/nomad-pro-engine)
#   NOMAD_PRO_REPO_URL      git URL (default https://github.com/komalamee/Grok-NP_residency-tracker.git;
#                           a local path or file:// URL works too)
#   NOMAD_PRO_BRANCH        branch (default main)
#   NOMAD_PRO_TARBALL_URL   tarball URL (default GitHub archive of the branch; file:// works)
#   NOMAD_PRO_VERSION_URL   URL of the published VERSION file (default raw.githubusercontent.com, branch main)
#   NOMAD_PRO_SOURCE_DIR    copy from a local folder instead of downloading (no git, no network)
#   NOMAD_PRO_NO_GIT=1      never use git (tarball / local folder only)
#   NOMAD_PRO_SKIP_PIP=1    don't install Python requirements
#   NOMAD_PRO_SKIP_TESTS=1  don't run the test suite
set -euo pipefail

REPO_SLUG="komalamee/Grok-NP_residency-tracker"
BRANCH="${NOMAD_PRO_BRANCH:-main}"
ENGINE_DIR="${NOMAD_PRO_ENGINE_DIR:-$HOME/nomad-pro-engine}"
REPO_URL="${NOMAD_PRO_REPO_URL:-https://github.com/${REPO_SLUG}.git}"
TARBALL_URL="${NOMAD_PRO_TARBALL_URL:-https://github.com/${REPO_SLUG}/archive/refs/heads/${BRANCH}.tar.gz}"
VERSION_URL="${NOMAD_PRO_VERSION_URL:-https://raw.githubusercontent.com/${REPO_SLUG}/${BRANCH}/VERSION}"
SOURCE_DIR="${NOMAD_PRO_SOURCE_DIR:-}"
MODE="install"
[ "${1:-}" = "--check" ] && MODE="check"
[ "$(id -u)" = "0" ] && echo "note: running as root is not needed; this installs into ${ENGINE_DIR} only." >&2

log()  { printf 'nomad-pro: %s\n' "$*"; }
warn() { printf 'nomad-pro: WARNING: %s\n' "$*" >&2; }
die()  { printf 'nomad-pro: ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }
use_git() { [ "${NOMAD_PRO_NO_GIT:-0}" != "1" ] && [ -z "$SOURCE_DIR" ] && have git; }
local_version() { [ -f "$ENGINE_DIR/VERSION" ] && tr -d ' \n\r' < "$ENGINE_DIR/VERSION" || echo "none"; }
# An engine folder we are allowed to replace: it must look like ours.
is_engine_dir() { [ -f "$1/VERSION" ] && [ -f "$1/tools/srt_engine.py" ]; }

remote_version() {
  if [ -n "$SOURCE_DIR" ]; then
    tr -d ' \n\r' < "$SOURCE_DIR/VERSION"
  elif have curl; then
    curl -fsSL --max-time 20 "$VERSION_URL" | tr -d ' \n\r'
  else
    return 1
  fi
}

have python3 || die "python3 is required."

# ---------------------------------------------------------------- --check
if [ "$MODE" = "check" ]; then
  lv="$(local_version)"
  rv="$(remote_version 2>/dev/null || true)"
  [ -n "$rv" ] || { echo "installed=${lv} published=unknown"; exit 1; }
  echo "installed=${lv} published=${rv}"
  [ "$lv" = "$rv" ] && exit 0 || exit 10
fi

# ---------------------------------------------------------------- fetch helpers
install_from_tree() {  # $1 = folder holding a full engine tree; swaps it into ENGINE_DIR
  local src="$1"
  is_engine_dir "$src" || die "downloaded tree does not look like the Nomad Pro engine (no VERSION / tools/srt_engine.py)."
  if [ -e "$ENGINE_DIR" ] && ! is_engine_dir "$ENGINE_DIR"; then
    if [ -n "$(ls -A "$ENGINE_DIR" 2>/dev/null)" ]; then
      die "$ENGINE_DIR exists and is not a Nomad Pro engine folder; not touching it. Move it or set NOMAD_PRO_ENGINE_DIR."
    fi
    rmdir "$ENGINE_DIR"
  fi
  local new="${ENGINE_DIR}.new.$$" old="${ENGINE_DIR}.old.$$"
  rm -rf "$new"; mkdir -p "$(dirname "$ENGINE_DIR")"
  cp -a "$src" "$new"
  rm -rf "$new/.git"
  if [ -e "$ENGINE_DIR" ]; then mv "$ENGINE_DIR" "$old"; fi
  mv "$new" "$ENGINE_DIR"
  rm -rf "$old"
}

install_from_tarball() {
  have curl || die "curl is needed for the tarball download."
  have tar  || die "tar is needed for the tarball download."
  local tmp; tmp="$(mktemp -d)"
  log "downloading ${TARBALL_URL}"
  curl -fsSL --max-time 300 "$TARBALL_URL" -o "$tmp/engine.tar.gz" || { rm -rf "$tmp"; die "download failed: ${TARBALL_URL}"; }
  mkdir "$tmp/x"
  tar -xzf "$tmp/engine.tar.gz" -C "$tmp/x" || { rm -rf "$tmp"; die "could not unpack the tarball."; }
  # GitHub archives unpack into one top folder (<repo>-<branch>/); accept a flat tarball too.
  local top="$tmp/x"
  if ! is_engine_dir "$top"; then
    top="$(find "$tmp/x" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  fi
  local rv lv; rv="$(tr -d ' \n\r' < "$top/VERSION" 2>/dev/null || echo "?")"; lv="$(local_version)"
  if is_engine_dir "$ENGINE_DIR" && [ "$rv" = "$lv" ] && [ ! -d "$ENGINE_DIR/.git" ]; then
    log "already at ${lv} (tarball install); nothing to replace."
  else
    install_from_tree "$top"
  fi
  rm -rf "$tmp"
  SOURCE_DESC="tarball ${TARBALL_URL}"
}

install_from_source_dir() {
  is_engine_dir "$SOURCE_DIR" || die "NOMAD_PRO_SOURCE_DIR=$SOURCE_DIR is not a Nomad Pro engine folder."
  local tmp; tmp="$(mktemp -d)"
  # copy without git metadata or bytecode
  (cd "$SOURCE_DIR" && tar --exclude=.git --exclude=__pycache__ --exclude='*.pyc' -cf - .) | (mkdir "$tmp/t" && cd "$tmp/t" && tar -xf -)
  if is_engine_dir "$ENGINE_DIR" && [ "$(local_version)" = "$(tr -d ' \n\r' < "$tmp/t/VERSION")" ] && diff -rq "$tmp/t" "$ENGINE_DIR" -x __pycache__ >/dev/null 2>&1; then
    log "already identical to ${SOURCE_DIR}; nothing to copy."
  else
    install_from_tree "$tmp/t"
  fi
  rm -rf "$tmp"
  SOURCE_DESC="local folder ${SOURCE_DIR}"
}

# ---------------------------------------------------------------- install / update
SOURCE_DESC=""
BEFORE="$(local_version)"
if [ -n "$SOURCE_DIR" ]; then
  install_from_source_dir
elif [ -d "$ENGINE_DIR/.git" ] && use_git; then
  log "updating git checkout in ${ENGINE_DIR}"
  if [ -n "$(git -C "$ENGINE_DIR" status --porcelain --untracked-files=no)" ]; then
    die "tracked files in ${ENGINE_DIR} were edited locally; not updating. Keep your own data outside the engine folder, then run: git -C \"${ENGINE_DIR}\" checkout -- . && bash install.sh"
  fi
  git -C "$ENGINE_DIR" pull --ff-only --quiet origin "$BRANCH" || die "git pull --ff-only failed (history diverged or network down). Nothing was changed."
  SOURCE_DESC="git $(git -C "$ENGINE_DIR" rev-parse --short HEAD)"
elif [ ! -e "$ENGINE_DIR" ] && use_git; then
  log "cloning ${REPO_URL} (${BRANCH}) into ${ENGINE_DIR}"
  mkdir -p "$(dirname "$ENGINE_DIR")"
  if git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$ENGINE_DIR"; then
    SOURCE_DESC="git $(git -C "$ENGINE_DIR" rev-parse --short HEAD)"
  else
    warn "git clone failed; falling back to the tarball."
    rm -rf "$ENGINE_DIR"
    install_from_tarball
  fi
else
  install_from_tarball
fi
AFTER="$(local_version)"
[ "$BEFORE" = "none" ] && log "installed ${AFTER}" || { [ "$BEFORE" = "$AFTER" ] && log "up to date at ${AFTER}" || log "updated ${BEFORE} -> ${AFTER}"; }

# ---------------------------------------------------------------- Python requirements
REQ="$ENGINE_DIR/tools/requirements.txt"
if [ "${NOMAD_PRO_SKIP_PIP:-0}" != "1" ] && [ -f "$REQ" ]; then
  if python3 - "$REQ" <<'PY' >/dev/null 2>&1
import sys, re
from importlib import metadata
for line in open(sys.argv[1]):
    name = re.split(r"[<>=!~;\[ ]", line.strip(), 1)[0]
    if name and not name.startswith("#"):
        metadata.version(name)
PY
  then
    log "Python requirements already present."
  else
    log "installing Python requirements (pip --user)"
    if ! python3 -m pip --version >/dev/null 2>&1; then
      python3 -m ensurepip --user >/dev/null 2>&1 || warn "pip is not available and could not be bootstrapped."
    fi
    if ! python3 -m pip install --user --quiet --no-warn-script-location -r "$REQ" 2>/tmp/nomad-pro-pip.$$; then
      if grep -q "externally-managed-environment" /tmp/nomad-pro-pip.$$; then
        # Debian/Ubuntu (PEP 668): --user still installs only into ~/.local, never system folders.
        python3 -m pip install --user --quiet --no-warn-script-location --break-system-packages -r "$REQ" \
          || warn "could not install requirements; PDF export may be unavailable (the engine's other tools still work)."
      else
        warn "could not install requirements ($(tail -n 1 /tmp/nomad-pro-pip.$$)); PDF export may be unavailable."
      fi
    fi
    rm -f /tmp/nomad-pro-pip.$$
  fi
fi

# ---------------------------------------------------------------- tests
TEST_STATUS="skipped"
if [ "${NOMAD_PRO_SKIP_TESTS:-0}" != "1" ]; then
  log "running the test suite"
  if (cd "$ENGINE_DIR" && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/tests -q) >/tmp/nomad-pro-tests.$$ 2>&1; then
    TEST_STATUS="passed ($(grep -Eo 'Ran [0-9]+ tests?' /tmp/nomad-pro-tests.$$ | head -n 1 || true))"
    grep -Eo 'skipped=[0-9]+' /tmp/nomad-pro-tests.$$ | head -n 1 | sed 's/^/  note: /' || true
  else
    TEST_STATUS="FAILED"
    tail -n 30 /tmp/nomad-pro-tests.$$ >&2
  fi
  rm -f /tmp/nomad-pro-tests.$$
fi

echo "Nomad Pro engine $(local_version) at ${ENGINE_DIR} (source: ${SOURCE_DESC:-unknown}; tests: ${TEST_STATUS})"
[ "$TEST_STATUS" = "FAILED" ] && exit 2
exit 0
