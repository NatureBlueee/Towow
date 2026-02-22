# Session Log: 2026-02-22

## 本次完成

### Task #31: Agent Teams 代码级名称绑定机制 [COMPLETED]

**问题根因**: RUN-006 中 LLM 编造了 3 个不存在的昵称（"雨洁"→P01, "Frank"→P03, "磊磊"→P05），传播链为 Lead Agent → Catalyst → Plan → Delivery。本质是保障等级不对称（Section 0.5 违反）：名称由 LLM 传递而非代码绑定。

**解决方案**:

1. **`assemble_prompts.py`** — 预组装工具
   - 从 config.json 提取规范名称
   - 预填充所有静态占位符（`{{agent_name}}`, `{{participant_list}}`, `{{profile}}`）
   - 保留动态占位符（`{{catalyst_output_previous_round}}`, `{{plan}}`）给运行时
   - 产出: name_registry.json + 14 个预组装文件（catalyst×1 + endpoint×5 + delivery×5 + plan_profiles×1 + manifest×1）
   - CLI: `python3 assemble_prompts.py --config run_NNN/config.json [--dry-run]`

2. **`validate_names.py`** — 名称一致性校验门
   - 检测输出中的 "P0X（名字）" 模式
   - 与 name_registry.json 的规范名称比对
   - RUN-006 验证结果: 101 errors, 4 warnings — 成功捕获全部 3 个编造昵称
   - CLI: `python3 validate_names.py run_NNN/`

3. **SKILL.md 更新**
   - 硬性约束 #7: 名称通过代码绑定
   - 新增 "名称绑定协议" Section
   - Teammate spawn prompt 引用预组装文件而非原始模板

**验证**: 对 RUN-006 完整运行 assemble + validate，确认端到端工作。

---

### Task #32: 前端去后端依赖 [COMPLETED]

**背景**: 后端崩溃，前端页面因依赖后端 API 全部白屏。

**方案**: MaintenanceBanner 模式
- 11 个后端依赖页面 → 维护横幅（playground, negotiation, enter, field, store, store/[scene], 5× team-matcher）
- 2 个 API 路由 → 503 响应（store/api/[...path], store/api/assist-demand）
- 1 个 layout 修改（team-matcher/layout.tsx — 移除 TeamAuthProvider）
- 4 个纯静态页面不受影响（首页, articles, 关于等）

**构建验证**: `npm run build` 通过，22 页面正常编译。

**恢复路径**: `git checkout HEAD -- <files>`（未提交前有效）

---

### 其他完成项

- **Delivery prompt v0** (delivery_v0.md): 反向投影 prompt，三维度（核心发现/行动路径/Agent观察）
- **Delivery 验证**: Task #26 (P02 需求方视角) + Task #27 (P08 参与者视角) 确认 prompt 有效
- **内测反馈模板**: Task #29 完成
- **RUN-006 执行完成**: 5人10对, 5轮收敛, 6对有关系+4对无关系, 催化时间稳定 3-4min/轮
- **state.json 更新**: 新增 prompt_versions.delivery + pipeline_tools section

## 新增工具清单

| 工具 | 路径 | 用途 |
|------|------|------|
| assemble_prompts.py | simulations/real/assemble_prompts.py | 预组装 prompt（代码级名称绑定） |
| validate_names.py | simulations/real/validate_names.py | 名称一致性校验门 |
| test_delivery.py | simulations/real/test_delivery.py | Delivery prompt 单独测试 |

## 待推进

- **Task #28**: 全流程管道架构设计（Agent Teams 模式）
- **Task #30**: 管道脚本实现 + 集成测试（blocked by #28）
- **RUN-006 用户评估**: state.json next_action = user_evaluate
- **前端修复 Lead 审查**: 本次执行
