#!/usr/bin/env bash
# Source this file to configure your shell, or execute it before a command.

_menagerie_x_hhtools_env() {
    local script_dir repo_root
    script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || return
    repo_root="$(cd -- "$script_dir/.." && pwd -P)" || return
    export HHTOOLS_ROBOT_DIR="$repo_root/robots"
}

if ! _menagerie_x_hhtools_env; then
    unset -f _menagerie_x_hhtools_env
    return 1 2>/dev/null || exit 1
fi
unset -f _menagerie_x_hhtools_env

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    if (( $# == 0 )); then
        echo 'Usage: source scripts/hhtools-env.sh' >&2
        echo '   or: scripts/hhtools-env.sh <command> [arguments...]' >&2
        exit 2
    fi
    exec "$@"
fi
