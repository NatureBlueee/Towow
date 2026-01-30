# TASK-EXP-004: RequirementForm 组件

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-004 |
| 状态 | TODO |
| 优先级 | P0 |
| 预估工时 | 4h |
| Beads ID | `towow-apq` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

实现需求提交表单组件，支持标题和描述输入，带表单验证。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 5.1.2 节 RequirementForm 设计
- 现有 Button 组件
- 现有 ContentCard 组件

## 3. 输出

- `/components/experience/RequirementForm.tsx` - 需求表单组件
- `/components/experience/RequirementForm.module.css` - 样式文件

## 4. 验收标准

- [ ] 标题输入框（必填，最大 100 字符）
- [ ] 描述输入框（必填，最大 2000 字符）
- [ ] 实时字符计数显示
- [ ] 表单验证（空值、超长提示）
- [ ] 提交按钮带 loading 状态
- [ ] disabled 状态支持（协商进行中禁用）
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：无

**接口依赖**：无

## 6. 实现要点

```typescript
// components/experience/RequirementForm.tsx
interface RequirementFormProps {
  onSubmit: (data: RequirementInput) => Promise<void>;
  isSubmitting?: boolean;
  disabled?: boolean;
}

interface RequirementInput {
  title: string;
  description: string;
}

export function RequirementForm({
  onSubmit,
  isSubmitting,
  disabled,
}: RequirementFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!title.trim()) newErrors.title = '请输入需求标题';
    if (title.length > 100) newErrors.title = '标题不能超过100字符';
    if (!description.trim()) newErrors.description = '请输入需求描述';
    if (description.length > 2000) newErrors.description = '描述不能超过2000字符';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    await onSubmit({ title, description });
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* ... */}
    </form>
  );
}
```

## 7. 测试要点

- 空表单提交验证测试
- 字符超限验证测试
- 正常提交流程测试
- loading 状态测试
- disabled 状态测试

---

## 实现记录

> 开发完成后填写

### 实现说明

（待填写）

### 测试结果

（待填写）

### 变更记录

| 时间 | 变更内容 | 变更人 |
|------|----------|--------|
| 2026-01-29 | 创建任务 | proj |
