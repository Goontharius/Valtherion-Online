#!/usr/bin/env bash
# usb-test.sh — one-shot bring-up for a USB deploy of Valtherion to an Android phone.
# Assumes: phone plugged in + USB debugging authorized, backend reachable on 127.0.0.1:8000,
# Metro running on 8081, and a fresh debug APK built.
set -euo pipefail
ADB="${ADB:-/Users/tfe/android-sdk/platform-tools/adb}"
MOBILE_DIR="$(cd "$(dirname "$0")" && pwd)"
APK="$MOBILE_DIR/android/app/build/outputs/apk/debug/app-debug.apk"

echo "▶ Waiting for device…"
"$ADB" wait-for-device
"$ADB" devices -l

echo "▶ Setting up reverse port forwarding (phone localhost:8000 -> Mac 127.0.0.1:8000)"
"$ADB" reverse tcp:8000 tcp:8000
echo "   reverse list:"; "$ADB" reverse --list

echo "▶ Installing debug APK…"
"$ADB" install -r "$APK"

echo "▶ Verifying backend on the phone's view (via reverse):"
if "$ADB" shell "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/" 2>/dev/null; then
  echo "   backend reachable"
else
  echo "   (curl not on device; install and let app verify)"
fi

echo "✅ USB test armed. Backend:127.0.0.1:8000 · APK:$APK".
echo "   Launch via: $ADB shell am start -n com.valtherion.online/.MainActivity"
