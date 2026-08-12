# Agent 知识库精简

## 背景

根 `AGENTS.md` 同时包含项目地图、业务流程、通用编码理念、历史防回归备注和易漂移的版本元数据，导致关键信息不突出，并且已有内容与当前实现不一致。

## 调整

- 根文件只保留 agent 开工时需要的入口、硬约束、验证命令和文档维护规则。
- 将消息处理顺序及跨模块状态契约移到 `kb/docs/message-processing.md`。
- 删除版本、提交号、固定过滤器数量等高漂移信息。
- 修正过滤链遗漏的 `TextNormalizeFilter`，并将旧版 `docker-compose` 命令改为 Docker Compose v2 的 `docker compose`。
- 删除不符合当前代码的“过滤器外禁止数据库会话”和不存在的 `clear_group_cache()` 说明，改为以 `get_db_session()` 和会话边界为约束。
- 将“每次改动都建上下文文档”收窄为仅记录架构决策或非显然 trade-off，避免文档噪声。

## 维护原则

根 `AGENTS.md` 应保持短小稳定；流程细节进入 `kb/docs/`，用户行为进入 `README.md`，历史决策进入 `docs/ai/context/`。代码变化后只更新对应层级，不在根文件复制大段实现细节。
