# 2026-04-29 Bug Review Fixes

## Context
A bug review found two high-confidence issues in the message forwarding path:

1. `MediaFilter` can mark a message as blocked by setting `context.should_forward = False`, `context.media_blocked = True`, or `context.skipped_media`, but the chain continues into `EditFilter` before `SenderFilter` performs the final send/no-send guard.
2. `message_listener.py` used `normalize_channel_id()` without importing it. The same active-state branch also reused the normalized channel ID for database lookup, while `/bind` stores raw Telethon chat IDs.

## Decisions
- `EditFilter` now exits before editing when previous filters have marked the message as non-forwardable or media-restricted.
- `EditFilter` keeps EDIT mode terminal: once an EDIT-mode rule is handled or skipped for any reason (prior blocking decision, not a channel, no user client, text unchanged, or after successful/failed edit), the filter chain stops with `return False` before `SenderFilter` to avoid editing and forwarding the same source message.
- `message_listener.py` imports `normalize_channel_id` and separates the raw `chat_id` used for database/rule lookup from `state_chat_id` used for state-manager reads and clears.
- This is intentionally minimal: it preserves existing database storage compatibility instead of migrating all stored chat IDs.

## Verification
Run syntax compilation and inspect diffs after the patch. LSP diagnostics are unavailable in this environment because `basedpyright-langserver` is not installed.
