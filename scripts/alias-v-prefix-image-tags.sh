#!/usr/bin/env bash
# Alias bare-semver container tags (1.3.0, 1.3, 1.0.0-rc.1) to the documented
# v-prefixed names (v1.3.0, v1.3, v1.0.0-rc.1) without rebuilding.
#
# Why: docker/metadata-action's type=semver strips the leading v from git tags,
# so historical GHCR publishes used :1.3.0 while docs/compose pin IMAGE_TAG=v1.3.0.
# Re-running a past tag workflow is not enough — Actions uses the workflow file
# at the tagged commit, which still had bare-semver patterns for those releases.
#
# Usage:
#   REGISTRIES='ghcr.io/sturmi77' SOURCE_TAGS='1.3.0 1.3' \
#     ./scripts/alias-v-prefix-image-tags.sh
#
# Env:
#   REGISTRIES    space-separated registry/owner prefixes (required)
#   IMAGES        space-separated image names (default: correlcore-api correlcore-web)
#   SOURCE_TAGS   space-separated bare semver tags to alias, incl. prerelease
#                 (required), e.g. '1.3.0 1.3 1.0.0-rc.1'
#   DRY_RUN       if 1, only print actions (default: 0)
#   FAIL_ON_ERROR if 1, exit non-zero on first alias failure (default: 0)
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
FAIL_ON_ERROR="${FAIL_ON_ERROR:-0}"
IMAGES="${IMAGES:-correlcore-api correlcore-web}"
REGISTRIES="${REGISTRIES:-}"
SOURCE_TAGS="${SOURCE_TAGS:-}"

if [[ -z "${REGISTRIES}" ]]; then
  echo "REGISTRIES is required (e.g. 'ghcr.io/sturmi77')" >&2
  exit 2
fi

if [[ -z "${SOURCE_TAGS}" ]]; then
  echo "SOURCE_TAGS is required (space-separated bare semver tags, e.g. '1.3.0 1.3')" >&2
  exit 2
fi

tag_exists() {
  local ref="$1"
  docker buildx imagetools inspect "${ref}" >/dev/null 2>&1
}

aliased=0
skipped_missing_src=0
skipped_exists=0
skipped_invalid=0
failed=0

for registry in ${REGISTRIES}; do
  for image in ${IMAGES}; do
    for bare in ${SOURCE_TAGS}; do
      # Bare semver: major.minor, major.minor.patch, and prerelease
      # major.minor.patch-<pre> (e.g. 1.0.0-rc.1). The digits.digits anchor
      # still never rewrites sha-/latest/main.
      if [[ ! "${bare}" =~ ^[0-9]+\.[0-9]+(\.[0-9]+(-[0-9A-Za-z.-]+)?)?$ ]]; then
        echo "skip (not bare semver): ${bare}"
        skipped_invalid=$((skipped_invalid + 1))
        continue
      fi

      src="${registry}/${image}:${bare}"
      dst="${registry}/${image}:v${bare}"

      if ! tag_exists "${src}"; then
        echo "skip (source missing): ${src}"
        skipped_missing_src=$((skipped_missing_src + 1))
        continue
      fi

      if tag_exists "${dst}"; then
        echo "skip (already present): ${dst}"
        skipped_exists=$((skipped_exists + 1))
        continue
      fi

      if [[ "${DRY_RUN}" == "1" ]]; then
        echo "dry-run alias: ${dst} <- ${src}"
        aliased=$((aliased + 1))
        continue
      fi

      echo "alias: ${dst} <- ${src}"
      if docker buildx imagetools create -t "${dst}" "${src}"; then
        aliased=$((aliased + 1))
      else
        echo "ERROR: failed to alias ${dst} from ${src}" >&2
        failed=$((failed + 1))
        if [[ "${FAIL_ON_ERROR}" == "1" ]]; then
          exit 1
        fi
      fi
    done
  done
done

echo "alias-v-prefix done aliased=${aliased} skipped_exists=${skipped_exists} skipped_missing_src=${skipped_missing_src} skipped_invalid=${skipped_invalid} failed=${failed} dry_run=${DRY_RUN}"
if [[ "${failed}" -gt 0 ]]; then
  exit 1
fi
