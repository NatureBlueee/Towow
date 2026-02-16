"""
Phase 0 测试集：模糊意图匹配验证

447 个 Agent Profile 横跨 4 个场景：
  hackathon (118), skill_exchange (107), recruitment (114), matchmaking (108)

测试设计原则：
  - 每个查询都有基于真实 Profile 数据的期望命中
  - 分 4 个难度级别，逐级验证编码质量
  - 同时测试 raw（无 formulation）和 formulated（有 formulation）两种模式
  - 互补关系是核心挑战——sentence-transformers 擅长语义相似，不擅长需求↔能力匹配

难度级别：
  L1 — 直接匹配：查询词直接出现在 Profile 中
  L2 — 同义改写：查询和 Profile 用不同词表达同一含义
  L3 — 互补匹配：查询表达需求，Profile 表达能力（need ↔ capability）
  L4 — 跨域模糊：抽象意图，需要跨领域关联

每条测试：
  query:         用户输入的原始意图
  context:       用户的隐式上下文（用于 formulation，Phase 0 可选）
  expected_hits: 期望出现在 Top-10 的 agent_id（至少命中其中 N 个即算通过）
  min_hits:      Top-10 中至少命中几个 expected_hits
  anti_hits:     不应该出现在 Top-5 的 agent_id（负面验证）
  level:         难度级别 (L1-L4)
  note:          测试意图说明
"""

TEST_QUERIES = [
    # ================================================================
    # L1 — 直接匹配（Direct Match）
    # 查询词直接出现在 Profile 的 role/skills/bio 中
    # 预期准确率：Top-10 命中率 > 80%
    # ================================================================
    {
        "query": "安全研究员",
        "context": None,
        "expected_hits": [
            "zero_day",           # hackathon: 全栈安全研究员
            "ghost_in_shell",     # hackathon: 安全研究员 / 逆向工程师
            "binary_sage",        # hackathon: 安全研究员
            "zero_day_hunter",    # recruitment: 安全研究员
            "packet_sniffer",     # skill_exchange: 网络安全研究员
        ],
        "min_hits": 3,
        "anti_hits": [],
        "level": "L1",
        "note": "role 中直接包含「安全研究员」的 Agent",
    },
    {
        "query": "Kubernetes 工程师",
        "context": None,
        "expected_hits": [
            "sudo_rm",            # hackathon: 云原生架构师, skills=[Kubernetes]
            "echo_in_void",       # hackathon: DevOps / 基础设施工程师, skills=[Kubernetes]
            "cloud_nomad",        # hackathon: DevOps / 云架构师, skills=[Kubernetes]
            "void_operator",      # hackathon: DevOps工程师, skills=[Kubernetes]
            "chaos_gardener",     # hackathon: DevOps 炼金术士, skills=[Kubernetes]
            "git_rebase_i",       # recruitment: DevOps 工程师, skills=[Kubernetes]
        ],
        "min_hits": 3,
        "anti_hits": [],
        "level": "L1",
        "note": "skills 中直接包含 Kubernetes",
    },
    {
        "query": "Python 数据分析",
        "context": None,
        "expected_hits": [
            "regex_queen",        # hackathon: 数据工程师, skills=[Python, Spark, SQL]
            "diao_bao_xia_nv",    # hackathon: 数据科学, skills=[Pandas, Scikit-learn]
            "shu_ju_lao_nong",    # hackathon: 数据分析, skills=[SQL, Python, pandas]
            "data_witch",         # hackathon: Data Scientist, skills=[Python, ML]
            "zhan_bu_shi",        # hackathon: 塔罗师 / 数据分析师, skills=[Python]
        ],
        "min_hits": 3,
        "anti_hits": [],
        "level": "L1",
        "note": "skills 同时包含 Python + 数据相关",
    },
    {
        "query": "游戏开发 Unity",
        "context": None,
        "expected_hits": [
            "mo_fa_shi_de_bug",   # hackathon: 游戏开发, skills=[Unity, C#]
            "pixel_poet",         # hackathon: 独立游戏开发者, skills=[Unity, C#]
            "xiao_chou",          # hackathon: 马戏团小丑 / 游戏开发者, skills=[Unity]
            "diu_zhen_ren",       # hackathon: 游戏叙事设计, skills=[Unity]
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L1",
        "note": "直接匹配 Unity 游戏开发",
    },
    {
        "query": "区块链 智能合约 Solidity",
        "context": None,
        "expected_hits": [
            "cyber_monk",         # skill_exchange: 区块链布道者, skills=[Solidity智能合约]
            "liang_zi_da_shu",    # hackathon: 理论物理博士 / 区块链架构师, skills=[Solidity]
            "blockchain_skeptic", # hackathon: Smart Contract Developer, skills=[Solidity]
            "hui_sheng",          # hackathon: 区块链诗人, skills=[Solidity, Web3.js]
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L1",
        "note": "直接匹配区块链 + Solidity",
    },

    # ================================================================
    # L2 — 同义改写（Synonym/Paraphrase Match）
    # 查询和 Profile 用不同词表达同一含义
    # 预期准确率：Top-10 命中率 > 60%
    # ================================================================
    {
        "query": "做网页 3D 视觉效果的人",
        "context": None,
        "expected_hits": [
            "neko_chan",           # hackathon: 前端视觉魔法师, skills=[Three.js, WebGL]
            "yu_zhou_chen_ai",    # hackathon: 前端开发 / 天文爱好者, skills=[Three.js, WebGL]
            "neon_samurai",       # hackathon: 前端刺客, skills=[WebGL, Three.js, GLSL]
            "liu_guang_ke",       # hackathon: 视觉叙事者, skills=[Three.js, Shader编程]
            "pixel_witch",        # hackathon: 前端视觉开发, skills=[WebGL]
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L2",
        "note": "「网页3D视觉」= Three.js/WebGL，词汇不同但语义相同",
    },
    {
        "query": "搞声音艺术和实验音乐的",
        "context": None,
        "expected_hits": [
            "wu_sheng_de_ren",    # hackathon: 声音设计师 / 实验音乐人
            "echo_chamber",       # hackathon: 音频工程师
            "hui_se_xin_hao",     # hackathon: 声波考古学家
            "glitch_queen",       # skill_exchange: 视觉黑客 & 生成艺术家, skills=[Max/MSP]
            "frequency_hermit",   # skill_exchange: 实验音乐人, skills=[SuperCollider]
            "sonic_archaeologist", # hackathon/skill: 声波考古学家
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L2",
        "note": "「声音艺术」≈ 声音设计 / 实验音乐 / Max/MSP",
    },
    {
        "query": "能写高性能后端服务的",
        "context": None,
        "expected_hits": [
            "packet_loss",        # hackathon: 后端性能狂魔, skills=[C++, 高并发]
            "async_await",        # recruitment: 后端架构师, skills=[Go, Rust, 高并发]
            "midnight_debugger",  # hackathon: 后端工程师, skills=[Go, 性能优化]
            "mem_leak",           # hackathon: 性能偏执狂, skills=[C++, 性能分析]
            "mu_yu_ren",          # hackathon: 后端隐士, skills=[Rust, 分布式系统]
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L2",
        "note": "「高性能后端」≈ 性能优化 + 后端 + Go/Rust/C++",
    },
    {
        "query": "做创意互动装置的艺术家",
        "context": None,
        "expected_hits": [
            "glitch_girl",        # hackathon: 创意技术实验员, skills=[Processing, Arduino]
            "glitch_artist",      # hackathon: Creative Technologist, skills=[Processing, Arduino]
            "glitch_poet",        # hackathon: 创意技术开发, skills=[Processing, Arduino]
            "leather_punk",       # hackathon: 手工皮具匠人, skills=[Arduino, 3D建模]
            "fermentation_hacker",# hackathon: 生物艺术家, skills=[生物传感器]
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L2",
        "note": "「创意互动装置」≈ Arduino + Processing + 生成艺术",
    },
    {
        "query": "懂密码学的人",
        "context": None,
        "expected_hits": [
            "digital_hermit",     # hackathon: 加密货币研究者, skills=[cryptography]
            "liang_zi_liu_lang",  # skill_exchange: 密码学研究者, skills=[后量子密码, 零知识证明]
            "bit_alchemist",      # skill_exchange: 密码学研究员
            "mo_sheng_ren",       # hackathon: 隐私工程师, skills=[加密算法]
            "protocol_punk",      # skill_exchange: 网络协议设计师, skills=[密码学]
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L2",
        "note": "「密码学」在不同 Profile 中的多种表达",
    },

    # ================================================================
    # L3 — 互补匹配（Complementary Match）
    # 查询表达需求，Profile 表达能力
    # 这是 sentence-transformers 的最大挑战
    # 预期准确率（raw）：Top-10 命中率 > 30%
    # 预期准确率（formulated）：Top-10 命中率 > 50%
    # ================================================================
    {
        "query": "我的项目需要做安全审计",
        "context": "我在开发一个 DeFi 协议，需要有人帮我审查智能合约的安全性",
        "expected_hits": [
            "cyber_monk",         # skill_exchange: can_teach=[智能合约安全审计]
            "zero_day",           # hackathon: 全栈安全研究员, skills=[区块链安全]
            "blockchain_skeptic", # hackathon: Smart Contract Developer, skills=[Security Audit]
            "grey_hat",           # hackathon: 安全研究员 / 前渗透测试负责人
            "ghost_in_shell",     # hackathon: 安全研究员 / 逆向工程师
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L3",
        "note": "需求「需要安全审计」→ 能力「安全研究员 / 合约审计」。互补关系",
    },
    {
        "query": "我想学怎么做实时视觉特效",
        "context": "我是一个设计师，想学 Shader 编程",
        "expected_hits": [
            "glitch_queen",       # skill_exchange: can_teach=[实时视觉编程, 音视频同步]
            "shader_shaman",      # skill_exchange: 图形程序员, skills=[OpenGL/Vulkan]
            "shader_punk",        # hackathon: 视觉黑客, skills=[GLSL, 生成艺术]
            "shader_witch",       # skill_exchange: 图形程序员, skills=[GLSL/HLSL]
            "neon_vandal",        # skill_exchange: 视觉黑客, skills=[Shader编程]
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L3",
        "note": "需求「想学」→ 能力「can_teach」。learning ↔ teaching 互补",
    },
    {
        "query": "帮我部署一个能扛大流量的后端",
        "context": None,
        "expected_hits": [
            "sudo_rm",            # hackathon: 云原生架构师, bio=能扛百万QPS的架构
            "async_await",        # recruitment: 后端架构师, skills=[高并发]
            "packet_loss",        # hackathon: 后端性能狂魔, skills=[高并发]
            "echo_in_void",       # hackathon: DevOps / 基础设施工程师
            "cloud_nomad",        # hackathon: DevOps / 云架构师
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L3",
        "note": "需求「扛大流量」→ 能力「高并发 / K8s / 性能」",
    },
    {
        "query": "我的网站太丑了需要重新设计",
        "context": None,
        "expected_hits": [
            "broken_mirror",      # hackathon: UI/UX 设计师
            "ctrl_z",             # hackathon: UI/UX设计师
            "wu_ming_zhi",        # hackathon: 交互设计游民
            "san_xing_lv_shi",    # hackathon: 前诉讼律师 / UI/UX 设计师
            "pixel_chef",         # hackathon: UI/UX Designer
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L3",
        "note": "需求「网站太丑」→ 能力「UI/UX 设计」。日常用语 ↔ 专业能力",
    },
    {
        "query": "数据库越来越慢怎么办",
        "context": "我们用的 MySQL，数据量大概两千万行",
        "expected_hits": [
            "db_lao_wang",        # hackathon: 数据库专家 / 性能优化顾问
            "db_necromancer",     # hackathon: 数据复活术士, skills=[SQL优化]
            "sql_poet",           # skill_exchange: 数据库架构师, skills=[查询优化]
            "packet_loss",        # hackathon: 后端性能狂魔, skills=[数据库优化]
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L3",
        "note": "问题描述 → 需要数据库优化专家。口语 ↔ 专业能力",
    },

    # ================================================================
    # L4 — 跨域模糊匹配（Cross-Domain Fuzzy Match）
    # 抽象、模糊、跨领域的意图
    # 这是真正的"意图场"测试——能否发现非显而易见的关联
    # 预期准确率（raw）：Top-10 命中率 > 20%
    # 预期准确率（formulated）：Top-10 命中率 > 40%
    # ================================================================
    {
        "query": "想做一个把声音变成画面的东西",
        "context": None,
        "expected_hits": [
            "glitch_girl",        # hackathon: 做过能听的数据、看得见的声音
            "glitch_queen",       # skill_exchange: 视觉黑客, skills=[Max/MSP, VJ现场]
            "wu_sheng_de_ren",    # hackathon: 声音设计师, skills=[generative audio]
            "liu_guang_ke",       # hackathon: 视觉叙事者, skills=[声音设计]
            "glitch_monk",        # hackathon: 实验性程序员, skills=[电路弯曲, Max/MSP]
            "echo_chamber",       # hackathon: 音频工程师, skills=[Web Audio API]
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L4",
        "note": "跨域意图：音频 × 视觉。需要同时理解两个领域的交叉",
    },
    {
        "query": "用技术做点有意义的事",
        "context": "我刚毕业，会写代码但不知道做什么",
        "expected_hits": [
            # 这类查询极度模糊，期望命中的是有「技术+意义」关键词的 Profile
            "git_push_origin_love",  # matchmaking: 开源项目维护者, 相信技术改变世界
            "dai_ma_wu_tuo_bang",    # recruitment: 开源原教旨主义者, GPL布道
            "stack_overflow_soul",   # matchmaking: 全栈独立开发者
            "code_monk",             # matchmaking: 开源维护者
        ],
        "min_hits": 1,
        "anti_hits": [],
        "level": "L4",
        "note": "极度模糊。测试编码器能否从「有意义」关联到开源/公益方向",
    },
    {
        "query": "把传统手艺和数字技术结合",
        "context": None,
        "expected_hits": [
            "lao_tie_rust",       # hackathon: 前川菜厨师长 / 系统编程
            "ink_alchemist",      # hackathon: 传统印刷工艺师
            "leather_punk",       # hackathon: 手工皮具匠人, skills=[Arduino, 3D建模]
            "memory_weaver",      # hackathon: 档案管理员+纺织艺术家
            "ink_and_pixel",      # hackathon: 插画师 / 前端开发
            "diao_ke_shi_shader", # skill_exchange: 木雕艺人 / 图形编程
        ],
        "min_hits": 2,
        "anti_hits": [],
        "level": "L4",
        "note": "跨域：传统工艺 × 数字技术。这些 Agent 的 bio 正是这种交叉",
    },
    {
        "query": "我需要帮手",
        "context": None,
        "expected_hits": [],  # 太模糊，不设期望命中
        "min_hits": 0,
        "anti_hits": [],
        "level": "L4",
        "note": "极端模糊基准测试。记录返回了什么，用于分析编码器的默认偏好",
    },
    {
        "query": "认识一些有趣的人",
        "context": "我是一个程序员，想跳出技术圈认识不同背景的人",
        "expected_hits": [
            # 跨背景的有趣 Profile
            "lao_tie_rust",       # hackathon: 前川菜厨师长转码农
            "san_xing_lv_shi",    # hackathon: 前诉讼律师转设计师
            "zhan_bu_shi",        # hackathon: 塔罗师 / 数据分析师
            "shou_yi_ren",        # hackathon: 兽医 / 机器学习工程师
            "fei_xing_yuan_404",  # hackathon: 退役民航机长 / DevOps工程师
        ],
        "min_hits": 1,
        "anti_hits": [],
        "level": "L4",
        "note": "社交意图 + 跨领域。Profile 中有跨界背景的人",
    },
]


# ================================================================
# 统计与基准
# ================================================================

def summary():
    """打印测试集摘要"""
    by_level = {}
    for q in TEST_QUERIES:
        level = q["level"]
        by_level.setdefault(level, []).append(q)

    print(f"Total queries: {len(TEST_QUERIES)}")
    for level in sorted(by_level):
        queries = by_level[level]
        total_expected = sum(len(q["expected_hits"]) for q in queries)
        print(f"  {level}: {len(queries)} queries, {total_expected} expected hits")

    # 列出所有期望命中的 agent_id（去重）
    all_hits = set()
    for q in TEST_QUERIES:
        all_hits.update(q["expected_hits"])
    print(f"  Unique agents referenced: {len(all_hits)}")


if __name__ == "__main__":
    summary()
