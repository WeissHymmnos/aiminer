# Update 5

## 目标

修复 Web 前端 `Stop Run` 不生效或状态显示异常的问题，并把 stop 状态机收敛到前后端一致。

## 变更文件

- `api.py`
- `tests/unit/test_api_contract.py`
- `frontend/src/lib/api.ts`
- `frontend/src/components/Layout.tsx`
- `frontend/src/pages/SwarmRunDetailPage.tsx`
- `frontend/src/pages/SwarmRunsPage.tsx`
- `instruction.md`

## 主要更新内容

- 后端 stop 状态机改为两阶段
  - `POST /api/swarm/runs/{run_id}/stop` 在进程仍存活时不再直接写最终 `stopped`。
  - 先写 `stopping` 并广播停止中事件。
  - 只有 `_wait_run_process()` 确认子进程退出后，才把状态最终落成 `stopped`。

- 修复 `status` 与 `is_active` 的矛盾态
  - 补齐状态归一化逻辑。
  - 不再允许出现 `status=stopped` 但 `is_active=true` 的结果。
  - 对历史脏 manifest 也能自动归一化为 `stopping` 或最终态。

- 恢复前端鉴权头注入
  - `frontend/src/lib/api.ts` 恢复 token 读取与存储方法。
  - 所有请求现在都会自动附带：
    - `Authorization: Bearer <token>`
    - `X-API-Key: <token>`
  - `Layout` 恢复 `API Token` 输入框，写入 `localStorage`。

- 修复 stop 按钮反馈逻辑
  - `SwarmRunsPage` 和 `SwarmRunDetailPage` 统一通过状态视图函数渲染运行状态。
  - stop 发出后立即进入本地 `stopping` 反馈。
  - 按钮文案区分：
    - `Sending Stop...`
    - `Stopping...`
    - `Stop Run`
  - 只有 run 真正进入最终停止态后，按钮才切换为删除逻辑。

- 补充回归测试
  - 新增 stop 活跃 run 时返回 `stopping` 的测试。
  - 新增 stop 后 watcher 收口为 `stopped` 的测试。

## 验证

- `pytest -q tests/unit/test_api_contract.py`
- 结果：`15 passed`

## 影响范围

- 用户侧：前端 stop run 的行为和显示状态恢复一致。
- API 侧：stop 从“同步最终态”改为“异步两阶段状态机”。
- 文档侧：`instruction.md` 已同步更新 stop 状态说明、token 注入说明和页面行为说明。

## 后续建议

- 前端再做一次端到端联调，确认 `stopping -> stopped -> delete` 的完整按钮切换链路。
- 若后续引入更细粒度运维态，可扩展 `paused/cancelling` 等中间状态，但要保持前后端统一枚举。 
