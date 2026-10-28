#!/usr/bin/env bash
# shellcheck disable=SC1090,SC2034,SC2154
STAGE=breeze-provider
download_artifact "10682012012" "daaa5abda5a8f824c6fa509142d7cd9132de213d782cb32e0561873f427aa577" "${WORK}/breeze"
BREEZE_THEME="$(find "${WORK}/breeze" -type f -name 'breeze-icon-theme_6.30.0-0supralinux1_all.deb' -print -quit)"
BREEZE_RCC="$(find "${WORK}/breeze" -type f -name 'breeze-icon-theme-rcc_6.30.0-0supralinux1_all.deb' -print -quit)"
BREEZE_LIB="$(find "${WORK}/breeze" -type f -name 'libkf6breezeicons6_6.30.0-0supralinux1_amd64.deb' -print -quit)"
BREEZE_DEV="$(find "${WORK}/breeze" -type f -name 'libkf6breezeicons-dev_6.30.0-0supralinux1_amd64.deb' -print -quit)"
BREEZE_SRC="$(find "${WORK}/breeze" -type f -name 'kf6-breeze-icons_6.30.0.orig.tar.xz' -print -quit)"
for f in "${BREEZE_THEME}" "${BREEZE_RCC}" "${BREEZE_LIB}" "${BREEZE_DEV}" "${BREEZE_SRC}"; do [[ -s "${f}" ]]; done
printf '%s  %s\n' '308a20089ef387da2d5ba08b42be4299dd62fe5f5535786a0d8881d93b0d1e09' "${BREEZE_THEME}" | sha256sum --check --strict
printf '%s  %s\n' 'b5105c4deb0b120b8bd08550f1d79e9db79069503e1eb08992da867380f1df8a' "${BREEZE_RCC}" | sha256sum --check --strict
printf '%s  %s\n' '39843417452315f82dda133b09d1b588a5d23d44095ff821e63ee7943075b232' "${BREEZE_LIB}" | sha256sum --check --strict
printf '%s  %s\n' '46974cd2a2e7fb22fabf5332fcf51b560a9c03fca4c1cc3eff014cd5b0336a1b' "${BREEZE_DEV}" | sha256sum --check --strict
printf '%s  %s\n' '93866c19791838fc9757b305e010e23bb38cb5f201e4ecc96cc8ef5f1173ebe6' "${BREEZE_SRC}" | sha256sum --check --strict
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  "${BREEZE_THEME}" "${BREEZE_RCC}" "${BREEZE_LIB}" "${BREEZE_DEV}"
[[ "$(dpkg-query -W -f='${Version}' breeze-icon-theme)" == '4:6.30.0-0supralinux1' ]]
[[ "$(dpkg-query -W -f='${Version}' libkf6breezeicons-dev)" == '4:6.30.0-0supralinux1' ]]

STAGE=breeze-source-proof
mkdir -p "${WORK}/breeze-source"
tar -xJf "${BREEZE_SRC}" --strip-components=1 -C "${WORK}/breeze-source"
python3 - "${WORK}/breeze-source/icons/breezeicons.cpp" "${EVIDENCE}/breeze-source-proof.json" <<'PY'
import json,sys
from pathlib import Path
text=Path(sys.argv[1]).read_text()
checks={
  "resource_init":'Q_INIT_RESOURCE(breeze_icons);' in text,
  "reads_fallback":'QIcon::fallbackThemeName()' in text,
  "accepts_empty_or_hicolor":'fallbackTheme.isEmpty() || fallbackTheme == QLatin1String("hicolor")' in text,
  "sets_breeze_fallback":'QIcon::setFallbackThemeName(QStringLiteral("breeze"));' in text,
}
if not all(checks.values()): raise SystemExit(f"unexpected BreezeIcons source shape: {checks}")
Path(sys.argv[2]).write_text(json.dumps({"source_sha256":"93866c19791838fc9757b305e010e23bb38cb5f201e4ecc96cc8ef5f1173ebe6","checks":checks},indent=2,sort_keys=True)+"\n")
PY

STAGE=kiconthemes-source-proof
download_artifact "10731249726" "5b06a92638fb67409710b140f3ebc597400d0d739db497e3d570fbe42cfa5206" "${WORK}/kiconthemes"
KICONS_SRC="$(find "${WORK}/kiconthemes" -type f -name 'kf6-kiconthemes_6.30.0.orig.tar.xz' -print -quit)"
[[ -s "${KICONS_SRC}" ]]
printf '%s  %s\n' 'c0c684823d0e087f35168cd79f1053fd358bb8fb47b27996a11c7d7ee3da6f4d' "${KICONS_SRC}" | sha256sum --check --strict
mkdir -p "${WORK}/kiconthemes-source"
tar -xJf "${KICONS_SRC}" --strip-components=1 -C "${WORK}/kiconthemes-source"
python3 - "${WORK}/kiconthemes-source/src/kicontheme.cpp" "${EVIDENCE}/kiconthemes-source-proof.json" <<'PY'
import json,sys
from pathlib import Path
text=Path(sys.argv[1]).read_text()
call=text.find('BreezeIcons::initIcons();')
ret=text.find('if (!initThemeUsed)',call)
checks={
  "startup_function":'Q_COREAPP_STARTUP_FUNCTION(initThemeHelper)' in text,
  "startup_calls_breeze_init":call >= 0,
  "breeze_init_precedes_initThemeUsed_guard":call >= 0 and ret > call,
}
if not all(checks.values()): raise SystemExit(f"unexpected KIconThemes source shape: {checks}")
Path(sys.argv[2]).write_text(json.dumps({"source_sha256":"c0c684823d0e087f35168cd79f1053fd358bb8fb47b27996a11c7d7ee3da6f4d","checks":checks},indent=2,sort_keys=True)+"\n")
PY


source "${ROOT}/scripts/run-kde-tier3-kio-round15-probe.sh"
