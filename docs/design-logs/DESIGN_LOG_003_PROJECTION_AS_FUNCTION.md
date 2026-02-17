# Design Log #003: 投影即函数——架构的极度简化

> 讨论日期：2026-02-07
> 参与者：架构师 + 创始人
> 状态：✅ 核心洞察已确立
> 触发：Task #3 讨论中发现过度复杂，重新审视架构本质

---

## 核心问题：我们陷入了什么？

在讨论 Task #3（Service Agent 结晶机制）时，出现了：
- 三层防漂移机制（先验锚定、维度平衡、周期性校准）
- 详细的参数调优（0.3、0.1、0.2...）
- Edge Agent vs Service Agent 的差异化更新策略
- 复杂的权重公式和伪代码

**创始人的质疑**：
> "本质和实现没有区分开来，这个东西不应该这么复杂的。"
> "什么才是好的架构？有些问题本身就不该出现。"
> "应该要极度简单。"

---

## 核心洞察 1：Agent 是函数，不是对象

### 错误的理解（之前）

```
Profile Data → 初始化 → Edge Agent（有状态对象）
                      → 不断更新 → 可能漂移 → 需要防漂移机制
```

**问题**：
- 把 Agent 当成"有状态对象"
- 讨论"如何维护状态"
- 创造了"防漂移"这个不存在的问题

### 正确的理解（现在）

```
ProfileDataSource（数据源）
       ↓
投影函数（无状态）
       ↓
Edge Agent Vector = project(profile_data, lens="full_dimension")
Service Agent Vector = project(profile_data, lens="focus_on_X")
```

**关键**：
- **投影是函数，不是对象**
- **Agent 不存储状态，而是计算状态**
- **没有"维护"，只有"重新投影"**

### 为什么这是极度简单？

```python
# V1 核心逻辑（伪代码）
def get_agent_vector(user_id, lens):
    """
    获取 Agent 的 HDC 向量

    极度简单：读取 + 投影
    """
    profile_data = data_source.get_profile(user_id)  # 读取
    vector = project(profile_data, lens)              # 投影
    return vector
```

**不需要**：
- Profile Data 更新算法
- 防漂移机制
- 状态维护
- 复杂的参数调优

---

## 核心洞察 2：协作数据回流到数据源

### 创始人的提问

> "为什么不能让协作本身作为数据回到 SecondMe？外部数据源再投影到我们系统内部，是不是都不需要某一步骤？"

### 架构的根本转变

**之前的架构**：
```
SecondMe（先验）→ 通爻 Profile Data → 经验融入 → 更新 Profile Data
                                    ↓
                              Edge Agent（投影）
```

**新的架构**：
```
ProfileDataSource（统一数据源）
    ↑               ↓
协作数据回流    读取并投影
    ↑               ↓
通爻记录      Agent Vector（投影）
```

**关键变化**：
- **通爻不维护 Profile Data**，只投影
- **协作数据回流到数据源**（SecondMe / Claude / GPT / ...）
- **数据源自己处理更新**（通爻不管）

### 为什么这是正确的？

**1. 真正的"完备性"（设计原则 0.9）**

> 完备性 ≠ 完全性
> 窗户（实时连通）vs 照片（过时数据）

- **数据源是"窗户"**，通爻持续读取
- **不是"拷贝数据"**，而是"保持连通"

**2. 符合"投影是基本操作"（设计原则 0.8）**

```
丰富的东西（Profile Data）× 透镜 → 聚焦的结果（Agent Vector）
```

- 投影是函数调用，无状态
- 数据源变了 → 重新投影即可

**3. 可插拔的 Adapter 架构**

```
ProfileDataSource（抽象接口）
    ↓
    ├─ SecondMe Adapter
    ├─ Claude Adapter
    ├─ GPT Adapter
    ├─ Template Adapter
    └─ Custom Adapter
```

**SecondMe 只是其中一个 Adapter**，不是唯一的。

---

## 核心洞察 3：Service Agent 不是"结晶"，是"新增透镜"

### Task #3 的问题重新定义

**之前的问题**（过度复杂）：
- 什么经验应该强化 Profile？
- 结晶的触发条件是什么？
- 如何防止 Profile 漂移？

**新的问题**（极度简化）：
- 透镜如何定义？（参数是什么？）
- 如何从 Profile Data 投影出 Service Agent Vector？
- 手动创建透镜的 UX 是什么？

### 为什么是"透镜"而不是"结晶"？

**"结晶"的隐含假设**：
- Agent 是有状态的
- 经验积累 → 状态改变 → 新 Agent "从旧 Agent 分裂"

**"透镜"的正确理解**：
- Agent 是投影函数的结果
- 新增透镜 = 新增一个 lens 参数
- Edge Agent 和 Service Agent 都从**同一份 Profile Data** 投影

```python
# 不是"分裂"
edge_agent.split() → service_agent  # ❌

# 而是"新增透镜"
edge_vector = project(profile_data, "full_dimension")      # ✅
service_vector = project(profile_data, "focus_on_frontend")  # ✅
```

---

## 三句话解释系统（新版本）

**通爻的 Profile 更新机制**：

1. **ProfileDataSource 是数据源**（SecondMe / Claude / GPT / ...）
2. **协作数据回流到数据源**，数据源自己更新 Profile
3. **通爻从数据源投影**：Edge Agent = 全维度，Service Agent = 聚焦维度

**能解释清楚！✅**

---

## 简单设计的四个目标

### 1. 可理解（三句话原则）

✅ 上面已验证

### 2. 可验证（快速证明有效 or 无效）

**V1 的核心假设**：
- ProfileDataSource + 投影机制 = 足够灵活
- 协作数据回流 = 有效的 Profile 演化

**如何验证**：
- 跑 1 次黑客松场景
- 看投影是否合理
- 看数据回流是否生效

**2 周可以验证！✅**

### 3. 可扩展（本质稳定，实现可变）

**本质**：投影是基本操作
```
Agent Vector = project(profile_data, lens)
```

**实现**：
- HDC 编码 → 可以换成其他编码
- SecondMe Adapter → 可以换成其他数据源
- 缓存策略 → 可以优化

**本质与实现分离！✅**

### 4. 反脆弱（失败也产生价值）

**如果投影机制失败**：
- 协作数据已记录（WOWOK 链上）
- 可以尝试不同的投影方式
- 数据回流到 SecondMe，SecondMe 也有价值

**数据沉淀！✅**

---

## Task List 的清理

基于"极度简单"原则，清理了过度设计：

| Task | 操作 | 原因 |
|------|------|------|
| #7 冷启动策略 | ❌ 删除 | ProfileDataSource 已有初始数据 |
| #9 HDC 验证 benchmark | ⏸️ 延后 V2+ | V1 先验证核心机制 |
| #10 参考架构调研 | ⏸️ 延后 V2+ | 不阻塞主线 |
| #11 安全模型 | ⏸️ 延后 V2+ | V1 先验证核心机制 |
| #3 Service Agent 结晶 | ✏️ 重新定义 | 改为"透镜机制"，极度简化 |
| #15 决策 2：回声信号加权 | ✅ 完成 | 共识机制 > 统计平滑 |

---

## V1 架构的极度简化版本

### 核心组件

```
1. ProfileDataSource（可插拔接口）
   - SecondMe / Claude / GPT / Template / Custom
   - 提供：get_profile(user_id) → ProfileData
   - 接收：update_profile(user_id, experience_data)

2. 投影函数（无状态）
   - project(profile_data, lens) → HDC Vector
   - lens 可以是 "full_dimension" 或 "focus_on_X"

3. 透镜库（可扩展）
   - "full_dimension": 全维度投影 → Edge Agent
   - "focus_on_frontend": 聚焦前端 → Service Agent
   - 手动创建（场景模板）或自动发现（V2+）

4. 协作数据回流
   - 通爻记录协作数据（WOWOK 链上）
   - 定期同步到 ProfileDataSource
   - 数据源自己处理更新
```

### V1 代码逻辑（伪代码）

```python
# 核心逻辑：极度简单
class ToWowNetwork:
    def get_agent_vector(self, user_id: str, lens: str) -> HDCVector:
        """
        获取 Agent 的 HDC 向量
        """
        # Step 1: 从数据源读取
        profile_data = self.data_source.get_profile(user_id)

        # Step 2: 投影
        vector = project(profile_data, lens)

        return vector

    def record_experience(self, user_id: str, experience_data: dict):
        """
        记录协作经验，回流到数据源
        """
        # Step 1: 通爻记录（链上 or 本地）
        self.experience_store.save(user_id, experience_data)

        # Step 2: 回流到数据源
        self.data_source.update_profile(user_id, experience_data)
```

**不需要**：
- Profile 更新算法（数据源自己处理）
- 防漂移机制（投影函数无状态）
- 状态维护（每次重新投影）

---

## 实现层面的问题（标识为子课题）

以下是实现层面的问题，不在架构讨论中展开：

### 1. ProfileDataSource 的同步策略
- 实时同步 vs 批量同步？
- 如果数据源不可用怎么办？
- 需要本地缓存吗？

### 2. 投影函数的性能
- 每次都重新计算 HDC 投影，会不会很慢？
- 需要缓存机制吗？
- 如何做增量更新？

### 3. 透镜的定义
- 透镜的参数是什么？
- 如何从 Profile Data 提取"聚焦维度"？
- V2 如何自动发现透镜？

### 4. 协作数据的格式
- 回流到数据源的数据格式是什么？
- 不同 Adapter 的数据格式如何统一？

**关键**：这些都是**实现细节**，不影响架构本质。

---

## 反思：什么是好的架构？

### 对于通爻来讲，好的架构应该：

1. **极度简单**
   - 核心逻辑可以用三句话解释
   - 不创造不存在的问题

2. **本质稳定**
   - 投影是基本操作（不变）
   - 具体编码可以替换（可变）

3. **可快速验证**
   - V1 可以在 2 周内验证核心假设
   - 失败也产生价值（数据沉淀）

4. **复杂性涌现**
   - 不是"设计复杂性"
   - 而是"简单规则递归产生复杂性"

### 警惕的陷阱

1. **协议设计的兔子洞**
   - 双向响应机制、多层嵌套、概念循环
   - 容易在抽象层打转

2. **概念到执行的翻译鸿沟**
   - 概念很酷，但无法落地
   - 涌现系统很难 debug，很难给用户稳定预期

3. **过度设计**
   - 在架构层讨论实现细节（参数、公式）
   - 创造不存在的问题（如"防漂移"）

---

## 下一步

基于这个架构突破，下一步的工作：

1. **✅ 已完成**：
   - 清理 Task List
   - 重新定义 Task #3

2. **⏸️ 待讨论**：
   - 透镜的定义（Task #3 简化版）
   - ProfileDataSource 接口设计
   - 协作数据回流的实现方案

3. **📝 待记录**：
   - 更新架构文档（Section 6.5 扩展）
   - 更新 MEMORY.md

---

*写于发现"投影即函数"的那个下午。*
*本质是极度简单的，复杂性应该从简单规则中涌现。*
