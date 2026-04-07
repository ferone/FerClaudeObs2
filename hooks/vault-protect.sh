#!/bin/bash
# Blocks edits to confidential vault zones and protected files.
# Used as a PreToolUse hook for Edit|Write operations.
# Exit 2 = block the action. Exit 0 = allow.

# Requires jq for JSON parsing — fail open if missing
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Block edits to paths containing INTERNAL or CONFIDENTIAL
case "$FILE_PATH" in
  *INTERNAL*|*CONFIDENTIAL*)
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"Protected vault zone: path contains INTERNAL or CONFIDENTIAL. These files cannot be edited without manual intervention.\"}}"
    exit 2
    ;;
esac

# Block edits to _TEMPLATES/
case "$FILE_PATH" in
  *_TEMPLATES/*|*/_TEMPLATES/*)
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"Cannot edit files inside _TEMPLATES/ — templates are managed by the user. Use explicit user instruction to modify.\"}}"
    exit 2
    ;;
esac

# Block edits to HOME.md
BASENAME=$(basename "$FILE_PATH")
case "$BASENAME" in
  HOME.md)
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"Cannot edit HOME.md — this is the vault home page and must be edited manually.\"}}"
    exit 2
    ;;
esac

exit 0
