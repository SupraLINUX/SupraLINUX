#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

bundle="build/ksq-1/technical-acceptance-bundle"
archive="build/ksq-1/aurora-ksq-1-technical-acceptance.tar.gz"
archive_sha="${archive}.sha256"

rm -rf "${bundle}"
rm -f "${archive}" "${archive_sha}"
mkdir -p \
  "${bundle}/metadata" \
  "${bundle}/repository" \
  "${bundle}/candidate/debs" \
  "${bundle}/candidate/range-evidence" \
  "${bundle}/candidate/kwallet-validation" \
  "${bundle}/candidate/original-full-validation-artifact" \
  "${bundle}/candidate/revalidated-full" \
  "${bundle}/reference/debs" \
  "${bundle}/reference/range-evidence" \
  "${bundle}/reproducibility/acceptance-artifact" \
  "${bundle}/reproducibility/revalidated-acceptance" \
  "${bundle}/reproducibility/dedicated-proofs" \
  "${bundle}/ksq0/regression" \
  "${bundle}/ksq0/normalized"

git diff --quiet
git diff --cached --quiet
git status --porcelain=v1 --untracked-files=no > "${bundle}/metadata/git-status.txt"
[[ ! -s "${bundle}/metadata/git-status.txt" ]]
git rev-parse HEAD > "${bundle}/metadata/acceptance-head.txt"
git archive --format=tar.gz --output="${bundle}/repository/repository-snapshot.tar.gz" HEAD

cp -a .github/ksq-1-acceptance-runs.env "${bundle}/metadata/"
cp -a build/ksq-1/technical-acceptance/technical-acceptance-status.env "${bundle}/metadata/"
cp -a build/ksq-1/technical-acceptance/run-provenance-status.env "${bundle}/metadata/"
cp -a build/ksq-1/technical-acceptance/run-provenance.json "${bundle}/metadata/"
cp -a build/ksq-1/technical-acceptance/run-provenance.sha256 "${bundle}/metadata/"

cp -a build/ksq-1/full/debs/. "${bundle}/candidate/debs/"
cp -a build/ksq-1/full/evidence-artifacts/. "${bundle}/candidate/range-evidence/"
cp -a build/ksq-1/full/kwallet-validation/. "${bundle}/candidate/kwallet-validation/"
cp -a build/ksq-1/original-full-validation-artifact/. "${bundle}/candidate/original-full-validation-artifact/"

cp -a build/ksq-1/reference/debs/. "${bundle}/reference/debs/"
cp -a build/ksq-1/reference/evidence-artifacts/. "${bundle}/reference/range-evidence/"

cp -a build/ksq-1/repro/acceptance-artifact/. "${bundle}/reproducibility/acceptance-artifact/"
cp -a build/ksq-1/repro/revalidated-acceptance/. "${bundle}/reproducibility/revalidated-acceptance/"
cp -a build/ksq-1/repro/dedicated-proofs/. "${bundle}/reproducibility/dedicated-proofs/"
cp -a build/ksq-1/ksq0-regression/. "${bundle}/ksq0/regression/"
cp -a build/ksq-1/ksq0-normalized/. "${bundle}/ksq0/normalized/"

for name in full-build-manifest.tsv full-binary-packages.tsv full-debs.sha256 full-build-status.env; do
  [[ -f "build/ksq-1/full/${name}" ]]
  cp -a "build/ksq-1/full/${name}" "${bundle}/candidate/revalidated-full/${name}"
done

cat > "${bundle}/metadata/integrity-model.env" <<'EOF'
AURORA_KSQ_1_BUNDLE_PAYLOAD_DIGEST=sha256
AURORA_KSQ_1_BUNDLE_PAYLOAD_MANIFEST=bundle-files.sha256
AURORA_KSQ_1_BUNDLE_ARCHIVE_DIGEST=sha256
AURORA_KSQ_1_BUNDLE_ARCHIVE_SIDECAR=aurora-ksq-1-technical-acceptance.tar.gz.sha256
AURORA_KSQ_1_BUNDLE_GITHUB_ARTIFACT_DIGEST=external-trust-root
EOF

cat > "${bundle}/VERIFY.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT}"
sha256sum -c bundle-files.sha256
(
  cd metadata
  sha256sum -c run-provenance.sha256
)
grep -Fxq 'AURORA_KSQ_1_TECHNICAL_ACCEPTANCE=PASS' metadata/technical-acceptance-status.env
grep -Fxq 'AURORA_KSQ_1_TECHNICAL_ACCEPTANCE_PROVENANCE=PASS' metadata/technical-acceptance-status.env
grep -Fxq 'AURORA_KSQ_1_RUN_PROVENANCE_STATUS=PASS' metadata/run-provenance-status.env
grep -Fxq 'AURORA_KSQ_1_REPRODUCIBILITY_STATUS=PASS' reproducibility/revalidated-acceptance/reproducibility-status.env
grep -Fxq 'AURORA_KSQ_1_REPRODUCIBILITY_BYTE_IDENTICAL=yes' reproducibility/revalidated-acceptance/reproducibility-status.env
grep -Fxq 'AURORA_KSQ_1_FULL_BUILD_STATUS=PASS' candidate/revalidated-full/full-build-status.env
grep -Fxq 'AURORA_KSQ_1_FULL_BUILD_KWALLET_PAM=PASS' candidate/revalidated-full/full-build-status.env
grep -Fxq 'AURORA_KSQ_1_KWALLET_BINARY_RUNTIME_DEPS=PASS' candidate/kwallet-validation/status.env
grep -Fxq 'AURORA_KSQ_1_KWALLET_PAM_INSTALLATION=PASS' candidate/kwallet-validation/status.env
grep -Fxq 'AURORA_KSQ_0_CLOSURE_STATUS=COMPLETE' ksq0/normalized/closure-status.env
grep -Fxq 'AURORA_KSQ_0_CLOSURE_SOURCES=101' ksq0/normalized/closure-status.env
grep -Fxq 'AURORA_KSQ_0_CLOSURE_UNRESOLVED=0' ksq0/normalized/closure-status.env
[[ "$(wc -l < reproducibility/revalidated-acceptance/reproducibility-manifest.tsv)" -eq 102 ]]
[[ "$(wc -l < ksq0/normalized/unresolved.tsv)" -eq 1 ]]
echo AURORA_KSQ_1_ACCEPTANCE_BUNDLE_VERIFY_SUCCESS
EOF
chmod 0755 "${bundle}/VERIFY.sh"

(
  cd "${bundle}"
  find . -type f ! -name bundle-files.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum > bundle-files.sha256
  sha256sum -c bundle-files.sha256
  ./VERIFY.sh
)

(
  cd build/ksq-1
  tar \
    --sort=name \
    --mtime='@0' \
    --owner=0 \
    --group=0 \
    --numeric-owner \
    -cf - technical-acceptance-bundle \
    | gzip -n > aurora-ksq-1-technical-acceptance.tar.gz
  sha256sum aurora-ksq-1-technical-acceptance.tar.gz \
    > aurora-ksq-1-technical-acceptance.tar.gz.sha256
  sha256sum -c aurora-ksq-1-technical-acceptance.tar.gz.sha256
)

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
tar -xzf "${archive}" -C "${tmp}"
"${tmp}/technical-acceptance-bundle/VERIFY.sh"

echo AURORA_KSQ_1_ACCEPTANCE_BUNDLE_SELF_VERIFIED
