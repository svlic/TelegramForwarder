# Review fixes: 1 / 3 / 6 / 7 / D / E

Date: 2026-07-10

## Scope

Minimal fixes for review items 1, 3, 6, 7, D, E (no unrelated cleanup).

## Changes

### 1. `/clear_all` child tables
- File: `handlers/command_handlers.py` → `perform_clear_all`
- Deletes `MediaTypes`, `MediaExtensions`, `RuleSync` before `ReplaceRule` / `Keyword` / `ForwardRule` / `Chat`
- Avoids orphan FK rows when wiping all rules

### 3. FilterChain media cleanup
- Files: `filters/context.py` (`cleanup_media_files`), `filters/filter_chain.py` (`finally`)
- Always removes leftover `context.media_files` even if a mid-chain filter aborts or raises
- Idempotent if `SenderFilter` already deleted the files

### 6. Regex timeout / bounds
- New: `utils/regex_safety.py` — thread-pool timeout (1s), max pattern 500, max input 100k
- Wired into `utils/common.py` `check_keyword_match` and `filters/replace_filter.py`
- On timeout: same fail-closed semantics as bad regex (whitelist reject / blacklist match)
- `ai_filter.py` prompt placeholder `re.search` left alone (fixed internal patterns, not user input)

### 7. `add_keywords` duplicate key includes `is_regex`
- File: `models/db_operations.py`
- Duplicate check is `(rule_id, keyword, is_regex, is_blacklist)` for main + sync paths
- Plain and regex keywords with the same text can coexist

### D. Delete index sort + dedup
- `delete_keywords` / `delete_replace_rules`: `sorted(set(indices), reverse=True)`
- Prevents wrong deletes when user passes duplicates or ascending multi-indices

### E. InitFilter no longer swallows exceptions
- File: `filters/init_filter.py`
- Removed `try/finally: return True` that suppressed outer exceptions
- Media-group collection errors still caught locally and recorded on `context.errors`

## Tests

- `tests/test_review_fixes_1_3_6_7_d_e.py`

## Tradeoffs

- Regex timeout uses `ThreadPoolExecutor`; a timed-out worker thread may keep running until the engine returns (CPython cannot kill threads). Bounds reduce risk; true kill would need a process pool or a C extension.
- Pattern/input length caps may reject legitimate huge patterns; 500/100k is intentional safety default.
