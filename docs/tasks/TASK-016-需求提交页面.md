# TASK-016：需求提交页面

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-016 |
| 所属Phase | Phase 5：前端开发 |
| 硬依赖 | TASK-015 |
| 接口依赖 | TASK-018（SSE API格式） |
| 可并行 | - |
| 预估工作量 | 1天 |
| 状态 | 待开始 |

---

## 任务描述

实现用户提交需求的页面，包括输入框、提交按钮、状态反馈。这是用户与ToWow系统交互的入口。

---

## 页面设计

### 布局示意

```
┌─────────────────────────────────────────┐
│              ToWow 协作网络              │
│         让AI帮你找到合作伙伴             │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │                                 │   │
│  │   说说你想做什么...              │   │
│  │                                 │   │
│  │                                 │   │
│  └─────────────────────────────────┘   │
│                                         │
│              [ 发起协作 ]               │
│                                         │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│                                         │
│  示例：                                 │
│  - 我想在北京办一场AI主题聚会           │
│  - 找一个懂设计的人帮我做产品原型        │
│  - 组织一次周末徒步活动                 │
│                                         │
└─────────────────────────────────────────┘
```

---

## 具体工作

### 1. 需求提交页面组件

`src/features/demand/DemandSubmitPage.tsx`:

```tsx
import React, { useState } from 'react';
import { Input, Button, Card, Typography, Space, message } from 'antd';
import { SendOutlined, BulbOutlined } from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { demandApi } from '../../api/demand';
import { useDemandStore } from '../../stores/demandStore';
import './DemandSubmitPage.css';

const { TextArea } = Input;
const { Title, Text } = Typography;

const EXAMPLES = [
  '我想在北京办一场50人的AI主题聚会',
  '找一个懂AI的设计师帮我做产品原型',
  '组织一次周末在郊区的徒步活动',
];

export const DemandSubmitPage: React.FC = () => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setCurrentDemand } = useDemandStore();

  const handleSubmit = async () => {
    if (!input.trim()) {
      message.warning('请输入你的需求');
      return;
    }

    setLoading(true);
    try {
      const result = await demandApi.submit(input);
      setCurrentDemand(result);
      message.success('需求已提交，正在寻找合作伙伴...');
      navigate(`/negotiation/${result.demand_id}`);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || '提交失败，请重试';
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleExampleClick = (example: string) => {
    setInput(example);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit();
    }
  };

  return (
    <div className="demand-submit-page">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Card className="submit-card">
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div className="header">
              <Title level={2}>ToWow 协作网络</Title>
              <Text type="secondary">让AI帮你找到合作伙伴</Text>
            </div>

            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="说说你想做什么..."
              autoSize={{ minRows: 4, maxRows: 8 }}
              maxLength={500}
              showCount
              className="demand-input"
            />

            <Button
              type="primary"
              size="large"
              icon={<SendOutlined />}
              onClick={handleSubmit}
              loading={loading}
              block
            >
              发起协作
            </Button>

            <Text type="secondary" className="shortcut-hint">
              提示：Ctrl + Enter 快速提交
            </Text>

            <div className="examples">
              <Space>
                <BulbOutlined />
                <Text type="secondary">示例：</Text>
              </Space>
              <div className="example-list">
                {EXAMPLES.map((example, index) => (
                  <motion.div
                    key={index}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Button
                      type="text"
                      onClick={() => handleExampleClick(example)}
                      className="example-button"
                    >
                      - {example}
                    </Button>
                  </motion.div>
                ))}
              </div>
            </div>
          </Space>
        </Card>
      </motion.div>
    </div>
  );
};
```

### 2. 样式文件

`src/features/demand/DemandSubmitPage.css`:

```css
.demand-submit-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.submit-card {
  width: 100%;
  max-width: 600px;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.header {
  text-align: center;
  margin-bottom: 16px;
}

.header h2 {
  margin-bottom: 8px;
  color: #1a1a1a;
}

.demand-input {
  font-size: 16px;
  border-radius: 8px;
}

.demand-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.shortcut-hint {
  display: block;
  text-align: center;
  font-size: 12px;
}

.examples {
  padding-top: 16px;
  border-top: 1px dashed #e8e8e8;
}

.example-list {
  margin-top: 8px;
}

.example-button {
  color: #666;
  padding: 4px 0;
  text-align: left;
  width: 100%;
}

.example-button:hover {
  color: #667eea;
}
```

### 3. API封装

`src/api/demand.ts`:

```typescript
import { apiClient } from './client';
import { DemandSubmitRequest, DemandSubmitResponse } from '../types';

export const demandApi = {
  /**
   * 提交需求
   */
  submit: async (rawInput: string, userId?: string): Promise<DemandSubmitResponse> => {
    const request: DemandSubmitRequest = {
      raw_input: rawInput,
      user_id: userId,
    };
    const response = await apiClient.post<DemandSubmitResponse>('/api/demand/submit', request);
    return response.data;
  },

  /**
   * 获取需求详情
   */
  getDetail: async (demandId: string) => {
    const response = await apiClient.get(`/api/demand/${demandId}`);
    return response.data;
  },

  /**
   * 获取需求状态
   */
  getStatus: async (demandId: string) => {
    const response = await apiClient.get(`/api/demand/${demandId}/status`);
    return response.data;
  },
};
```

---

## 接口契约

### 后端API（TASK-018提供）

**POST /api/demand/submit**

Request:
```json
{
  "raw_input": "我想在北京办一场AI主题聚会",
  "user_id": "anonymous"
}
```

Response:
```json
{
  "demand_id": "d-abc12345",
  "channel_id": "collab-abc12345",
  "status": "processing",
  "understanding": {
    "surface_demand": "想在北京办一场AI主题聚会",
    "confidence": "high"
  }
}
```

---

## 验收标准

- [ ] 页面正常显示，布局美观
- [ ] 可以输入需求文本（支持多行）
- [ ] 字数限制和计数功能正常
- [ ] 点击提交后调用API
- [ ] 提交时显示loading状态
- [ ] 提交成功后跳转到协商页面
- [ ] 提交失败显示错误提示
- [ ] 示例点击可以填充输入框
- [ ] Ctrl+Enter快捷键正常工作
- [ ] 动画效果流畅

---

## 产出物

- `src/features/demand/DemandSubmitPage.tsx`
- `src/features/demand/DemandSubmitPage.css`
- `src/api/demand.ts`

---

**创建时间**: 2026-01-21
**来源**: supplement-03-frontend.md
