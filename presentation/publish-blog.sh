#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf 'Usage: %s [--publish "commit message"]\n' "$0"
    printf 'Build the slides, copy them into blog_contents, and build Hugo.\n'
    printf 'Set BLOG_REPO to use a different blog checkout.\n'
    printf 'With --publish, run the blog publisher to commit and push both blog repositories.\n'
}

publish=false
message=''
if [[ $# -gt 0 ]]; then
    case "$1" in
    --help | -h)
        usage
        exit 0
        ;;
    --publish)
        if [[ $# -ne 2 || -z "$2" ]]; then
            usage >&2
            exit 2
        fi
        publish=true
        message="$2"
        ;;
    *)
        usage >&2
        exit 2
        ;;
    esac
fi

for tool in bun hugo rsync; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Error: %s is required on PATH.\n' "$tool" >&2
        exit 1
    fi
done

presentation_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
blog_repo="${BLOG_REPO:-${presentation_dir}/../../blog_contents}"
if [[ ! -f "${blog_repo}/config.yaml" || ! -d "${blog_repo}/static" ]]; then
    printf 'Error: BLOG_REPO must point to the blog checkout with config.yaml and static/: %s\n' "$blog_repo" >&2
    exit 1
fi
blog_repo="$(cd "$blog_repo" && pwd)"

if [[ -L "${blog_repo}/static/kubecon-na26" ]]; then
    printf 'Error: the generated deck directory must not be a symlink.\n' >&2
    exit 1
fi
if [[ "$publish" == true && ! -x "${blog_repo}/hack/build-and-publish.sh" ]]; then
    printf 'Error: the blog publisher is missing or not executable.\n' >&2
    exit 1
fi

cd "$presentation_dir"
bun install --frozen-lockfile
bun run build --base /kubecon-na26/ --router-mode hash
rsync -a --delete dist/ "${blog_repo}/static/kubecon-na26/"

if [[ "$publish" == true ]]; then
    "${blog_repo}/hack/build-and-publish.sh" "$message"
    printf 'Pushed blog updates. GitHub Pages will deploy https://suraj.io/kubecon-na26/\n'
else
    (cd "$blog_repo" && hugo)
    printf 'Built slides at %s/public/kubecon-na26/index.html\n' "$blog_repo"
    printf 'Run with --publish "commit message" to publish to https://suraj.io/kubecon-na26/\n'
fi
