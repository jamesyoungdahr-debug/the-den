#!/bin/bash
# Runs every headless check against a running backend. Needs the system PySide6 +
# Kirigami QML modules (see README) and, when the server requires sign-in, an admin
# API token from the profile page:
#
#   DEN_URL=http://127.0.0.1:8686 DEN_API_TOKEN=... tests/run_all.sh
#
# Model tests talk to the backend directly; qml_harness.py compiles every page against
# the real models; screenshot_app.py walks the whole app and writes a PNG per page.
cd "$(dirname "$0")/.."
export QT_QPA_PLATFORM=offscreen DEN_URL="${DEN_URL:-http://127.0.0.1:8686}"
fail=0
for t in tests/check_*.py tests/qml_harness.py; do
    printf "%-48s " "$t"
    if out=$(timeout 180 python3 -u "$t" 2>&1); then echo "ok"; else fail=$((fail+1)); echo "FAIL"; echo "$out" | tail -15; fi
done
printf "%-48s " "tests/screenshot_app.py"
if timeout 240 python3 -u tests/screenshot_app.py "${SCREENS:-/tmp/the-den-client-screens}" >/dev/null 2>&1; then echo "ok (PNGs in ${SCREENS:-/tmp/the-den-client-screens})"; else fail=$((fail+1)); echo "FAIL"; fi
echo; [ $fail -eq 0 ] && echo "all green" || echo "$fail failed"
exit $fail
