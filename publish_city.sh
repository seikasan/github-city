#!/usr/bin/env bash
# Update only the generated-image branch. No main-branch commits or force push.
set -euo pipefail
city_source="$(realpath "${1:-dist/city.svg}")"
test -s "$city_source"
city_branch="city-art"
city_publish_dir="$(mktemp -d)"
trap 'git worktree remove --force "$city_publish_dir" >/dev/null 2>&1 || true' EXIT
city_remote_ref="$(git ls-remote --heads origin "refs/heads/$city_branch")"
if [[ -n "$city_remote_ref" ]]; then
  git fetch --no-tags origin "$city_branch"
  git worktree add --detach "$city_publish_dir" FETCH_HEAD
else
  git worktree add --detach "$city_publish_dir" HEAD
  git -C "$city_publish_dir" checkout --orphan "$city_branch"
  git -C "$city_publish_dir" rm -rf --ignore-unmatch .
fi
cp "$city_source" "$city_publish_dir/city.svg"
git -C "$city_publish_dir" add city.svg
if git -C "$city_publish_dir" diff --cached --quiet; then
  echo 'City SVG is unchanged.'
  exit 0
fi
git -C "$city_publish_dir" -c user.name='github-actions[bot]' \
  -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
  commit -m 'Update GitHub city'
git -C "$city_publish_dir" push origin "HEAD:refs/heads/$city_branch"
