# 研究文档 005：WOWOK Machine 智能合约参考

**日期**: 2026-02-18
**状态**: 参考文档
**用途**: 模块二结晶实验 Phase 3（方案生成 → JSON 输出）的格式参考

---

## 概述

WOWOK Machine 是运行在 SUI 区块链上的工作流智能合约框架。核心概念：

- **Machine = 模板**（节点 + 转换 + 权限 + 守卫），发布后不可变
- **Progress = 执行实例**，每个任务/订单创建一个，跟踪当前节点和权重累积
- **Node = 工作流阶段**，通过 pairs（入边）和 forwards（可执行动作）连接
- **Guard = 链上布尔条件**，gate forward 的执行
- **namedOperator = 角色模板**，Machine 中定义角色名，Progress 中绑定实际地址

### 与通爻模块二的关系

结晶收敛后，方案生成 Agent 输出协作构型。这个构型需要格式化为 WOWOK Machine JSON，使每个参与者的任务/收益/成本成为链上可执行的智能合约。

映射关系：
```
结晶产出的"谁做什么" → Machine 的 nodes（工作流阶段）
参与者的角色 → namedOperator（角色模板）
任务依赖关系 → pairs（节点间的转换条件）
验收条件 → threshold + weight（加权投票逻辑）
约束条件 → Guard（链上布尔验证）
```

---

## SDK 与 MCP

### 安装

```bash
# TypeScript SDK
npm i wowok_agent@latest    # JSON-driven wrapper
npm i wowok                 # 核心 SDK

# MCP Server（独立运行，无需安装）
npx -y wowok_machine_mcp_server
```

### MCP 配置

```json
{
  "mcpServers": {
    "wowok_machine": {
      "command": "npx",
      "args": ["-y", "wowok_machine_mcp_server"],
      "disabled": false
    }
  }
}
```

MCP 暴露一个工具：`machine_operations`，接受完整的 Machine JSON schema。

### 完整 MCP 生态

| 包名 | 用途 |
|------|------|
| `wowok_machine_mcp_server` | Machine + Progress 操作 |
| `wowok_permission_mcp_server` | 权限管理 |
| `wowok_guard_mcp_server` | Guard 创建 |
| `wowok_service_mcp_server` | Service（商店）管理 |
| `wowok_treasury_mcp_server` | 资金管理 |
| `wowok_repository_mcp_server` | 链上数据存储 |
| `wowok_demand_mcp_server` | 需求表达 |
| `wowok_personal_mcp_server` | 个人信息 + 账户管理 |
| `wowok_query_mcp_server` | 只读查询 |

---

## Machine JSON Schema

### 顶层结构

```json
{
  "account": "wallet_name_or_address",
  "data": {
    "object": "<name_or_address> 或 { name, onChain, permission, tags }",
    "description": "工作流描述",
    "endpoint": "https://api.example.com/callbacks",
    "bPublished": false,
    "bPaused": false,
    "nodes": { "op": "add", "bReplace": false, "data": [/* nodes */] },
    "consensus_repository": { "op": "add", "objects": ["repo_name"] },
    "clone_new": { "namedNew": { "name": "...", "onChain": true } },
    "progress_new": { /* 创建 Progress */ },
    "progress_namedOperator": { /* 绑定角色 */ },
    "progress_next": { /* 推进工作流 */ },
    "progress_hold": { /* 暂停/恢复 */ },
    "progress_parent": { /* 父子关系 */ },
    "progress_context_repository": { /* 绑定数据仓库 */ },
    "progress_task": { /* 绑定业务对象 */ }
  },
  "session": {
    "network": "sui testnet",
    "retentive": "always"
  }
}
```

### Node 结构

```json
{
  "name": "阶段名称",
  "pairs": [
    {
      "prior_node": "",         // "" = 起始节点（无前驱）
      "threshold": 2,           // 推进所需的最小权重点数
      "forwards": [
        {
          "name": "操作名称",
          "permission": 1001,        // 自定义权限索引 >= 1000
          "namedOperator": "角色名", // Progress 中绑定实际地址
          "weight": 1,               // 执行时贡献的权重点数
          "guard": "guard_name"      // 可选：Guard 验证
        }
      ]
    }
  ]
}
```

**关键规则**：
- `prior_node: ""` 标记起始节点，每个 Machine 只有一个
- 一个 node 可有多个 pairs（从不同前驱节点可达）
- `threshold >= 1` 需要 forward 执行累积权重；`threshold: 0` 自动推进
- 分支：多个 node 的 pairs 共享同一个 prior_node

### Threshold + Weight 逻辑

| threshold | forwards weights | 含义 |
|-----------|-----------------|------|
| 1 | [1] | 单人审批 |
| 2 | [1, 1] | 双人审批 |
| 2 | [2] | 高权限单人审批 |
| 3 | [2, 1, 1] | 经理 + 一人，或三个普通人 |
| 0 | any | 无需审批，自动推进 |

### Node 操作

```json
// 添加节点
{ "op": "add", "bReplace": false, "data": [/* node array */] }

// 删除节点
{ "op": "remove", "names": ["node1", "node2"] }

// 重命名
{ "op": "rename node", "data": [{ "old": "旧名", "new": "新名" }] }

// 添加 forward
{
  "op": "add forward",
  "data": [{
    "prior_node_name": "源节点",
    "node_name": "目标节点",
    "threshold": 1,
    "forward": { /* forward schema */ }
  }]
}
```

---

## Progress 操作

### 创建 Progress

```json
{
  "data": {
    "object": "my_machine",
    "progress_new": {
      "namedNew": { "name": "task_001", "onChain": true },
      "task_address": "order_address"
    }
  }
}
```

### 绑定角色

```json
{
  "data": {
    "object": "my_machine",
    "progress_namedOperator": {
      "progress": "task_001",
      "data": [
        {
          "name": "team_lead",
          "operators": [
            { "name_or_address": "alice", "local_mark_first": true }
          ]
        }
      ]
    }
  }
}
```

### 推进工作流

```json
{
  "data": {
    "object": "my_machine",
    "progress_next": {
      "progress": "task_001",
      "operation": {
        "next_node_name": "task_completed",
        "forward": "submit_deliverable"
      },
      "deliverable": "任务完成说明"
    }
  }
}
```

---

## 权限与 Guard

### 权限

- 自定义业务权限索引 >= 1000
- 内置 Machine 管理权限：600-607
- 内置 Progress 操作权限：650-655
- 特殊角色：`Machine.OPERATOR_ORDER_PAYER`（Order 支付方，自动绑定）

### Guard

链上不可变布尔条件对象。可查询：Progress 状态/节点、Order 数据、Service 数据、支付数据、区块链时间、签名者地址等。

Guard witness 类型（运行时提供的值）：

| Code | 关系 | 描述 |
|------|------|------|
| 30 | Order → Progress | 从 Order 上下文验证 Progress |
| 33 | Progress → Machine | 从 Progress 上下文验证 Machine |
| 34-38 | Arb → * | 仲裁相关验证 |

---

## 生命周期

```
创建 Machine → 添加 nodes → 配置权限/Guard → 发布（不可逆）
                                                    ↓
                                              创建 Progress → 绑定角色 → 推进工作流 → 完成
```

- **发布不可逆**：`bPublished: true` 后工作流拓扑冻结
- **暂停**：`bPaused: true` 阻止新 Progress 创建，已有 Progress 继续
- **克隆**：`clone_new` 创建可修改的副本

---

## 通爻结晶 → Machine 映射模板

结晶收敛后，方案生成 Agent 应产出类似以下结构：

```json
{
  "data": {
    "object": {
      "name": "crystallization_output_{session_id}",
      "onChain": true,
      "tags": ["towow", "crystallization"]
    },
    "description": "结晶产出的协作构型",
    "nodes": {
      "op": "add",
      "bReplace": false,
      "data": [
        {
          "name": "协作确认",
          "pairs": [{
            "prior_node": "",
            "threshold": 3,
            "forwards": [
              { "name": "参与者A确认", "namedOperator": "participant_a", "weight": 1 },
              { "name": "参与者B确认", "namedOperator": "participant_b", "weight": 1 },
              { "name": "参与者C确认", "namedOperator": "participant_c", "weight": 1 }
            ]
          }]
        },
        {
          "name": "任务A完成",
          "pairs": [{
            "prior_node": "协作确认",
            "threshold": 1,
            "forwards": [
              { "name": "提交交付物", "namedOperator": "participant_a", "weight": 1 }
            ]
          }]
        },
        {
          "name": "任务B完成",
          "pairs": [{
            "prior_node": "协作确认",
            "threshold": 1,
            "forwards": [
              { "name": "提交交付物", "namedOperator": "participant_b", "weight": 1 }
            ]
          }]
        },
        {
          "name": "协作完成",
          "pairs": [
            {
              "prior_node": "任务A完成",
              "threshold": 1,
              "forwards": [{ "name": "验收A", "namedOperator": "participant_b", "weight": 1 }]
            },
            {
              "prior_node": "任务B完成",
              "threshold": 1,
              "forwards": [{ "name": "验收B", "namedOperator": "participant_a", "weight": 1 }]
            }
          ]
        }
      ]
    }
  }
}
```

**注意**：这是概念模板。实际的 Machine JSON 需要根据结晶产出的具体协作构型动态生成。方案生成 Agent 的 prompt 负责将自然语言分工方案转换为这个格式。

---

## 关键常量

| 常量 | 值 | 含义 |
|------|------|------|
| `Machine.INITIAL_NODE_NAME` | `""` | 虚拟起始节点 |
| `Machine.OPERATOR_ORDER_PAYER` | 特殊字符串 | 内置角色：Order 支付方 |
| 自定义权限索引 | `>= 1000` | 业务权限必须 >= 1000 |
| Guard identifier | `1..255` | Guard 表 ID 有效范围 |

---

*本文档基于 WOWOK 官方文档、SDK 源码和 MCP Server 源码整理。详细 TypeScript SDK 用法参见 `wowok` npm 包和 `wowok-ai/examples` GitHub 仓库。*
