# Experience 架构重构计划

**执行时间**: 2026-02-07
**目标**: 将 Experience 重构为应用目录模式

---

## 当前问题

1. ❌ 多版本混乱（experience, experience-v2, experience-v3）
2. ❌ Team Matcher 路由不统一（独立在 /team）
3. ❌ 没有统一的应用管理机制
4. ❌ 难以扩展新应用

---

## 目标架构

```
/experience                    # 应用入口大厅
/apps/team-matcher            # Team Matcher 应用
/apps/demand-negotiation      # 需求协商应用
/apps/* (future)              # 未来的应用
```

---

## 执行步骤

### Phase 1: 创建基础设施 ✅

1. ✅ 创建应用注册表: `lib/apps/registry.ts`
2. ✅ 创建类型定义: `lib/apps/types.ts`
3. ✅ 创建应用卡片组件: `components/experience-hub/AppCard.tsx`
4. ✅ 创建应用网格组件: `components/experience-hub/AppGrid.tsx`
5. ✅ 创建 Coming Soon 卡片: `components/experience-hub/ComingSoonCard.tsx`
6. ✅ 样式调整：使用温暖明亮配色（主站风格），不使用暗色模式

### Phase 2: 重构 Experience 入口 ✅

5. ✅ 备份当前 /experience 到 /archive/experience-v1
6. ✅ 创建新的 /experience/page.tsx (应用目录首页)
7. ✅ 创建 /experience/layout.tsx (统一布局)
8. ✅ 更新导航链接: Header.tsx 和 Footer.tsx (`/experience-v2` → `/experience`)

### Phase 3: 迁移应用

8. [ ] 迁移 Team Matcher: /team → /apps/team-matcher
9. [ ] 迁移需求协商: /experience-v2 → /apps/demand-negotiation
10. [ ] 更新所有内部链接和导航

### Phase 4: 清理和测试

11. [ ] 归档旧版本: experience-v1, v2, v3 → /archive
12. [ ] 更新导航组件
13. [ ] 端到端测试所有路由
14. [ ] 更新文档

---

## 关键文件映射

### 创建的新文件
```
lib/apps/
├── registry.ts           # 应用注册表
└── types.ts              # 类型定义

components/experience-hub/
├── AppCard.tsx           # 应用卡片
├── AppGrid.tsx           # 应用网格
└── ComingSoonCard.tsx    # Coming Soon 卡片

app/experience/
├── page.tsx              # 新入口首页
└── layout.tsx            # 统一布局
```

### 移动的文件
```
app/team/               → app/apps/team-matcher/
app/experience-v2/      → app/apps/demand-negotiation/
app/experience-v3/      → archive/experience-v3/
```

---

## 路由变更

| 旧路由 | 新路由 | 说明 |
|--------|--------|------|
| /team/request | /apps/team-matcher/request | Team Matcher 入口 |
| /team/progress/[id] | /apps/team-matcher/progress/[id] | 进度页 |
| /team/proposals/[id] | /apps/team-matcher/proposals/[id] | 方案页 |
| /experience | /experience | 改为应用目录 |
| /experience-v2 | /apps/demand-negotiation | 需求协商应用 |
| /experience-v3 | /archive/experience-v3 | 归档 |

---

## 应用注册表结构

```typescript
export const APPS: AppMetadata[] = [
  {
    id: 'team-matcher',
    name: 'Team Matcher',
    description: '黑客松组队匹配',
    icon: '🤝',
    path: '/apps/team-matcher',
    status: 'active',
    category: 'matching',
    tags: ['黑客松', '组队', '响应范式'],
  },
  {
    id: 'demand-negotiation',
    name: 'Demand Negotiation',
    description: '需求协商演示',
    icon: '💬',
    path: '/apps/demand-negotiation',
    status: 'active',
    category: 'negotiation',
    tags: ['需求', '协商', 'Agent'],
  },
];
```

---

## 验证清单

- [ ] 所有应用都能从 /experience 访问
- [ ] 应用卡片显示正确
- [ ] 路由跳转正常
- [ ] 内部链接已更新
- [ ] WebSocket 连接正常（Team Matcher）
- [ ] OAuth 登录流程正常
- [ ] 移动端响应式正常

---

## Rollback 策略

如果出现问题，可以快速回滚：

```bash
# 恢复旧版本
git revert HEAD

# 或者手动恢复
mv app/apps/team-matcher app/team
mv app/apps/demand-negotiation app/experience-v2
```

---

## 关键配置文件

需要更新的配置：
- `next.config.js` - 路由配置（如果有）
- `components/navigation/*` - 导航链接
- `lib/team-matcher/api.ts` - API 路径（如果使用相对路径）

---

**下一步**: 立即执行 Phase 1（创建基础设施）
