# TASK-REDIS-006: 集成测试与文档

> Beads 任务ID: `towow-6fw`

## 任务信息

- **任务 ID**: TASK-REDIS-006
- **所属 Epic**: SESSION-REDIS
- **状态**: pending
- **优先级**: P2

## 任务描述

完成集成测试和文档更新。

## 验收标准

- [ ] 集成测试：内存模式正常工作
- [ ] 集成测试：Redis 模式正常工作
- [ ] 集成测试：自动降级正常工作
- [ ] 更新 `.env.example` 添加新环境变量
- [ ] 更新 README 添加 Redis 配置说明
- [ ] 更新 CLAUDE.md 添加 Session 存储说明

## 依赖关系

- **硬依赖**: TASK-REDIS-002, 003, 004, 005
- **接口依赖**: 无
- **可并行**: 无

## 测试场景

### 1. 内存模式测试

```bash
SESSION_STORE_TYPE=memory uvicorn web.app:app --reload
```

- 登录功能正常
- 服务重启后 Session 丢失（预期行为）

### 2. Redis 模式测试

```bash
SESSION_STORE_TYPE=redis REDIS_URL=redis://localhost:6379/0 uvicorn web.app:app --reload
```

- 登录功能正常
- 服务重启后 Session 保持

### 3. 自动降级测试

```bash
SESSION_STORE_TYPE=auto REDIS_URL=redis://invalid:6379/0 uvicorn web.app:app --reload
```

- 服务正常启动（降级到内存）
- 日志显示降级警告

## 文档更新

### .env.example

```bash
# Session 存储配置
SESSION_STORE_TYPE=auto  # auto/redis/memory
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=towow:
```

## 预计工作量

2-3 小时
