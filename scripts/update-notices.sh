#!/usr/bin/env bash
set -euo pipefail

# Generate / update the repo-root NOTICES file.
#
# Includes fixed notices for:
#   - Alpine base image (Dockerfile uses python:*-alpine)
#   - Impeccable design skill (Apache-2.0; UI design guidance)
# then Python dependency notices from requirements.txt via pip-licenses
# (https://pypi.org/project/pip-licenses/).
#
# Usage (from repository root):
#   ./scripts/update-notices.sh
#   ./scripts/update-notices.sh --output NOTICES
#   ./scripts/update-notices.sh --python .venv/bin/python

OUTPUT="NOTICES"
PYTHON=""

for arg in "$@"; do
  case "$arg" in
    --output=*)
      OUTPUT="${arg#--output=}"
      ;;
    --python=*)
      PYTHON="${arg#--python=}"
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/update-notices.sh [--output=NOTICES] [--python=PATH]

Regenerate third-party Python license/NOTICE text with pip-licenses.

Options:
  --output=PATH   Output file (default: NOTICES at repo root)
  --python=PATH   Python interpreter whose site-packages to scan
                  (default: temporary venv with requirements.txt)
  -h, --help      Show this help

Always install deps into a clean env (temp venv or your project venv)
before scanning so the NOTICES file matches what the app ships.
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

require_cmd python3
[[ -f requirements.txt ]] || fail "requirements.txt not found in repository root."

TMP_DIR=""
cleanup() {
  if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}
trap cleanup EXIT

if [[ -z "${PYTHON}" ]]; then
  require_cmd python3
  TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/aegis-notices.XXXXXX")"
  python3 -m venv "${TMP_DIR}/venv"
  # shellcheck disable=SC1091
  source "${TMP_DIR}/venv/bin/activate"
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r requirements.txt "pip-licenses>=5.0" >/dev/null
  PYTHON="$(command -v python)"
else
  [[ -x "${PYTHON}" ]] || fail "Python not executable: ${PYTHON}"
  "${PYTHON}" -m pip show pip-licenses >/dev/null 2>&1 || \
    fail "pip-licenses is not installed for ${PYTHON}. Install with: ${PYTHON} -m pip install pip-licenses"
fi

TMP_JSON="$(mktemp)"
TMP_BODY="$(mktemp)"
"${PYTHON}" -m piplicenses \
  --from=mixed \
  --format=json \
  --with-license-file \
  --with-notice-file \
  --no-license-path \
  --output-file="${TMP_JSON}"

"${PYTHON}" - "${TMP_JSON}" "${TMP_BODY}" <<'PY'
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
packages = json.loads(open(src, encoding="utf-8").read())
divider = "-" * 80
blocks = []
for pkg in packages:
    name = pkg.get("Name") or "UNKNOWN"
    version = pkg.get("Version") or ""
    license_name = pkg.get("License") or "UNKNOWN"
    license_text = (pkg.get("LicenseText") or "").strip()
    notice_text = (pkg.get("NoticeText") or "").strip()
    if notice_text.upper() == "UNKNOWN":
        notice_text = ""

    lines = [name, version, license_name, ""]
    if license_text and license_text.upper() != "UNKNOWN":
        lines.append(license_text)
        lines.append("")
    if notice_text:
        lines.append("NOTICE:")
        lines.append(notice_text)
        lines.append("")
    blocks.append("\n".join(lines).rstrip() + "\n")

open(dst, "w", encoding="utf-8").write(("\n" + divider + "\n\n").join(blocks))
PY

{
  cat <<EOF
Third-party notices for Aegis-KeePass OTP Sync
==============================================

This file lists third-party notices for:
  1. The Alpine Linux base used by the published Docker image (Dockerfile)
  2. Impeccable design skill guidance used for the UI (Apache-2.0)
  3. Python packages from requirements.txt (and transitive deps), via pip-licenses

Regenerate with:

  ./scripts/update-notices.sh

Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

--------------------------------------------------------------------------------

Alpine Linux (Docker base image)
python:*-alpine (official Docker Hub image)
Mixed (distribution + package licenses)

The published container image (\`ghcr.io/wsj-br/aegis-keepass\`) is built \`FROM
python:*-alpine\`, which is based on Alpine Linux.

Alpine Linux is a community-developed Linux distribution built around musl libc
and BusyBox. See: https://www.alpinelinux.org/about/

Key components commonly present in Alpine / python-alpine images include (not
exhaustive; package set varies by tag):

  - Alpine aports / packaging infrastructure — often MIT / OSI-permissive for
    Alpine project material; individual packages keep their own licenses.
  - musl libc — MIT
    https://musl.libc.org/
  - BusyBox — GPL-2.0-only
    https://busybox.net/license.html
  - apk-tools and other Alpine packages — see each package license

For the exact package list and licenses inside a built image:

  docker run --rm --entrypoint sh IMAGE -c 'apk info -v && apk info -a busybox'

Package index: https://pkgs.alpinelinux.org/

This section is a distribution attribution for the Docker base OS. It does not
reproduce every Alpine system package license text (that set is defined by the
base image tag, not by this repository's requirements.txt).

--------------------------------------------------------------------------------

Impeccable
https://github.com/pbakaus/impeccable
Apache-2.0

Copyright 2025 Paul Bakaus

UI design guidance for this project draws on Impeccable
(https://impeccable.style), an Apache-2.0 licensed design skill pack.
Source: https://github.com/pbakaus/impeccable

Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to the Licensor for inclusion in the Work by the copyright
      owner or by an individual or Legal Entity authorized to submit on
      behalf of the copyright owner. For the purposes of this definition,
      "submitted" means any form of electronic, verbal, or written
      communication sent to the Licensor or its representatives, including
      but not limited to communication on electronic mailing lists, source
      code control systems, and issue tracking systems that are managed by,
      or on behalf of, the Licensor for the purpose of discussing and
      improving the Work, but excluding communication that is conspicuously
      marked or otherwise designated in writing by the copyright owner as
      "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   Copyright 2025 Paul Bakaus

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

--------------------------------------------------------------------------------

EOF
  cat "${TMP_BODY}"
} > "${OUTPUT}"

rm -f "${TMP_JSON}" "${TMP_BODY}"

echo "Wrote ${OUTPUT}"
