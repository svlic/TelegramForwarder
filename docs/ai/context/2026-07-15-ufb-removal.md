# UFB module full removal

Date: 2026-07-15

## Decision

User does not use UniversalForumBlock (UFB). Remove the entire integration rather than leave half-dead hooks.

## Why full removal

- UFB was optional side-channel keyword sync over websockets, not core forwarding.
- Keeping `is_ufb` / commands / env flags without a client would create dead UI and maintenance cost.
- Historical bugs (keyword add rollback when UFB sync failed, blocking IO in event loop) disappear with the module.

## Removed

### Code
- `ufb/` directory (`UFBClient`, websocket sync)
- `models/db_operations.py`: `init_ufb`, `sync_to_server`, `sync_from_json`, `UFBClient` usage; `create()` is now plain `return cls()`
- `models/models.py`: `is_ufb`, `ufb_domain`, `ufb_item` columns + migration entries
- Handlers: `/ufb_bind`, `/ufb_unbind`, `/ufb_item_change` and aliases `ub`/`uu`/`uic`
- Button callbacks: toggle UFB, ufb item change, settings row for UFB
- `main.py` BotCommands for UFB
- Help text UFB section in `command_handlers.py`

### Config / deps
- `.env.example`: `UFB_ENABLED`, `UFB_SERVER_URL`, `UFB_TOKEN`
- `utils/constants.py`: same env constants
- `docker-compose.yml`: `./ufb/config` volume
- `requirements.txt`: `websockets`
- `.dockerignore` / `.gitignore`: ufb path entries

### Docs
- `README.md`: feature bullet, env block, settings row, UFB special section, command list
- `AGENTS.md`: structure entry replaced with "do not reintroduce UFB"

## Tradeoffs

- Existing SQLite DBs may still have unused `is_ufb` / `ufb_domain` / `ufb_item` columns. Safe to leave; schema no longer creates or migrates them.
- Historical notes under `docs/ai/context/*` still mention UFB as past review context; not rewritten.

## Verification

- Grep on `*.py`, `*.yml`, `*.txt`, `.env.example`, docker/gitignore: no runtime UFB symbols
- `ForwardRule` has no ufb columns in ORM
- `DBOperations` has no `sync_to_server` / `init_ufb` / `sync_from_json`
- Tests: `21 passed` (`.venv/bin/python -m pytest tests/ -q`)
