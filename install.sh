#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./install.sh [--target DIR] [--method symlink|copy] [--force] <skill> [<skill> ...]
  ./install.sh [--target DIR] [--method symlink|copy] [--force] --all
  ./install.sh --list

Options:
  --target DIR        Install into DIR. Default: ~/.codex/skills
  --method METHOD     Install via symlink or copy. Default: symlink
  --force             Replace existing target skill directory
  --all               Install all skills in this repo
  --list              Print available skills
  -h, --help          Show this help
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_TARGET="${HOME}/.codex/skills"
TARGET_DIR="${DEFAULT_TARGET}"
METHOD="symlink"
FORCE=0
INSTALL_ALL=0

available_skills() {
  find "${SCRIPT_DIR}" -mindepth 1 -maxdepth 1 -type d ! -name '.git' ! -name '__pycache__' -exec test -f '{}/SKILL.md' ';' -print | xargs -n1 basename | sort
}

print_list() {
  available_skills
}

fail() {
  echo "Error: $*" >&2
  exit 1
}

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      [[ $# -ge 2 ]] || fail "--target requires a directory"
      TARGET_DIR="$2"
      shift 2
      ;;
    --method)
      [[ $# -ge 2 ]] || fail "--method requires symlink or copy"
      METHOD="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --all)
      INSTALL_ALL=1
      shift
      ;;
    --list)
      print_list
      exit 0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

case "${METHOD}" in
  symlink|copy)
    ;;
  *)
    fail "--method must be symlink or copy"
    ;;
esac

if [[ ${INSTALL_ALL} -eq 1 ]]; then
  mapfile -t SKILLS < <(available_skills)
else
  SKILLS=("${ARGS[@]}")
fi

[[ ${#SKILLS[@]} -gt 0 ]] || fail "no skills selected; use --list to inspect available skills"

mkdir -p "${TARGET_DIR}"

for skill in "${SKILLS[@]}"; do
  SRC="${SCRIPT_DIR}/${skill}"
  DEST="${TARGET_DIR}/${skill}"

  [[ -d "${SRC}" ]] || fail "skill not found: ${skill}"
  [[ -f "${SRC}/SKILL.md" ]] || fail "missing SKILL.md for skill: ${skill}"

  if [[ -e "${DEST}" || -L "${DEST}" ]]; then
    if [[ ${FORCE} -eq 1 ]]; then
      rm -rf "${DEST}"
    else
      fail "target already exists: ${DEST} (use --force to replace)"
    fi
  fi

  if [[ "${METHOD}" == "symlink" ]]; then
    ln -s "${SRC}" "${DEST}"
  else
    cp -R "${SRC}" "${DEST}"
  fi

  echo "Installed ${skill} -> ${DEST} (${METHOD})"
done
