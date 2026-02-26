#!/bin/bash
# iOS build validation hook — runs after swift-ios-frontend agent stops.
# Skipped if the agent already ran xcodebuild in its session.

INPUT=$(cat)

TRANSCRIPT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('agent_transcript_path', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

# If the agent already ran xcodebuild, skip to avoid a redundant build.
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ] && grep -q "xcodebuild" "$TRANSCRIPT" 2>/dev/null; then
    echo "xcodebuild already run by swift-ios-frontend agent — skipping hook build."
    exit 0
fi

echo "swift-ios-frontend agent did not run xcodebuild — running build validation now..."

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

xcodebuild \
    -project "$PROJECT_ROOT/ios/BudgetMasterApp/Budget Chat.xcodeproj" \
    -scheme "Budget Chat" \
    -destination "platform=iOS Simulator,name=iPhone 17 Pro,OS=26.0" \
    build 2>&1
