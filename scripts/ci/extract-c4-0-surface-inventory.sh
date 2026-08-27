#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "extract-c4-0-surface-inventory.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
IMAGE="${BUILD_DIR}/aurora-c4-0-rootfs.img"
INVENTORY_DIR="${BUILD_DIR}/c4-0-inventory"
MOUNT_DIR="${BUILD_DIR}/aurora-c4-0-post-rootfs"
DPKG_ADMINDIR="${MOUNT_DIR}/var/lib/dpkg"

mkdir -p "${INVENTORY_DIR}" "${MOUNT_DIR}"

cleanup() {
  set +e
  if mountpoint -q "${MOUNT_DIR}"; then
    umount "${MOUNT_DIR}" >/dev/null 2>&1 || umount -l "${MOUNT_DIR}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ ! -f "${IMAGE}" ]]; then
  echo "AURORA_C4_0_EXTENDED_INVENTORY_SKIPPED=image-missing"
  exit 0
fi

mount -o loop,ro "${IMAGE}" "${MOUNT_DIR}"
[[ -r "${DPKG_ADMINDIR}/status" ]] || {
  echo "AURORA_C4_0_EXTENDED_INVENTORY_FAILURE=dpkg-status-missing" >&2
  exit 1
}

package_version() {
  local package="$1"
  dpkg-query --admindir="${DPKG_ADMINDIR}" -W -f='${Version}' "${package}" 2>/dev/null || true
}

emit_owner_rows_for_exact_path() {
  local surface_kind="$1"
  local surface_id="$2"
  local path="$3"
  local output="$4"
  local unresolved="$5"
  local matches line owner_field owner version found=0

  matches="$(dpkg-query --admindir="${DPKG_ADMINDIR}" -S "${path}" 2>/dev/null || true)"
  while IFS= read -r line; do
    [[ -n "${line}" ]] || continue
    owner_field="${line%: *}"
    IFS=',' read -ra owner_candidates <<<"${owner_field}"
    for owner in "${owner_candidates[@]}"; do
      owner="${owner#${owner%%[![:space:]]*}}"
      owner="${owner%${owner##*[![:space:]]}}"
      [[ -n "${owner}" ]] || continue
      version="$(package_version "${owner}")"
      printf '%s\t%s\t%s\t%s\t%s\n' \
        "${surface_kind}" "${surface_id}" "${owner}" "${version:-UNKNOWN}" "${path}" >>"${output}"
      found=1
    done
  done <<<"${matches}"

  if [[ "${found}" -eq 0 ]]; then
    printf '%s\t%s\t%s\n' "${surface_kind}" "${surface_id}" "${path}" >>"${unresolved}"
  fi
}

first_owner_for_exact_path() {
  local path="$1"
  local line owner
  line="$(dpkg-query --admindir="${DPKG_ADMINDIR}" -S "${path}" 2>/dev/null | head -n1 || true)"
  [[ -n "${line}" ]] || return 0
  owner="${line%: *}"
  owner="${owner%%,*}"
  owner="${owner#${owner%%[![:space:]]*}}"
  owner="${owner%${owner##*[![:space:]]}}"
  printf '%s' "${owner}"
}

desktop_key() {
  local file="$1"
  local key="$2"
  awk -v key="${key}" '
    BEGIN { in_desktop=0 }
    /^\[Desktop Entry\][[:space:]]*$/ { in_desktop=1; next }
    /^\[/ { if (in_desktop) exit; next }
    in_desktop && index($0, key "=") == 1 {
      sub(/^[^=]*=/, "")
      gsub(/[\t\r\n]/, " ")
      print
      exit
    }
  ' "${file}" 2>/dev/null || true
}

# KCM ownership/version evidence. Match exact plugin/desktop/JSON basenames only;
# substring matching is intentionally forbidden because IDs such as kcm_network
# and kcm_networkmanagement coexist in the Plasma stack.
: >"${INVENTORY_DIR}/kcm-package-owners.tsv"
: >"${INVENTORY_DIR}/kcm-desktop-metadata.tsv"
: >"${INVENTORY_DIR}/unresolved-kcm-owners.txt"
printf 'KIND\tSURFACE_ID\tPACKAGE\tVERSION\tPATH\n' >>"${INVENTORY_DIR}/kcm-package-owners.tsv"
printf 'SURFACE_ID\tPACKAGE\tVERSION\tPATH\tNAME\tCOMMENT\tNO_DISPLAY\tONLY_SHOW_IN\tNOT_SHOW_IN\tPARENT_APP\tSYSTEM_SETTINGS_PARENT_CATEGORY\tKINFOCENTER_CATEGORY\tCATEGORIES\tEXEC\n' >>"${INVENTORY_DIR}/kcm-desktop-metadata.tsv"
if [[ -r "${INVENTORY_DIR}/actual-kcms.txt" ]]; then
  while IFS= read -r kcm_id; do
    [[ -n "${kcm_id}" ]] || continue
    found_path=0
    while IFS= read -r host_path; do
      [[ -n "${host_path}" ]] || continue
      found_path=1
      rel="${host_path#${MOUNT_DIR}}"
      emit_owner_rows_for_exact_path KCM "${kcm_id}" "${rel}" \
        "${INVENTORY_DIR}/kcm-package-owners.tsv" "${INVENTORY_DIR}/unresolved-kcm-owners.txt"

      if [[ "${rel}" == *.desktop ]]; then
        owner="$(first_owner_for_exact_path "${rel}")"
        version="$(package_version "${owner}")"
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
          "${kcm_id}" "${owner:-UNKNOWN}" "${version:-UNKNOWN}" "${rel}" \
          "$(desktop_key "${host_path}" Name)" \
          "$(desktop_key "${host_path}" Comment)" \
          "$(desktop_key "${host_path}" NoDisplay)" \
          "$(desktop_key "${host_path}" OnlyShowIn)" \
          "$(desktop_key "${host_path}" NotShowIn)" \
          "$(desktop_key "${host_path}" X-KDE-ParentApp)" \
          "$(desktop_key "${host_path}" X-KDE-System-Settings-Parent-Category)" \
          "$(desktop_key "${host_path}" X-KDE-KInfoCenter-Category)" \
          "$(desktop_key "${host_path}" Categories)" \
          "$(desktop_key "${host_path}" Exec)" \
          >>"${INVENTORY_DIR}/kcm-desktop-metadata.tsv"
      fi
    done < <(
      find \
        "${MOUNT_DIR}/usr/lib" \
        "${MOUNT_DIR}/usr/share/applications" \
        "${MOUNT_DIR}/usr/share/kservices5" \
        "${MOUNT_DIR}/usr/share/kservices6" \
        -type f \( \
          -name "${kcm_id}.so" -o \
          -name "${kcm_id}.desktop" -o \
          -name "${kcm_id}.json" \
        \) -print 2>/dev/null | sort -u
    )
    if [[ "${found_path}" -eq 0 ]]; then
      printf 'KCM\t%s\tPATH_NOT_FOUND\n' "${kcm_id}" >>"${INVENTORY_DIR}/unresolved-kcm-owners.txt"
    fi
  done <"${INVENTORY_DIR}/actual-kcms.txt"
else
  echo "AURORA_C4_0_EXTENDED_INVENTORY_WARNING=actual-kcms-missing"
fi

# Portal descriptor ownership/version evidence.
: >"${INVENTORY_DIR}/portal-package-owners.tsv"
: >"${INVENTORY_DIR}/unresolved-portal-owners.txt"
printf 'KIND\tSURFACE_ID\tPACKAGE\tVERSION\tPATH\n' >>"${INVENTORY_DIR}/portal-package-owners.tsv"
if [[ -r "${INVENTORY_DIR}/actual-portals.txt" ]]; then
  while IFS= read -r portal_id; do
    [[ -n "${portal_id}" ]] || continue
    portal_path="/usr/share/xdg-desktop-portal/portals/${portal_id}.portal"
    emit_owner_rows_for_exact_path PORTAL "${portal_id}" "${portal_path}" \
      "${INVENTORY_DIR}/portal-package-owners.tsv" "${INVENTORY_DIR}/unresolved-portal-owners.txt"
  done <"${INVENTORY_DIR}/actual-portals.txt"
else
  echo "AURORA_C4_0_EXTENDED_INVENTORY_WARNING=actual-portals-missing"
fi

# KWin package metadata and compiled plugin files relevant to configurable surfaces.
: >"${INVENTORY_DIR}/kwin-surface-files.tsv"
: >"${INVENTORY_DIR}/unresolved-kwin-surface-owners.txt"
printf 'KIND\tSURFACE_ID\tPACKAGE\tVERSION\tPATH\n' >>"${INVENTORY_DIR}/kwin-surface-files.tsv"
if [[ -d "${MOUNT_DIR}/usr/share/kwin" ]]; then
  while IFS= read -r host_path; do
    rel="${host_path#${MOUNT_DIR}}"
    parent="$(basename "$(dirname "${rel}")")"
    grandparent="$(basename "$(dirname "$(dirname "${rel}")")")"
    surface_id="${grandparent}:${parent}"
    emit_owner_rows_for_exact_path KWIN_METADATA "${surface_id}" "${rel}" \
      "${INVENTORY_DIR}/kwin-surface-files.tsv" "${INVENTORY_DIR}/unresolved-kwin-surface-owners.txt"
  done < <(find "${MOUNT_DIR}/usr/share/kwin" -type f \( -name metadata.json -o -name metadata.desktop \) -print | sort)
fi
while IFS= read -r host_path; do
  rel="${host_path#${MOUNT_DIR}}"
  surface_id="$(basename "${rel}")"
  emit_owner_rows_for_exact_path KWIN_PLUGIN "${surface_id}" "${rel}" \
    "${INVENTORY_DIR}/kwin-surface-files.tsv" "${INVENTORY_DIR}/unresolved-kwin-surface-owners.txt"
done < <(find "${MOUNT_DIR}/usr/lib" -type f -path '*/qt6/plugins/kwin/*' -print 2>/dev/null | sort)

# QML/package plasmoids.
: >"${INVENTORY_DIR}/plasma-plasmoid-surfaces.tsv"
: >"${INVENTORY_DIR}/unresolved-plasma-surface-owners.txt"
printf 'KIND\tSURFACE_ID\tPACKAGE\tVERSION\tPATH\n' >>"${INVENTORY_DIR}/plasma-plasmoid-surfaces.tsv"
if [[ -d "${MOUNT_DIR}/usr/share/plasma/plasmoids" ]]; then
  while IFS= read -r host_path; do
    rel="${host_path#${MOUNT_DIR}}"
    surface_id="$(basename "$(dirname "${rel}")")"
    emit_owner_rows_for_exact_path PLASMOID "${surface_id}" "${rel}" \
      "${INVENTORY_DIR}/plasma-plasmoid-surfaces.tsv" "${INVENTORY_DIR}/unresolved-plasma-surface-owners.txt"
  done < <(find "${MOUNT_DIR}/usr/share/plasma/plasmoids" -mindepth 2 -maxdepth 2 -type f \( -name metadata.json -o -name metadata.desktop \) -print | sort)
fi

# Plasma 6 can ship C++ applets as compiled plugins with embedded metadata.
: >"${INVENTORY_DIR}/plasma-applet-plugin-surfaces.tsv"
: >"${INVENTORY_DIR}/unresolved-plasma-applet-plugin-owners.txt"
printf 'KIND\tSURFACE_ID\tPACKAGE\tVERSION\tPATH\n' >>"${INVENTORY_DIR}/plasma-applet-plugin-surfaces.tsv"
while IFS= read -r host_path; do
  rel="${host_path#${MOUNT_DIR}}"
  surface_id="$(basename "${rel}" .so)"
  emit_owner_rows_for_exact_path PLASMA_APPLET_PLUGIN "${surface_id}" "${rel}" \
    "${INVENTORY_DIR}/plasma-applet-plugin-surfaces.tsv" "${INVENTORY_DIR}/unresolved-plasma-applet-plugin-owners.txt"
done < <(find "${MOUNT_DIR}/usr/lib" -type f -path '*/qt6/plugins/plasma/applets/*.so' -print 2>/dev/null | sort)

# KDED plugins are desktop integration services even when they have no standalone UI.
: >"${INVENTORY_DIR}/kded-plugin-surfaces.tsv"
: >"${INVENTORY_DIR}/unresolved-kded-plugin-owners.txt"
printf 'KIND\tSURFACE_ID\tPACKAGE\tVERSION\tPATH\n' >>"${INVENTORY_DIR}/kded-plugin-surfaces.tsv"
while IFS= read -r host_path; do
  rel="${host_path#${MOUNT_DIR}}"
  surface_id="$(basename "${rel}" .so)"
  emit_owner_rows_for_exact_path KDED_PLUGIN "${surface_id}" "${rel}" \
    "${INVENTORY_DIR}/kded-plugin-surfaces.tsv" "${INVENTORY_DIR}/unresolved-kded-plugin-owners.txt"
done < <(find "${MOUNT_DIR}/usr/lib" -type f -path '*/qt6/plugins/kf6/kded/*.so' -print 2>/dev/null | sort)

# Dolphin/KIO user-facing integration actions, properties pages and protocol workers.
: >"${INVENTORY_DIR}/kio-service-menu-surfaces.tsv"
: >"${INVENTORY_DIR}/kio-protocol-surfaces.tsv"
: >"${INVENTORY_DIR}/kio-plugin-surfaces.tsv"
: >"${INVENTORY_DIR}/unresolved-kio-surface-owners.txt"
printf 'KIND\tSURFACE_ID\tPACKAGE\tVERSION\tPATH\n' >>"${INVENTORY_DIR}/kio-service-menu-surfaces.tsv"
printf 'KIND\tSURFACE_ID\tPACKAGE\tVERSION\tPATH\n' >>"${INVENTORY_DIR}/kio-protocol-surfaces.tsv"
printf 'KIND\tSURFACE_ID\tPACKAGE\tVERSION\tPATH\n' >>"${INVENTORY_DIR}/kio-plugin-surfaces.tsv"
for dir in \
  "${MOUNT_DIR}/usr/share/kio/servicemenus" \
  "${MOUNT_DIR}/usr/share/kservices5/ServiceMenus" \
  "${MOUNT_DIR}/usr/share/kservices6/ServiceMenus" \
  "${MOUNT_DIR}/usr/share/dolphin/servicemenus"; do
  [[ -d "${dir}" ]] || continue
  while IFS= read -r host_path; do
    rel="${host_path#${MOUNT_DIR}}"
    surface_id="$(basename "${rel}")"
    emit_owner_rows_for_exact_path KIO_SERVICE_MENU "${surface_id}" "${rel}" \
      "${INVENTORY_DIR}/kio-service-menu-surfaces.tsv" "${INVENTORY_DIR}/unresolved-kio-surface-owners.txt"
  done < <(find "${dir}" -maxdepth 1 -type f -name '*.desktop' -print | sort)
done
while IFS= read -r host_path; do
  rel="${host_path#${MOUNT_DIR}}"
  surface_id="$(basename "${rel}")"
  emit_owner_rows_for_exact_path KIO_PROTOCOL "${surface_id}" "${rel}" \
    "${INVENTORY_DIR}/kio-protocol-surfaces.tsv" "${INVENTORY_DIR}/unresolved-kio-surface-owners.txt"
done < <(find "${MOUNT_DIR}/usr/share" -type f -name '*.protocol' \( -path '*/kio/*' -o -path '*/kservices*/*' \) -print 2>/dev/null | sort)

for spec in \
  'KIO_WORKER|*/qt6/plugins/kf6/kio/*.so' \
  'KIO_FILEITEMACTION|*/qt6/plugins/kf6/kfileitemaction/*.so' \
  'KIO_PROPERTIESDIALOG|*/qt6/plugins/kf6/propertiesdialog/*.so'; do
  kind="${spec%%|*}"
  pattern="${spec#*|}"
  while IFS= read -r host_path; do
    rel="${host_path#${MOUNT_DIR}}"
    surface_id="$(basename "${rel}" .so)"
    emit_owner_rows_for_exact_path "${kind}" "${surface_id}" "${rel}" \
      "${INVENTORY_DIR}/kio-plugin-surfaces.tsv" "${INVENTORY_DIR}/unresolved-kio-surface-owners.txt"
  done < <(find "${MOUNT_DIR}/usr/lib" -type f -path "${pattern}" -print 2>/dev/null | sort)
done

# Raw path snapshots make the structured extraction auditable if KDE moves metadata
# between directories in a later Plasma 6.6 or Frameworks 6 SRU.
find "${MOUNT_DIR}/usr/share/kwin" -type f -printf '%p\n' 2>/dev/null \
  | sed "s#^${MOUNT_DIR}##" | sort >"${INVENTORY_DIR}/kwin-files.txt" || true
find "${MOUNT_DIR}/usr/share/plasma/plasmoids" -type f -printf '%p\n' 2>/dev/null \
  | sed "s#^${MOUNT_DIR}##" | sort >"${INVENTORY_DIR}/plasma-plasmoid-files.txt" || true

printf 'AURORA_C4_0_EXTENDED_INVENTORY_KCM_OWNER_UNRESOLVED=%s\n' "$(wc -l <"${INVENTORY_DIR}/unresolved-kcm-owners.txt")"
printf 'AURORA_C4_0_EXTENDED_INVENTORY_PORTAL_OWNER_UNRESOLVED=%s\n' "$(wc -l <"${INVENTORY_DIR}/unresolved-portal-owners.txt")"
printf 'AURORA_C4_0_EXTENDED_INVENTORY_KWIN_OWNER_UNRESOLVED=%s\n' "$(wc -l <"${INVENTORY_DIR}/unresolved-kwin-surface-owners.txt")"
printf 'AURORA_C4_0_EXTENDED_INVENTORY_PLASMA_OWNER_UNRESOLVED=%s\n' "$(wc -l <"${INVENTORY_DIR}/unresolved-plasma-surface-owners.txt")"
printf 'AURORA_C4_0_EXTENDED_INVENTORY_PLASMA_APPLET_PLUGIN_OWNER_UNRESOLVED=%s\n' "$(wc -l <"${INVENTORY_DIR}/unresolved-plasma-applet-plugin-owners.txt")"
printf 'AURORA_C4_0_EXTENDED_INVENTORY_KDED_OWNER_UNRESOLVED=%s\n' "$(wc -l <"${INVENTORY_DIR}/unresolved-kded-plugin-owners.txt")"
printf 'AURORA_C4_0_EXTENDED_INVENTORY_KIO_OWNER_UNRESOLVED=%s\n' "$(wc -l <"${INVENTORY_DIR}/unresolved-kio-surface-owners.txt")"
echo "AURORA_C4_0_EXTENDED_INVENTORY_SUCCESS"
