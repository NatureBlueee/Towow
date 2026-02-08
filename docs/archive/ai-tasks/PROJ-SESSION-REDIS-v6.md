# PROJ-SESSION-REDIS-v6: Redis Session 存储迁移项目计划

## 文档元信息

- **项目 ID**: SESSION-REDIS
- **版本**: v6
- **状态**: ACTIVE
- **创建日期**: 2026-01-30 16:43 CST
- **关联文档**:
  - 技术方案: `.ai/TECH-SESSION-REDIS-v6.md`
  - 任务文档: `.ai/TASK-REDIS-001.md` ~ `.ai/TASK-REDIS-006.md`

---

## 1. 项目概述

### 1.1 项目目标

将 Session 存储从内存迁移到 Redis，实现：
1. **持久化**: Session 数据在服务重启后不丢失
2. **可扩展**: 支持多实例部署时 Session 共享
3. **高可用**: Redis 不可用时自动降级到内存存储
4. **可配置**: 通过环境变量灵活切换存储后端

### 1.2 成功指标

- [ ] 所有 Session 操作通过抽象接口完成
- [ ] Redis 存储正常工作时，Session 在服务重启后保持
- [ ] Redis 不可用时，自动降级到内存存储且不影响服务
- [ ] 单元测试覆盖率 > 80%

---

## 2. 范围说明

### 2.1 本期包含

| 范围内 | 说明 |
|--------|------|
| SessionStore 抽象接口 | 统一的 Session 存储 API |
| MemorySessionStore 实现 | 开发环境/降级用 |
| RedisSessionStore 实现 | 生产环境 |
| app.py 集成 | 替换内存 Session 存储 |
| oauth2_client.py 集成 | 替换 OAuth2 State 存储 |
| 集成测试与文档 | 验证与文档更新 |

### 2.2 本期不包含

| 范围外 | 原因 |
|--------|------|
| Redis 集群配置 | 后续迭代 |
| Session 加密 | 后续迭代 |
| 分布式锁 | 当前场景不需要 |
| Token 存储 | 不在本次范围 |
| 监控告警 | 后续迭代 |

---

## 3. Task 对齐表

### 3.1 TASK -> Beads 对齐表

| TASK ID | Beads ID | 任务名称 | 优先级 | 状态 |
|---------|----------|----------|--------|------|
| TASK-REDIS-001 | `towow-lw6` | SessionStore 抽象接口 | P0 | open |
| TASK-REDIS-002 | `towow-8sh` | MemorySessionStore 实现 | P1 | open |
| TASK-REDIS-003 | `towow-3gj` | RedisSessionStore 实现 | P1 | open |
| TASK-REDIS-004 | `towow-l2y` | app.py 集成 | P1 | open |
| TASK-REDIS-005 | `towow-ahn` | oauth2_client.py 集成 | P1 | open |
| TASK-REDIS-006 | `towow-6fw` | 集成测试与文档 | P2 | open |

### 3.2 依赖关系图

```
Phase 1: 基础设施
+-- TASK-REDIS-001 (towow-lw6): SessionStore 抽象接口 [P0]

Phase 2: 存储实现（可并行）
+-- TASK-REDIS-002 (towow-8sh): MemorySessionStore <-- 001
+-- TASK-REDIS-003 (towow-3gj): RedisSessionStore <-- 001

Phase 3: 集成（可并行）
+-- TASK-REDIS-004 (towow-l2y): app.py 集成 <-- 001 (接口依赖: 002, 003)
+-- TASK-REDIS-005 (towow-ahn): oauth2_client.py 集成 <-- 001 (接口依赖: 002, 003)

Phase 4: 测试与文档
+-- TASK-REDIS-006 (towow-6fw): 集成测试与文档 <-- 002, 003, 004, 005
```

### 3.3 beads 依赖设置记录

```bash
# 硬依赖设置（已执行）
bd dep add towow-8sh towow-lw6   # 002 -> 001
bd dep add towow-3gj towow-lw6   # 003 -> 001
bd dep add towow-l2y towow-lw6   # 004 -> 001
bd dep add towow-ahn towow-lw6   # 005 -> 001
bd dep add towow-6fw towow-8sh   # 006 -> 002
bd dep add towow-6fw towow-3gj   # 006 -> 003
bd dep add towow-6fw towow-l2y   # 006 -> 004
bd dep add towow-6fw towow-ahn   # 006 -> 005
```

**接口依赖说明**（契约先行，不设置 beads 依赖）：
- TASK-REDIS-004 和 005 对 002、003 是接口依赖
- 可以在 001 完成后立即启动，使用桩实现
- 002、003 完成后进行接口联调验证

---

## 4. 执行进度表

| TASK ID | Beads ID | 状态 | Owner | 预计工时 | 阻塞点 |
|---------|----------|------|-------|----------|--------|
| TASK-REDIS-001 | `towow-lw6` | TODO | [TBD] | 1-2h | - |
| TASK-REDIS-002 | `towow-8sh` | TODO | [TBD] | 2-3h | 等待 001 |
| TASK-REDIS-003 | `towow-3gj` | TODO | [TBD] | 2-3h | 等待 001 |
| TASK-REDIS-004 | `towow-l2y` | TODO | [TBD] | 3-4h | 等待 001 |
| TASK-REDIS-005 | `towow-ahn` | TODO | [TBD] | 2-3h | 等待 001 |
| TASK-REDIS-006 | `towow-6fw` | TODO | [TBD] | 2-3h | 等待 002-005 |

**总预计工时**: 12-18 小时

---

## 5. 执行计划

### 5.1 执行批次（无限 AI Dev 场景）

#### 第一批（立即可启动）
- **TASK-REDIS-001** (towow-lw6): SessionStore 抽象接口
  - 无依赖，可立即启动
  - 预计 1-2 小时

#### 第二批（等待第一批完成）
可并行启动：
- **TASK-REDIS-002** (towow-8sh): MemorySessionStore 实现
- **TASK-REDIS-003** (towow-3gj): RedisSessionStore 实现
- **TASK-REDIS-004** (towow-l2y): app.py 集成
- **TASK-REDIS-005** (towow-ahn): oauth2_client.py 集成

#### 第三批（等待第二批完成）
- **TASK-REDIS-006** (towow-6fw): 集成测试与文档

### 5.2 接口依赖验证约定

| 被依赖任务 | 接口依赖任务 | 验证状态 | 验证时间点 |
|-----------|-------------|---------|-----------|
| TASK-REDIS-002 | TASK-REDIS-004 | 待验证 | 002 完成后 |
| TASK-REDIS-002 | TASK-REDIS-005 | 待验证 | 002 完成后 |
| TASK-REDIS-003 | TASK-REDIS-004 | 待验证 | 003 完成后 |
| TASK-REDIS-003 | TASK-REDIS-005 | 待验证 | 003 完成后 |

---

## 6. 里程碑

| 里程碑 | 完成标准 | 目标日期 |
|--------|----------|----------|
| M1: 接口定义完成 | TASK-REDIS-001 完成 | [TBD] |
| M2: 存储实现完成 | TASK-REDIS-002, 003 完成 | [TBD] |
| M3: 集成完成 | TASK-REDIS-004, 005 完成 | [TBD] |
| M4: 测试与上线 | TASK-REDIS-006 完成 | [TBD] |

---

## 7. Gate 检查点

### Gate A（进入实现前）
- [x] 技术方案文档: `TECH-SESSION-REDIS-v6.md`
- [x] 任务拆解完成: 6 个 TASK
- [x] beads 任务创建并关联
- [x] 依赖关系设置完成

### Gate B（P0/P1 进入 DONE 前）
- [ ] 对应 AC 的测试用例与结果
- [ ] 真数据真流程验证
- [ ] 回滚方案确认

### Gate C（方向偏差时）
- 触发条件：发现"不是想要的"或关键分叉决策改变
- 必须动作：升版本并记录变更点

---

## 8. 风险与预案

| 风险 | 影响 | 概率 | 预案 |
|------|------|------|------|
| Redis 连接不稳定 | Session 丢失 | 中 | 自动降级 + 重连机制 |
| 内存存储数据丢失 | 用户需重新登录 | 高（重启时） | 提示用户，非阻塞 |
| Redis 序列化问题 | 数据读取失败 | 低 | 统一使用 JSON 序列化 |

---

## 9. 验收检查点（禁止 Mock）

- [ ] 前端是否调用真实后端 API？
- [ ] 后端是否返回真实数据结构？
- [ ] 是否进行了真数据端到端验证？

---

## 10. 变更记录

| 日期 | 变更内容 | 决策人 |
|------|----------|--------|
| 2026-01-30 | 初始版本，创建项目计划 | proj |

