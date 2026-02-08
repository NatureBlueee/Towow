# GapRecursionSkill V1 Prompt

> 接口定义见 `docs/ARCHITECTURE_DESIGN.md` Section 9.8

```
System:
    你需要把一个资源缺口转化为一个独立的需求。
    这个需求会被广播到网络中，由其他参与者响应。

    规则：
    1. 子需求应该比原始需求更具体
    2. 子需求应该自包含——看到它的人不需要知道父需求的细节
    3. 但要保留足够的上下文，让响应者理解背景

User:
    ## 原始需求
    {parent_demand_text}

    ## 识别到的缺口
    {gap_description}

    请生成一个独立的子需求。
```

**优化方向（给 SkillPolisher）**：子需求的抽象程度（太具体会限制响应范围，太抽象会失去精准度）；如何平衡自包含和上下文保留。
