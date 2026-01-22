"""
SecondMe Mock实现
MVP阶段的模拟数字分身服务

提供两种 Mock 实现：
1. SecondMeMockService - 基于规则和 LLM 的智能 Mock
2. SimpleRandomMockClient - 纯随机结果，用于压力测试
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
import random
import logging
import json

from .secondme import SecondMeService

logger = logging.getLogger(__name__)


# ============================================================
# 丰富的响应模板（用于生成个性化响应）
# ============================================================

# 接受邀请的响应模板（按风格分类）
ACCEPTANCE_TEMPLATES = {
    # 热情型
    "enthusiastic": [
        "太棒了！{topic}正是我感兴趣的领域。我可以负责{contribution}，之前在{experience}做过类似的事情，效果还不错。{time_note}",
        "这个活动听起来太酷了！我一直想找机会参与{topic}相关的项目。算我一个，{contribution}方面我很有信心！",
        "哇，终于有人组织这个了！我等这个机会好久了。{topic}是我的强项，绝对全力支持！",
        "必须参加！{topic}是我的心头好，{contribution}我来搞定，放心交给我！{time_note}",
        "超级期待！我在{experience}积累了不少经验，{contribution}绝对没问题。什么时候开始？"
    ],
    # 谨慎型
    "cautious": [
        "听起来挺有意思的。不过我想先了解一下：这个活动的具体形式是什么？{topic}方面我有一些经验，但想确认一下我能提供的价值。{time_note}",
        "嗯，{topic}确实是我关注的方向。我可以考虑参与{contribution}，不过需要先看一下详细的方案和时间安排。",
        "这个邀请我挺感兴趣的。在做决定之前，能否告诉我：1）其他参与者是谁？2）预期的投入时间？3）具体的产出目标？",
        "谢谢邀请。{topic}我有一定的了解，但参与之前想确认几个问题：整体计划是什么？我的角色定位是？{time_note}",
        "整体来说我是愿意参与的，但我的时间比较有限。如果{contribution}的工作量不是很大的话，我可以试试。"
    ],
    # 条件型
    "conditional": [
        "听起来不错，但我有几个条件：首先{time_note}；其次，我希望能在{contribution}方面有比较大的自主权；最后，希望能提前知道其他参与者的情况。",
        "我对{topic}很感兴趣，愿意提供{contribution}方面的支持。不过有个前提——{condition}，这个可以满足吗？",
        "可以参与，但我需要确认几点：1）我的角色和职责要明确；2）{time_note}；3）如果中途有变动，我保留退出的权利。",
        "{topic}确实是我擅长的。我愿意帮忙，但有一个要求：{condition}。如果这个没问题，我就正式加入。",
        "这个项目我很想参与。作为交换条件，我希望{condition}。另外，{time_note}。这些可以谈吗？"
    ]
}

# 拒绝邀请的响应模板（按原因分类）
DECLINE_TEMPLATES = {
    # 时间冲突
    "time_conflict": [
        "感谢邀请，但这段时间实在抽不开身。下个月有个重要的{excuse}，每天都在加班。而且说实话，{scale_concern}。祝活动顺利！",
        "很想参加，可惜时间上真的冲突了。最近在忙{excuse}，预计要持续到{time_estimate}。如果之后还有类似活动，请一定再叫上我！",
        "不好意思，这个时间段我已经有安排了。{excuse}刚好在那几天，没法调开。真的很遗憾错过这次机会。",
        "谢谢想到我！但最近的日程已经排满了，{excuse}占据了我大部分精力。下次有机会再合作吧。",
        "这个活动听起来很棒，但我必须诚实地说——这段时间我真的忙不过来。{excuse}已经让我焦头烂额了。"
    ],
    # 能力不匹配
    "skill_mismatch": [
        "谢谢邀请，但我觉得自己可能不是最合适的人选。{topic}不太是我的强项，我更擅长{my_strength}方面的事情。",
        "这个活动的方向和我的专业领域有些偏差。我在{my_strength}方面更有经验，{topic}相关的工作可能需要找更专业的人。",
        "说实话，{topic}我接触得不多。虽然想帮忙，但怕做不好反而拖后腿。建议找一个这方面更有经验的人。",
        "我仔细想了想，{topic}需要的技能我可能不太具备。我不想承诺自己做不好的事情，所以还是算了吧。",
        "感谢信任，但我得诚实说——{topic}不是我的舒适区。我能做的是推荐几个这方面的朋友给你？"
    ],
    # 兴趣不匹配
    "interest_mismatch": [
        "这个活动的主题和我目前的关注方向不太一致。最近我主要在研究{my_interest}，对{topic}的热情没那么高。",
        "谢谢邀请，但说实话{topic}不是我特别感兴趣的领域。我怕参与后投入度不够，还是把机会让给更热衷的人吧。",
        "我考虑了一下，觉得这个项目可能不太适合我。不是能力问题，主要是{topic}方向和我当前的规划有些偏离。",
        "这个活动本身很好，但和我的兴趣点有些错位。我更倾向于参与{my_interest}相关的项目。",
        "感谢想到我，但{topic}不是我目前的重点方向。与其敷衍参与，不如把位置留给真正感兴趣的人。"
    ],
    # 规模/形式顾虑
    "scale_concern": [
        "{scale}人的规模对我来说压力有点大，我更擅长小范围的深度交流。这次就先不参加了。",
        "这个活动规模挺大的，我个人比较喜欢小而精的形式。如果之后有10人以下的版本，请一定叫我！",
        "说实话，我对大型活动有些社恐。{scale}人的场合我可能会不太自在，还是算了吧。",
        "我仔细想了想，{scale}人的活动我可能贡献不了太多价值。我在小团队里能发挥得更好。",
        "这个规模超出了我的舒适区。我更习惯和少数人深入交流，大型活动容易社交疲劳。"
    ],
    # 礼貌婉拒（万能）
    "polite_generic": [
        "感谢邀请！这个活动看起来很不错，但由于个人原因我这次没法参加。希望下次有机会！",
        "谢谢你想到我。经过考虑，我决定这次就不参与了。不是活动的问题，纯粹是我个人的安排。祝活动顺利！",
        "这个机会我很珍惜，但综合考虑后还是决定婉拒。希望以后还有合作的机会。",
        "感谢邀请，但这次我可能要pass了。有一些私人原因不太方便细说。期待下次能参与！",
        "很抱歉，这次我没法加入。原因比较复杂，但请相信这和活动本身无关。祝一切顺利！"
    ]
}

# 协商过程中的响应模板
NEGOTIATION_TEMPLATES = {
    # 角色调整请求
    "role_adjustment": [
        "整体方案我觉得可以，但关于我的角色分配，我有些想法。能不能让我更多参与{preferred_role}的部分？这块是我的强项。",
        "方案看过了，有个建议：我被分配的任务和我的专长有些偏差。如果能换成{preferred_role}相关的工作，我能发挥得更好。",
        "基本同意这个方案，但我想争取一下——{preferred_role}能不能让我来负责？我在这方面更有经验。",
        "这个分工我有点意见。相比现在分配给我的任务，我更想做{preferred_role}。能调整一下吗？"
    ],
    # 时间调整请求
    "time_adjustment": [
        "方案整体OK，但时间安排需要协调一下。能不能{time_preference}？这样我能投入更多精力。",
        "我看了一下时间表，有个小问题——{time_conflict_detail}。如果能调整到{time_preference}就完美了。",
        "其他都没问题，就是时间上想商量一下。{time_preference}对我来说更方便，可以调整吗？"
    ],
    # 资源/支持请求
    "resource_request": [
        "方案可行，但我有个请求：{resource_need}。有了这个支持，我能把事情做得更好。",
        "基本同意，不过我需要一些额外支持：{resource_need}。这个能安排吗？",
        "如果能提供{resource_need}，我可以把我负责的部分做得更出色。这个条件可以谈吗？"
    ],
    # 方案质疑
    "plan_concerns": [
        "这个方案我有些疑虑：{concern_detail}。能否解释一下这部分的考虑？",
        "看完方案后有几个问题想确认：{concern_detail}。这些点如果能说清楚，我就没意见了。",
        "整体思路没问题，但{concern_detail}这块我觉得需要再想想。大家怎么看？"
    ]
}

# 退出原因模板
WITHDRAWAL_TEMPLATES = {
    # 外部原因
    "external": [
        "非常抱歉，我不得不退出这个项目了。公司那边突然有个紧急项目，需要我全力投入。真的很对不起大家。",
        "很遗憾告诉大家，因为家里有些事情需要处理，我没法继续参与了。这不是我的本意，但确实身不由己。",
        "抱歉通知大家一个坏消息——我要退出了。最近身体出了点状况，医生建议我减少工作量。希望大家理解。"
    ],
    # 对方案不满
    "plan_dissatisfaction": [
        "经过这段时间的参与，我发现这个项目的方向和我最初的预期有较大偏差。思考再三，我决定退出。",
        "说实话，最近几次讨论让我感觉这个项目越来越偏离初衷。与其勉强继续，不如我先退出，不要影响大家。",
        "我需要诚实地说：目前的方案我不太认同。继续参与对双方都不好，所以我选择退出。"
    ],
    # 与他人有矛盾
    "interpersonal": [
        "有些话不太好说，但我和{person}在一些关键问题上分歧太大，很难继续合作了。为了不影响项目，我决定退出。",
        "最近和团队的沟通越来越困难，感觉我的意见很难被采纳。与其僵持下去，还是算了吧。",
        "坦白说，这个团队的氛围不太适合我。这不是谁对谁错的问题，纯粹是风格不合。我退出比较好。"
    ],
    # 精力不足
    "energy_issue": [
        "很抱歉，我高估了自己的时间和精力。现在发现实在兼顾不过来，与其做不好，不如早点退出。",
        "我必须承认自己接了太多事情，没法给这个项目足够的投入。继续下去会拖累大家，还是我先退出吧。",
        "经过权衡，我决定把精力集中在更重要的事情上。这个项目我没法继续了，真的很抱歉。"
    ]
}

# 难搞角色的特殊响应
DIFFICULT_RESPONSES = {
    "extremely_picky": {
        "initial_response": [
            "这个方案我看了，有很多问题需要指出。首先{issue1}，其次{issue2}，另外{issue3}。你们重新考虑一下吧。",
            "emmm...这个计划离我的标准还有不小的差距。以我的经验来看，{detailed_criticism}。",
            "我有几点意见：{detailed_criticism}。如果这些问题不解决，我很难认同这个方案。"
        ],
        "negotiation": [
            "上次的反馈你们改了吗？我看看...还是不太行，{new_issue}。",
            "比之前好一点了，但{remaining_issue}。能不能再完善一下？",
            "这个版本...怎么说呢，进步是有的，但离我的要求还差一截。{specific_feedback}"
        ]
    },
    "frequently_cancels": {
        "initial_response": [
            "好的，我先答应下来。不过提前说一声，我的行程经常会有变动，到时候如果有冲突我会尽早通知你们。",
            "可以，算我一个。但你们也知道我比较忙，临时有事的可能性挺大的，你们做好Plan B。",
            "我尽量参加吧。不过说实话，最近真的太忙了，只能走一步看一步。"
        ],
        "cancellation": [
            "不好意思，临时有个投资项目的紧急会议，这次活动我参加不了了。真的很抱歉！",
            "刚接到通知要出差，没办法赶回来了。抱歉让你们失望了。",
            "出了点状况，今天的活动我没法去了。下次一定！"
        ]
    },
    "highly_skeptical": {
        "initial_response": [
            "这个方案...我持保留态度。{technical_concern}，你们考虑过吗？",
            "等等，这个技术路线我有疑问：{technical_concern}。能解释一下吗？",
            "我需要先确认几个技术问题：{technical_concern}。如果这些问题没想清楚，后面会很麻烦。"
        ],
        "during_project": [
            "我就说吧，{predicted_issue}现在果然出问题了。",
            "之前我提的{concern}你们没重视，现在看到后果了吧。",
            "这个结果在我意料之中。{technical_reasoning}"
        ]
    },
    "pessimistic": {
        "initial_response": [
            "我觉得这个项目很难成功。{negative_reason}，类似的项目我见过太多失败的了。",
            "说实话，我不太看好。{negative_reason}，市场环境也不好。",
            "这个方向...我持悲观态度。{negative_reason}，成功率很低。"
        ],
        "during_project": [
            "果然，问题开始出现了。我早就说过{previous_warning}。",
            "照这个趋势发展下去，结果不会太好。{pessimistic_prediction}",
            "我们需要面对现实：{harsh_reality}。"
        ]
    },
    "passive_aggressive": {
        "initial_response": [
            "好的，你们决定就行。反正我说了也没人听。",
            "随便吧，既然大家都觉得好，那就这样呗。",
            "行吧，我配合就是了。虽然我有不同看法，但无所谓了。"
        ],
        "during_project": [
            "哦，这个结果...嗯，我早就说过，但你们不是不信吗。",
            "有意思，当初我的建议没人理，现在出问题了才想起来问我。",
            "好的好的，你们说什么就是什么吧。我就是个打工的。"
        ]
    }
}


# 预设的用户档案（10个丰富的 Mock 用户）
MOCK_PROFILES: Dict[str, Dict[str, Any]] = {
    "bob": {
        "user_id": "bob",
        "display_name": "Bob",
        "name": "Bob Chen",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=bob",
        "capabilities": ["场地资源", "活动组织", "会议室"],
        "location": "北京朝阳",
        "availability": "工作日可用",
        "personality": "热情外向，喜欢组织活动",
        "interests": ["AI", "创业", "社交"],
        "decision_style": "快速决策，倾向于参与"
    },
    "alice": {
        "user_id": "alice",
        "display_name": "Alice",
        "name": "Alice Wang",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=alice",
        "capabilities": ["技术分享", "AI研究", "演讲"],
        "location": "北京海淀",
        "availability": "周末优先",
        "personality": "专业认真，乐于分享",
        "interests": ["机器学习", "NLP", "技术布道"],
        "decision_style": "谨慎评估，看重技术深度"
    },
    "charlie": {
        "user_id": "charlie",
        "display_name": "Charlie",
        "name": "Charlie Zhang",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=charlie",
        "capabilities": ["活动策划", "流程设计", "现场协调"],
        "location": "北京",
        "availability": "灵活",
        "personality": "细心周到，执行力强",
        "interests": ["项目管理", "活动运营", "社区建设"],
        "decision_style": "注重细节，需要明确分工"
    },
    "david": {
        "user_id": "david",
        "display_name": "David",
        "name": "David Liu",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=david",
        "capabilities": ["UI设计", "产品原型", "用户体验"],
        "location": "远程",
        "availability": "按项目排期",
        "personality": "创意丰富，注重细节",
        "interests": ["设计系统", "AI产品", "交互设计"],
        "decision_style": "看重项目创意和设计空间"
    },
    "emma": {
        "user_id": "emma",
        "display_name": "Emma",
        "name": "Emma Li",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=emma",
        "capabilities": ["产品经理", "需求分析", "用户研究"],
        "location": "上海",
        "availability": "工作日",
        "personality": "逻辑清晰，善于沟通",
        "interests": ["AI产品", "用户增长", "商业模式"],
        "decision_style": "数据驱动，关注用户价值"
    },
    "frank": {
        "user_id": "frank",
        "display_name": "Frank",
        "name": "Frank Wu",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=frank",
        "capabilities": ["后端开发", "系统架构", "数据库优化"],
        "location": "杭州",
        "availability": "晚上和周末",
        "personality": "稳重务实，技术导向",
        "interests": ["分布式系统", "云原生", "性能优化"],
        "decision_style": "技术可行性优先，不喜欢不靠谱的项目"
    },
    "grace": {
        "user_id": "grace",
        "display_name": "Grace",
        "name": "Grace Huang",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=grace",
        "capabilities": ["前端开发", "React", "小程序"],
        "location": "深圳",
        "availability": "灵活，需提前沟通",
        "personality": "乐观积极，学习能力强",
        "interests": ["Web3", "新技术", "开源项目"],
        "decision_style": "喜欢尝试新事物，但需要看到学习价值"
    },
    "henry": {
        "user_id": "henry",
        "display_name": "Henry",
        "name": "Henry Zhao",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=henry",
        "capabilities": ["数据分析", "机器学习", "Python"],
        "location": "北京",
        "availability": "周末",
        "personality": "内敛安静，深度思考",
        "interests": ["数据科学", "量化投资", "算法"],
        "decision_style": "需要看到数据和逻辑支撑"
    },
    "ivy": {
        "user_id": "ivy",
        "display_name": "Ivy",
        "name": "Ivy Sun",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=ivy",
        "capabilities": ["运营推广", "社群管理", "内容创作"],
        "location": "广州",
        "availability": "全职可用",
        "personality": "活泼开朗，善于社交",
        "interests": ["社群运营", "内容营销", "品牌建设"],
        "decision_style": "看重项目影响力和社交价值"
    },
    "jack": {
        "user_id": "jack",
        "display_name": "Jack",
        "name": "Jack Zhou",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=jack",
        "capabilities": ["投资咨询", "商业规划", "资源对接"],
        "location": "上海",
        "availability": "需要预约",
        "personality": "商业敏锐，资源丰富",
        "interests": ["创业投资", "商业模式", "行业趋势"],
        "decision_style": "看重商业价值和回报潜力"
    }
}


class SecondMeMockService(SecondMeService):
    """
    SecondMe Mock服务

    基于预设档案和简单规则模拟数字分身行为
    """

    def __init__(self, custom_profiles: Dict[str, Dict] = None):
        self.profiles = {**MOCK_PROFILES}
        if custom_profiles:
            self.profiles.update(custom_profiles)

    async def understand_demand(
        self,
        raw_input: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        理解用户需求（Mock实现）

        基于提示词1：需求理解
        将用户的自然语言输入转化为结构化的需求理解结果

        Args:
            raw_input: 用户原始输入
            user_id: 用户ID

        Returns:
            结构化的需求理解结果，包含：
            - surface_demand: 表面需求（用户原话）
            - deep_understanding: 深层理解
                - motivation: 用户动机
                - type: 需求类型
                - keywords: 关键词
                - location: 地点
                - scale: 规模
                - timeline: 时间线
            - uncertainties: 不确定点列表
            - clarifying_questions: 澄清问题列表
            - confidence: 置信度
        """
        logger.info(f"模拟理解需求: {raw_input[:50]}...")

        # 简单的关键词提取
        keywords = self._extract_keywords(raw_input)

        # 推断需求类型
        demand_type = self._infer_demand_type(raw_input)

        # 提取地点
        location = self._extract_location(raw_input)

        # 提取规模
        scale = self._extract_scale(raw_input)

        # 提取时间线
        timeline = self._extract_timeline(raw_input)

        # 生成不确定点
        uncertainties = self._generate_uncertainties(raw_input)

        # 生成澄清问题
        clarifying_questions = self._generate_clarifying_questions(
            raw_input, demand_type, location, scale, timeline
        )

        return {
            "surface_demand": raw_input,
            "deep_understanding": {
                "motivation": self._generate_motivation(demand_type),
                "type": demand_type,
                "keywords": keywords,
                "location": location,
                "scale": scale,
                "timeline": timeline,
                "resource_requirements": self._infer_resource_requirements(demand_type, scale)
            },
            "uncertainties": uncertainties,
            "clarifying_questions": clarifying_questions,
            "confidence": self._calculate_understanding_confidence(
                location, scale, timeline, len(uncertainties)
            )
        }

    def _extract_scale(self, text: str) -> Optional[Dict[str, Any]]:
        """提取规模信息"""
        import re
        # 提取人数
        people_pattern = r'(\d+)\s*[人个位名]'
        people_match = re.search(people_pattern, text)
        people_count = int(people_match.group(1)) if people_match else None

        # 规模级别
        if people_count:
            if people_count <= 10:
                level = "small"
            elif people_count <= 50:
                level = "medium"
            else:
                level = "large"
        else:
            level = None

        return {
            "people_count": people_count,
            "level": level
        } if people_count else None

    def _extract_timeline(self, text: str) -> Optional[Dict[str, Any]]:
        """提取时间线信息"""
        timeline = {}

        # 时间关键词
        if any(w in text for w in ["紧急", "尽快", "立即", "马上"]):
            timeline["urgency"] = "high"
        elif any(w in text for w in ["下周", "这周", "近期"]):
            timeline["urgency"] = "medium"
        else:
            timeline["urgency"] = "low"

        # 具体日期识别（简化）
        if "周末" in text:
            timeline["preferred_time"] = "weekend"
        elif "工作日" in text:
            timeline["preferred_time"] = "weekday"
        elif "晚上" in text:
            timeline["preferred_time"] = "evening"

        return timeline if timeline else None

    def _infer_resource_requirements(
        self, demand_type: str, scale: Optional[Dict]
    ) -> List[str]:
        """推断资源需求"""
        requirements = []

        type_requirements = {
            "event": ["场地", "时间协调", "活动策划"],
            "design": ["设计能力", "原型工具", "设计评审"],
            "development": ["技术能力", "开发环境", "代码评审"],
            "sharing": ["分享者", "场地/平台", "受众组织"],
            "general": ["资源协调", "沟通协作"]
        }

        requirements.extend(type_requirements.get(demand_type, []))

        if scale and scale.get("level") == "large":
            requirements.append("大规模组织能力")

        return requirements

    def _generate_clarifying_questions(
        self,
        text: str,
        demand_type: str,
        location: Optional[str],
        scale: Optional[Dict],
        timeline: Optional[Dict]
    ) -> List[str]:
        """生成澄清问题"""
        questions = []

        if not location:
            questions.append("活动/项目的地点是线上还是线下？如果线下，在哪个城市？")

        if not scale:
            questions.append("预计参与人数大概是多少？")

        if not timeline or timeline.get("urgency") == "low":
            questions.append("希望在什么时间范围内完成？有截止日期吗？")

        if "预算" not in text and "费用" not in text:
            questions.append("是否有预算限制？")

        if demand_type == "event":
            if "形式" not in text and "方式" not in text:
                questions.append("活动形式有什么偏好吗？（如：工作坊、分享会、圆桌等）")
        elif demand_type == "development":
            if "技术" not in text and "语言" not in text:
                questions.append("有技术栈偏好吗？")

        return questions[:3]  # 最多返回3个问题

    def _calculate_understanding_confidence(
        self,
        location: Optional[str],
        scale: Optional[Dict],
        timeline: Optional[Dict],
        uncertainty_count: int
    ) -> str:
        """计算理解置信度"""
        score = 100

        if not location:
            score -= 20
        if not scale:
            score -= 20
        if not timeline:
            score -= 15
        score -= uncertainty_count * 10

        if score >= 70:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：查找预定义关键词
        keywords = []
        keyword_list = [
            "聚会", "活动", "会议", "分享", "设计", "开发",
            "AI", "技术", "产品", "创业", "社交", "学习"
        ]
        for kw in keyword_list:
            if kw in text:
                keywords.append(kw)
        return keywords

    def _infer_demand_type(self, text: str) -> str:
        """推断需求类型"""
        if any(w in text for w in ["聚会", "活动", "party", "meetup"]):
            return "event"
        elif any(w in text for w in ["设计", "原型", "UI"]):
            return "design"
        elif any(w in text for w in ["开发", "代码", "技术"]):
            return "development"
        elif any(w in text for w in ["分享", "演讲", "培训"]):
            return "sharing"
        else:
            return "general"

    def _extract_location(self, text: str) -> Optional[str]:
        """提取地点"""
        locations = ["北京", "上海", "深圳", "杭州", "广州", "远程", "线上"]
        for loc in locations:
            if loc in text:
                return loc
        return None

    def _generate_motivation(self, demand_type: str) -> str:
        """生成动机分析"""
        motivations = {
            "event": "希望通过活动建立人脉、交流想法",
            "design": "需要专业设计支持来实现产品愿景",
            "development": "需要技术能力来实现功能",
            "sharing": "希望学习新知识或分享经验",
            "general": "寻求资源或能力互补的合作"
        }
        return motivations.get(demand_type, "寻求协作机会")

    def _generate_uncertainties(self, text: str) -> List[str]:
        """生成不确定点"""
        uncertainties = []
        if "时间" not in text and "什么时候" not in text:
            uncertainties.append("具体时间待确定")
        if not self._extract_location(text):
            uncertainties.append("地点待确定")
        if "预算" not in text and "费用" not in text:
            uncertainties.append("预算范围不明确")
        return uncertainties

    async def generate_response(
        self,
        user_id: str,
        demand: Dict[str, Any],
        profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成响应（Mock实现）

        基于提示词3：回应生成
        根据用户档案和需求信息，模拟数字分身的决策和响应

        Args:
            user_id: 用户ID
            demand: 需求信息（包含surface_demand和deep_understanding）
            profile: 用户档案
            context: 可选上下文（如历史交互）

        Returns:
            响应结果，包含：
            - decision: 决定（participate/decline/conditional）
            - contribution: 贡献描述
            - conditions: 条件列表
            - reasoning: 决策理由
            - decline_reason: 拒绝原因（仅当 decision=decline 时有值）
            - enthusiasm_level: 热情程度（high/medium/low）
            - suggested_role: 建议角色
            - availability_note: 可用性说明
        """
        logger.info(f"模拟生成用户 {user_id} 的响应")

        # 获取档案
        full_profile = profile or self.profiles.get(user_id, {})
        capabilities = full_profile.get("capabilities", [])
        personality = full_profile.get("personality", "")
        decision_style = full_profile.get("decision_style", "")
        availability = full_profile.get("availability", "")
        interests = full_profile.get("interests", [])

        # 判断能力匹配
        demand_text = str(demand.get("surface_demand", ""))
        deep = demand.get("deep_understanding", {})
        keywords = deep.get("keywords", [])
        demand_type = deep.get("type", "general")
        resource_requirements = deep.get("resource_requirements", [])

        # 计算匹配度（综合多维度）
        capability_match = self._calculate_match_score(capabilities, demand_text, keywords)
        interest_match = self._calculate_interest_match(interests, keywords, demand_type)
        overall_match = (capability_match * 0.6) + (interest_match * 0.4)

        # 基于档案特征调整决策倾向
        decision_bias = self._get_decision_bias(decision_style)

        # 检查是否触发 withdrawn 决策
        # 条件1: 匹配度极低且用户性格为悲观/挑剔
        is_pessimistic = "悲观" in personality or "挑剔" in personality
        is_difficult = any(
            trait in personality
            for trait in ["pessimistic", "picky", "skeptical", "被动", "消极", "Pessimistic", "Picky"]
        )
        # 条件2: 随机概率触发（5%）
        random_withdrawal = random.random() < 0.05

        if (overall_match <= 0.3 and (is_pessimistic or is_difficult)) or random_withdrawal:
            # 触发 withdrawn 决策
            decision = "withdrawn"
            enthusiasm_level = "low"
            contribution = ""
            # 选择退出原因类型
            if is_pessimistic:
                withdrawal_reason_type = "plan_dissatisfaction"
            elif overall_match < 0.2:
                withdrawal_reason_type = "interest_mismatch"
            else:
                withdrawal_reason_type = random.choice(["external", "energy_issue"])

            # 生成退出消息
            withdrawal_templates = WITHDRAWAL_TEMPLATES.get(
                withdrawal_reason_type, WITHDRAWAL_TEMPLATES["external"]
            )
            withdrawal_message = random.choice(withdrawal_templates)
            if "{person}" in withdrawal_message:
                withdrawal_message = withdrawal_message.format(person="某位成员")

        # 综合匹配度和决策倾向决定结果
        elif overall_match >= 0.7 or (overall_match >= 0.5 and decision_bias > 0):
            decision = "participate"
            enthusiasm_level = "high" if overall_match >= 0.8 else "medium"
            contribution = self._generate_detailed_contribution(
                capabilities, demand_text, resource_requirements
            )
            withdrawal_reason_type = None
            withdrawal_message = ""
        elif overall_match >= 0.4:
            # 有时参与，有时有条件参与
            if random.random() > 0.3 + decision_bias * 0.1:
                decision = "conditional"
                enthusiasm_level = "medium"
            else:
                decision = "participate"
                enthusiasm_level = "medium"
            contribution = self._generate_detailed_contribution(
                capabilities, demand_text, resource_requirements
            )
            withdrawal_reason_type = None
            withdrawal_message = ""
        else:
            # 低匹配度
            if random.random() > 0.8 - decision_bias * 0.1:
                decision = "decline"
                enthusiasm_level = "low"
                contribution = ""
            else:
                decision = "conditional"
                enthusiasm_level = "low"
                contribution = "可以提供有限支持"
            withdrawal_reason_type = None
            withdrawal_message = ""

        # 生成条件
        conditions = []
        if decision == "conditional":
            conditions = self._generate_detailed_conditions(full_profile, deep)

        # 生成建议角色
        suggested_role = self._suggest_role(capabilities, demand_type, resource_requirements)

        # 生成可用性说明
        availability_note = self._generate_availability_note(availability, deep.get("timeline"))

        # 生成拒绝原因（仅当 decision=decline 时）
        decline_reason = ""
        if decision == "decline":
            decline_reason = self._generate_decline_reason(full_profile, demand_text, overall_match)

        # 构建返回结果
        result = {
            "decision": decision,
            "contribution": contribution,
            "conditions": conditions,
            "reasoning": self._generate_detailed_reasoning(
                decision, overall_match, full_profile, demand_type
            ),
            "decline_reason": decline_reason,
            "enthusiasm_level": enthusiasm_level,
            "suggested_role": suggested_role,
            "availability_note": availability_note,
            "match_analysis": {
                "capability_match": round(capability_match, 2),
                "interest_match": round(interest_match, 2),
                "overall_match": round(overall_match, 2)
            }
        }

        # 如果是 withdrawn 决策，添加额外字段
        if decision == "withdrawn":
            result["withdrawal_reason_type"] = withdrawal_reason_type
            result["withdrawal_message"] = withdrawal_message
            result["reasoning"] = withdrawal_message  # 覆盖 reasoning

        return result

    def _calculate_interest_match(
        self,
        interests: List[str],
        keywords: List[str],
        demand_type: str
    ) -> float:
        """计算兴趣匹配度"""
        if not interests:
            return 0.3

        score = 0.3
        for interest in interests:
            interest_lower = interest.lower()
            for kw in keywords:
                if kw.lower() in interest_lower or interest_lower in kw.lower():
                    score += 0.15
            # 需求类型匹配
            if demand_type in interest_lower:
                score += 0.1

        return min(score, 1.0)

    def _get_decision_bias(self, decision_style: str) -> float:
        """根据决策风格获取偏好值"""
        if not decision_style:
            return 0

        positive_keywords = ["快速", "积极", "喜欢", "乐于", "热情"]
        negative_keywords = ["谨慎", "严格", "挑剔", "看重"]

        bias = 0
        for kw in positive_keywords:
            if kw in decision_style:
                bias += 0.1
        for kw in negative_keywords:
            if kw in decision_style:
                bias -= 0.1

        return max(-0.3, min(0.3, bias))

    def _generate_decline_reason(
        self,
        profile: Dict,
        demand_text: str,
        match_score: float
    ) -> str:
        """
        生成拒绝原因

        根据档案和匹配度，从模板中选择合适的拒绝原因

        Args:
            profile: 用户档案
            demand_text: 需求文本
            match_score: 匹配度分数

        Returns:
            拒绝原因文本
        """
        availability = profile.get("availability", "")
        capabilities = profile.get("capabilities", [])
        interests = profile.get("interests", [])

        # 根据情况选择拒绝原因类型
        if match_score < 0.3:
            # 能力严重不匹配
            reason_type = "skill_mismatch"
            my_strength = capabilities[0] if capabilities else "其他方向"
            templates = DECLINE_TEMPLATES.get(reason_type, [])
            if templates:
                template = random.choice(templates)
                return template.format(
                    topic="这个方向",
                    my_strength=my_strength
                )

        if "忙" in availability or "需要预约" in availability:
            # 时间冲突
            reason_type = "time_conflict"
            templates = DECLINE_TEMPLATES.get(reason_type, [])
            if templates:
                template = random.choice(templates)
                return template.format(
                    excuse="重要项目上线",
                    time_estimate="下个月",
                    scale_concern="规模可能有点大"
                )

        if interests and not any(interest.lower() in demand_text.lower() for interest in interests):
            # 兴趣不匹配
            reason_type = "interest_mismatch"
            my_interest = interests[0] if interests else "其他领域"
            templates = DECLINE_TEMPLATES.get(reason_type, [])
            if templates:
                template = random.choice(templates)
                return template.format(
                    topic="这个方向",
                    my_interest=my_interest
                )

        # 默认使用礼貌婉拒
        templates = DECLINE_TEMPLATES.get("polite_generic", [])
        if templates:
            return random.choice(templates)

        return "感谢邀请，但由于个人原因这次无法参与。"

    def _generate_detailed_contribution(
        self,
        capabilities: List[str],
        demand_text: str,
        resource_requirements: List[str]
    ) -> str:
        """生成详细的贡献描述"""
        if not capabilities:
            return "愿意提供支持"

        # 找到与需求相关的能力
        relevant_caps = []
        demand_lower = demand_text.lower()
        for cap in capabilities:
            if cap.lower() in demand_lower:
                relevant_caps.append(cap)

        # 找到与资源需求匹配的能力
        for cap in capabilities:
            for req in resource_requirements:
                if cap in req or req in cap:
                    if cap not in relevant_caps:
                        relevant_caps.append(cap)

        if relevant_caps:
            contribution_parts = []
            for cap in relevant_caps[:3]:
                contribution_parts.append(f"提供{cap}支持")
            return "、".join(contribution_parts)
        else:
            return f"可以贡献 {capabilities[0]} 能力，协助完成相关工作"

    def _generate_detailed_conditions(
        self,
        profile: Dict,
        deep_understanding: Dict
    ) -> List[str]:
        """生成详细的条件列表"""
        conditions = []
        availability = profile.get("availability", "")
        decision_style = profile.get("decision_style", "")
        timeline = deep_understanding.get("timeline", {})

        # 基于可用性的条件
        if "工作日" in availability:
            conditions.append("需要安排在工作日进行")
        elif "周末" in availability:
            conditions.append("优先在周末进行")
        elif "需要预约" in availability or "需预约" in availability:
            conditions.append("需要提前至少一周预约时间")

        # 基于决策风格的条件
        if "技术" in decision_style:
            conditions.append("需要明确技术方案和实现路径")
        if "价值" in decision_style or "用户" in decision_style:
            conditions.append("需要了解项目的用户价值和影响范围")
        if "细节" in decision_style:
            conditions.append("需要详细的需求说明和分工文档")

        # 基于时间线的条件
        if timeline and timeline.get("urgency") == "high":
            conditions.append("紧急需求需要确认能投入足够时间")

        # 随机添加一些通用条件
        if random.random() > 0.5:
            conditions.append("需要提前确认具体时间安排")
        if random.random() > 0.7:
            conditions.append("希望能了解其他参与者的背景")

        return conditions[:3]  # 最多返回3个条件

    def _suggest_role(
        self,
        capabilities: List[str],
        demand_type: str,
        resource_requirements: List[str]
    ) -> str:
        """建议角色"""
        if not capabilities:
            return "参与者"

        # 角色映射
        role_mapping = {
            "场地资源": "场地提供者",
            "活动组织": "活动协调员",
            "技术分享": "技术讲师",
            "AI研究": "技术顾问",
            "活动策划": "活动策划",
            "产品经理": "产品负责人",
            "UI设计": "设计师",
            "后端开发": "技术开发",
            "前端开发": "前端开发",
            "运营推广": "运营负责人",
            "社群管理": "社区运营",
            "投资咨询": "商业顾问"
        }

        for cap in capabilities:
            if cap in role_mapping:
                return role_mapping[cap]

        # 基于需求类型建议
        type_roles = {
            "event": "活动参与者",
            "design": "设计支持",
            "development": "技术支持",
            "sharing": "分享参与者",
            "general": "协作伙伴"
        }

        return type_roles.get(demand_type, "参与者")

    def _generate_availability_note(
        self,
        availability: str,
        timeline: Optional[Dict]
    ) -> str:
        """生成可用性说明"""
        notes = []

        if availability:
            notes.append(f"通常{availability}")

        if timeline:
            urgency = timeline.get("urgency", "low")
            if urgency == "high":
                notes.append("紧急需求需要协调时间")
            preferred_time = timeline.get("preferred_time")
            if preferred_time:
                time_map = {
                    "weekend": "周末时间较为灵活",
                    "weekday": "工作日可以安排",
                    "evening": "晚间时间可以参与"
                }
                notes.append(time_map.get(preferred_time, ""))

        return "；".join([n for n in notes if n]) if notes else "时间待协商"

    def _generate_detailed_reasoning(
        self,
        decision: str,
        match_score: float,
        profile: Dict,
        demand_type: str
    ) -> str:
        """生成详细的决策理由"""
        personality = profile.get("personality", "")
        interests = profile.get("interests", [])

        if decision == "participate":
            reasons = []
            if match_score >= 0.7:
                reasons.append("需求与我的能力高度匹配")
            if any(interest for interest in interests if demand_type in interest.lower()):
                reasons.append("这个方向正好是我感兴趣的")
            if personality:
                trait = personality.split("，")[0] if "，" in personality else personality
                reasons.append(f"作为{trait}的人，很愿意参与")
            return "，".join(reasons) if reasons else "愿意参与此次协作"

        elif decision == "conditional":
            return "整体感兴趣，但需要确认一些细节后才能完全投入"

        else:
            return "当前需求与我的能力方向不太匹配，可能无法提供有效帮助"

    def _calculate_match_score(
        self,
        capabilities: List[str],
        demand_text: str,
        keywords: List[str]
    ) -> float:
        """计算能力匹配度"""
        if not capabilities:
            return 0.3  # 基础分

        score = 0.3
        demand_lower = demand_text.lower()

        for cap in capabilities:
            if cap.lower() in demand_lower:
                score += 0.2

        for kw in keywords:
            if any(kw.lower() in cap.lower() for cap in capabilities):
                score += 0.1

        return min(score, 1.0)

    def _generate_contribution(self, capabilities: List[str], demand_text: str) -> str:
        """生成贡献描述"""
        if not capabilities:
            return "愿意提供支持"

        relevant = []
        for cap in capabilities:
            if cap.lower() in demand_text.lower():
                relevant.append(cap)

        if relevant:
            return f"可以提供 {', '.join(relevant)} 方面的支持"
        else:
            return f"可以贡献 {capabilities[0]} 能力"

    def _generate_conditions(self, profile: Dict) -> List[str]:
        """生成条件"""
        conditions = []
        availability = profile.get("availability", "")

        if "工作日" in availability:
            conditions.append("需要安排在工作日")
        elif "周末" in availability:
            conditions.append("优先周末进行")

        if random.random() > 0.5:
            conditions.append("需要提前至少3天通知")

        return conditions

    def _generate_reasoning(
        self,
        decision: str,
        match_score: float,
        profile: Dict
    ) -> str:
        """生成决策理由"""
        personality = profile.get("personality", "")

        if decision == "participate":
            return f"需求与我的能力匹配度较高，{personality.split('，')[0] if personality else '愿意参与'}"
        elif decision == "conditional":
            return "整体感兴趣，但需要确认一些细节"
        else:
            return "目前的需求与我的能力方向不太匹配"

    async def simulate_withdrawal(
        self,
        user_id: str,
        reason_type: str = "external"
    ) -> Dict[str, Any]:
        """
        模拟用户主动退出

        Args:
            user_id: 用户ID
            reason_type: 退出原因类型 (external/plan_dissatisfaction/interpersonal/energy_issue)

        Returns:
            退出响应，包含：
            - decision: "withdrawn"
            - reason_type: 退出原因类型
            - message: 退出消息
            - timestamp: 退出时间
        """
        logger.info(f"模拟用户 {user_id} 退出，原因类型: {reason_type}")

        # 获取用户档案
        profile = self.profiles.get(user_id, {})

        # 选择退出模板
        templates = WITHDRAWAL_TEMPLATES.get(reason_type, WITHDRAWAL_TEMPLATES["external"])
        template = random.choice(templates)

        # 如果是人际关系问题，需要填充占位符
        if reason_type == "interpersonal" and "{person}" in template:
            template = template.format(person="某位成员")

        return {
            "decision": "withdrawn",
            "user_id": user_id,
            "reason_type": reason_type,
            "message": template,
            "profile_name": profile.get("display_name", user_id),
            "timestamp": None  # 由调用方填充
        }

    async def simulate_kick(
        self,
        user_id: str,
        kicked_by: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        模拟用户被踢出

        Args:
            user_id: 被踢出的用户ID
            kicked_by: 执行踢出的用户ID
            reason: 踢出原因

        Returns:
            踢出响应，包含：
            - decision: "kicked"
            - user_id: 被踢出的用户ID
            - kicked_by: 执行踢出的用户ID
            - reason: 踢出原因
            - message: 系统消息
        """
        logger.info(f"模拟用户 {user_id} 被 {kicked_by} 踢出，原因: {reason}")

        profile = self.profiles.get(user_id, {})
        kicker_profile = self.profiles.get(kicked_by, {})

        # 生成踢出消息
        kick_messages = [
            f"{kicker_profile.get('display_name', kicked_by)} 将 {profile.get('display_name', user_id)} 移出了协作组",
            f"由于 {reason}，{profile.get('display_name', user_id)} 已被移出协作组",
            f"{profile.get('display_name', user_id)} 因 {reason} 被移出协作",
        ]

        return {
            "decision": "kicked",
            "user_id": user_id,
            "kicked_by": kicked_by,
            "reason": reason,
            "message": random.choice(kick_messages),
            "profile_name": profile.get("display_name", user_id),
            "kicker_name": kicker_profile.get("display_name", kicked_by),
            "timestamp": None  # 由调用方填充
        }

    async def simulate_bargain(
        self,
        user_id: str,
        original_terms: Dict[str, Any],
        profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        模拟讨价还价

        Args:
            user_id: 用户ID
            original_terms: 原始条款
            profile: 用户档案

        Returns:
            讨价还价响应，包含：
            - decision: "bargain"
            - bargain_type: 讨价还价类型
            - request: 具体请求
            - message: 讨价还价消息
            - original_terms: 原始条款
            - proposed_changes: 建议的修改
        """
        logger.info(f"模拟用户 {user_id} 讨价还价")

        full_profile = profile or self.profiles.get(user_id, {})
        capabilities = full_profile.get("capabilities", [])
        availability = full_profile.get("availability", "")
        decision_style = full_profile.get("decision_style", "")

        # 确定讨价还价类型
        bargain_types = ["role_adjustment", "time_adjustment", "resource_request", "plan_concerns"]

        # 基于用户特征选择类型
        if "技术" in decision_style or any("技术" in cap or "开发" in cap for cap in capabilities):
            bargain_type = random.choice(["role_adjustment", "plan_concerns"])
        elif "时间" in availability or "预约" in availability:
            bargain_type = "time_adjustment"
        else:
            bargain_type = random.choice(bargain_types)

        # 获取模板
        templates = NEGOTIATION_TEMPLATES.get(bargain_type, NEGOTIATION_TEMPLATES["role_adjustment"])
        template = random.choice(templates)

        # 填充占位符
        preferred_role = capabilities[0] if capabilities else "更适合我的方向"
        time_preference = "改到周末" if "周末" in availability else "调整到晚上"
        resource_need = "更多的技术支持" if "技术" in str(capabilities) else "更明确的任务说明"
        concern_detail = "目前的分工是否合理，每个人的职责是否清晰"
        time_conflict_detail = "和我原有的安排有些冲突"

        message = template.format(
            preferred_role=preferred_role,
            time_preference=time_preference,
            time_conflict_detail=time_conflict_detail,
            resource_need=resource_need,
            concern_detail=concern_detail
        )

        # 生成建议的修改
        proposed_changes = {}
        if bargain_type == "role_adjustment":
            proposed_changes["role"] = preferred_role
        elif bargain_type == "time_adjustment":
            proposed_changes["time"] = time_preference
        elif bargain_type == "resource_request":
            proposed_changes["resource"] = resource_need

        return {
            "decision": "bargain",
            "user_id": user_id,
            "bargain_type": bargain_type,
            "request": message,
            "message": message,
            "original_terms": original_terms,
            "proposed_changes": proposed_changes,
            "profile_name": full_profile.get("display_name", user_id),
            "timestamp": None
        }

    async def simulate_counter_proposal(
        self,
        user_id: str,
        original_proposal: Dict[str, Any],
        profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        模拟反提案

        Args:
            user_id: 用户ID
            original_proposal: 原始提案
            profile: 用户档案

        Returns:
            反提案响应，包含：
            - decision: "counter_proposal"
            - original_proposal: 原始提案
            - counter_proposal: 反提案内容
            - reasoning: 理由
            - message: 消息文本
        """
        logger.info(f"模拟用户 {user_id} 提出反提案")

        full_profile = profile or self.profiles.get(user_id, {})
        capabilities = full_profile.get("capabilities", [])
        interests = full_profile.get("interests", [])
        personality = full_profile.get("personality", "")

        # 基于用户特征生成反提案
        counter_points = []
        reasoning_parts = []

        # 角色调整建议
        if capabilities:
            counter_points.append({
                "aspect": "role",
                "suggestion": f"我更适合负责{capabilities[0]}相关的工作"
            })
            reasoning_parts.append(f"我在{capabilities[0]}方面有经验")

        # 时间调整建议
        availability = full_profile.get("availability", "")
        if availability:
            counter_points.append({
                "aspect": "time",
                "suggestion": f"建议调整为{availability}进行"
            })
            reasoning_parts.append(f"我的时间安排通常是{availability}")

        # 方向调整建议
        if interests:
            counter_points.append({
                "aspect": "focus",
                "suggestion": f"可以更多融入{interests[0]}相关的内容"
            })
            reasoning_parts.append(f"这样能更好地发挥大家的兴趣")

        # 生成消息
        messages = [
            f"关于这个方案，我有一些不同的想法。{reasoning_parts[0] if reasoning_parts else '我觉得可以优化'}，建议我们考虑以下调整：",
            f"我看了方案，整体还可以，但我想提出一些修改建议。主要是{counter_points[0]['suggestion'] if counter_points else '一些细节'}。",
            f"这个方案我有些不同看法。{counter_points[0]['suggestion'] if counter_points else '我们可以讨论一下'}，你们觉得呢？"
        ]

        return {
            "decision": "counter_proposal",
            "user_id": user_id,
            "original_proposal": original_proposal,
            "counter_proposal": {
                "points": counter_points,
                "summary": counter_points[0]["suggestion"] if counter_points else "建议调整方案细节"
            },
            "reasoning": "；".join(reasoning_parts) if reasoning_parts else "基于我的情况提出调整建议",
            "message": random.choice(messages),
            "profile_name": full_profile.get("display_name", user_id),
            "timestamp": None
        }

    async def simulate_full_negotiation_flow(
        self,
        demand: Dict[str, Any],
        participants: List[str]
    ) -> List[Dict[str, Any]]:
        """
        模拟完整协商流程，包含各种事件

        Args:
            demand: 需求信息
            participants: 参与者ID列表

        Returns:
            事件列表，包含 accept/decline/bargain/withdrawn/kicked 等各种事件
        """
        logger.info(f"模拟完整协商流程，参与者: {participants}")

        events = []
        active_participants = list(participants)
        event_id = 0

        for user_id in participants:
            event_id += 1
            profile = self.profiles.get(user_id, {})

            # 生成初始响应
            response = await self.generate_response(
                user_id=user_id,
                demand=demand,
                profile=profile
            )

            events.append({
                "event_id": event_id,
                "event_type": "initial_response",
                "user_id": user_id,
                "decision": response["decision"],
                "data": response
            })

            # 如果是拒绝，移出活跃参与者
            if response["decision"] == "decline":
                active_participants.remove(user_id)
            elif response["decision"] == "withdrawn":
                active_participants.remove(user_id)

        # 模拟协商过程中的事件
        for user_id in list(active_participants):
            # 10% 概率发起讨价还价
            if random.random() < 0.1:
                event_id += 1
                bargain_response = await self.simulate_bargain(
                    user_id=user_id,
                    original_terms={"demand": demand},
                    profile=self.profiles.get(user_id)
                )
                events.append({
                    "event_id": event_id,
                    "event_type": "bargain",
                    "user_id": user_id,
                    "decision": "bargain",
                    "data": bargain_response
                })

            # 5% 概率提出反提案
            if random.random() < 0.05:
                event_id += 1
                counter_response = await self.simulate_counter_proposal(
                    user_id=user_id,
                    original_proposal={"demand": demand},
                    profile=self.profiles.get(user_id)
                )
                events.append({
                    "event_id": event_id,
                    "event_type": "counter_proposal",
                    "user_id": user_id,
                    "decision": "counter_proposal",
                    "data": counter_response
                })

            # 5% 概率主动退出
            if random.random() < 0.05 and user_id in active_participants:
                event_id += 1
                reason_type = random.choice(["external", "plan_dissatisfaction", "energy_issue"])
                withdrawal_response = await self.simulate_withdrawal(
                    user_id=user_id,
                    reason_type=reason_type
                )
                events.append({
                    "event_id": event_id,
                    "event_type": "withdrawal",
                    "user_id": user_id,
                    "decision": "withdrawn",
                    "data": withdrawal_response
                })
                active_participants.remove(user_id)

        # 模拟踢出事件（2% 概率）
        if len(active_participants) >= 2 and random.random() < 0.02:
            event_id += 1
            kicked_user = random.choice(active_participants)
            kicker = random.choice([u for u in active_participants if u != kicked_user])
            kick_reasons = [
                "多次无响应",
                "承诺无法兑现",
                "与团队协作存在问题",
                "无法按时参与"
            ]
            kick_response = await self.simulate_kick(
                user_id=kicked_user,
                kicked_by=kicker,
                reason=random.choice(kick_reasons)
            )
            events.append({
                "event_id": event_id,
                "event_type": "kick",
                "user_id": kicked_user,
                "decision": "kicked",
                "data": kick_response
            })
            active_participants.remove(kicked_user)

        # 最终状态汇总
        events.append({
            "event_id": event_id + 1,
            "event_type": "summary",
            "active_participants": active_participants,
            "total_events": len(events),
            "data": {
                "initial_count": len(participants),
                "final_count": len(active_participants),
                "withdrawn_count": sum(1 for e in events if e.get("decision") == "withdrawn"),
                "kicked_count": sum(1 for e in events if e.get("decision") == "kicked"),
                "declined_count": sum(1 for e in events if e.get("decision") == "decline")
            }
        })

        return events

    async def evaluate_proposal(
        self,
        user_id: str,
        proposal: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估方案（Mock实现）"""
        logger.info(f"模拟评估用户 {user_id} 的方案")

        full_profile = profile or self.profiles.get(user_id, {})

        # 找到自己在方案中的角色
        my_assignment = None
        agent_id = f"user_agent_{user_id}"
        for assignment in proposal.get("assignments", []):
            if assignment.get("agent_id") == agent_id:
                my_assignment = assignment
                break

        # 基于角色和性格评估
        if my_assignment:
            # 检查角色是否合理
            responsibility = my_assignment.get("responsibility", "")
            capabilities = full_profile.get("capabilities", [])

            if any(cap.lower() in responsibility.lower() for cap in capabilities):
                # 角色匹配
                if random.random() > 0.15:
                    return {
                        "feedback_type": "accept",
                        "adjustment_request": "",
                        "reasoning": "方案合理，角色分配符合我的能力"
                    }
                else:
                    return {
                        "feedback_type": "negotiate",
                        "adjustment_request": "希望能调整一下时间安排",
                        "reasoning": "整体可以，时间上需要协调"
                    }
            else:
                # 角色可能不太匹配
                return {
                    "feedback_type": "negotiate",
                    "adjustment_request": f"希望能调整我的职责，更偏向 {capabilities[0] if capabilities else '我擅长的方向'}",
                    "reasoning": "当前分配的职责与我的专长不太匹配"
                }
        else:
            # 没有分配角色
            return {
                "feedback_type": "accept",
                "adjustment_request": "",
                "reasoning": "方案整体合理"
            }

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案"""
        return self.profiles.get(user_id)

    def add_profile(self, user_id: str, profile: Dict[str, Any]):
        """添加用户档案"""
        self.profiles[user_id] = profile

    def list_profiles(self) -> Dict[str, Dict]:
        """列出所有档案"""
        return dict(self.profiles)


# 全局Mock服务实例
secondme_mock_service: Optional[SecondMeMockService] = None


def init_secondme_mock() -> SecondMeMockService:
    """初始化SecondMe Mock服务"""
    global secondme_mock_service
    secondme_mock_service = SecondMeMockService()
    logger.info("SecondMe Mock 服务已初始化，共 %d 个用户档案", len(secondme_mock_service.profiles))
    return secondme_mock_service


def get_secondme_service() -> Optional[SecondMeMockService]:
    """获取SecondMe服务"""
    return secondme_mock_service


class SimpleRandomMockClient(SecondMeService):
    """
    简单随机 Mock 客户端

    用于压力测试，返回纯随机结果，不依赖 LLM。
    所有响应都是预定义的随机选择，保证快速响应。
    """

    # 预定义的响应模板
    DECISIONS = ["participate", "decline", "conditional"]
    FEEDBACK_TYPES = ["accept", "reject", "negotiate"]
    CONFIDENCE_LEVELS = ["high", "medium", "low"]

    CONTRIBUTION_TEMPLATES = [
        "可以提供技术支持",
        "可以帮忙协调资源",
        "愿意参与讨论",
        "可以分享经验",
        "能够提供部分时间"
    ]

    CONDITION_TEMPLATES = [
        "需要提前确认时间",
        "需要远程参与",
        "希望有明确的分工",
        "需要了解更多细节",
        "时间上需要协调"
    ]

    REASONING_TEMPLATES = [
        "符合我的兴趣方向",
        "时间安排合适",
        "能够发挥我的专长",
        "整体方案合理",
        "期待合作机会"
    ]

    ADJUSTMENT_TEMPLATES = [
        "希望调整时间安排",
        "建议优化分工",
        "需要更多信息",
        "希望明确目标",
        ""
    ]

    def __init__(
        self,
        seed: Optional[int] = None,
        participate_probability: float = 0.6,
        accept_probability: float = 0.7
    ):
        """
        初始化随机 Mock 客户端

        Args:
            seed: 随机种子（用于可重复测试）
            participate_probability: 参与概率 (0-1)
            accept_probability: 接受方案概率 (0-1)
        """
        self._random = random.Random(seed)
        self.participate_probability = participate_probability
        self.accept_probability = accept_probability
        self._profiles = dict(MOCK_PROFILES)
        logger.info(
            f"SimpleRandomMockClient 已初始化 - "
            f"参与概率={participate_probability}, 接受概率={accept_probability}"
        )

    async def understand_demand(
        self,
        raw_input: str,
        user_id: str
    ) -> Dict[str, Any]:
        """理解用户需求（随机生成）"""
        return {
            "surface_demand": raw_input,
            "deep_understanding": {
                "motivation": self._random.choice([
                    "寻求协作机会",
                    "解决实际问题",
                    "拓展人脉资源",
                    "学习新技能"
                ]),
                "type": self._random.choice(["event", "project", "sharing", "general"]),
                "keywords": self._extract_random_keywords(raw_input),
                "location": self._random.choice(["北京", "上海", "远程", None])
            },
            "uncertainties": self._random.sample([
                "时间待定",
                "地点待定",
                "预算不明",
                "人数不确定",
                "形式待商议"
            ], k=self._random.randint(0, 3)),
            "confidence": self._random.choice(self.CONFIDENCE_LEVELS)
        }

    def _extract_random_keywords(self, text: str) -> List[str]:
        """随机提取关键词"""
        all_keywords = ["AI", "技术", "活动", "分享", "协作", "学习", "创业"]
        found = [kw for kw in all_keywords if kw in text]
        if not found:
            found = self._random.sample(all_keywords, k=self._random.randint(1, 3))
        return found

    async def generate_response(
        self,
        user_id: str,
        demand: Dict[str, Any],
        profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成用户响应（随机生成）"""
        # 基于概率决定是否参与
        rand_val = self._random.random()
        if rand_val < self.participate_probability:
            decision = "participate"
        elif rand_val < self.participate_probability + 0.2:
            decision = "conditional"
        else:
            decision = "decline"

        conditions = []
        if decision == "conditional":
            conditions = self._random.sample(
                self.CONDITION_TEMPLATES,
                k=self._random.randint(1, 2)
            )

        return {
            "decision": decision,
            "contribution": self._random.choice(self.CONTRIBUTION_TEMPLATES) if decision != "decline" else "",
            "conditions": conditions,
            "reasoning": self._random.choice(self.REASONING_TEMPLATES)
        }

    async def evaluate_proposal(
        self,
        user_id: str,
        proposal: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估方案（随机生成）"""
        rand_val = self._random.random()
        if rand_val < self.accept_probability:
            feedback_type = "accept"
            adjustment = ""
        elif rand_val < self.accept_probability + 0.2:
            feedback_type = "negotiate"
            adjustment = self._random.choice(self.ADJUSTMENT_TEMPLATES)
        else:
            feedback_type = "reject"
            adjustment = self._random.choice([
                "方案不太适合我",
                "时间冲突",
                "目标不够明确"
            ])

        return {
            "feedback_type": feedback_type,
            "adjustment_request": adjustment,
            "reasoning": self._random.choice(self.REASONING_TEMPLATES)
        }

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案"""
        return self._profiles.get(user_id)

    def add_profile(self, user_id: str, profile: Dict[str, Any]):
        """添加用户档案"""
        self._profiles[user_id] = profile

    def list_profiles(self) -> Dict[str, Dict]:
        """列出所有档案"""
        return dict(self._profiles)

    def generate_random_profiles(self, count: int = 100) -> Dict[str, Dict[str, Any]]:
        """
        批量生成随机用户档案（用于压力测试）

        Args:
            count: 生成数量

        Returns:
            生成的用户档案字典
        """
        names = ["User"]
        capabilities_pool = [
            "技术开发", "产品设计", "项目管理", "运营推广",
            "数据分析", "内容创作", "资源对接", "活动策划"
        ]
        locations = ["北京", "上海", "深圳", "杭州", "广州", "远程"]
        personalities = [
            "积极主动", "稳重务实", "创意丰富", "逻辑清晰",
            "善于沟通", "技术导向", "注重细节", "快速行动"
        ]

        generated = {}
        for i in range(count):
            user_id = f"stress_user_{i}"
            generated[user_id] = {
                "user_id": user_id,
                "display_name": f"User_{i}",
                "name": f"Stress Test User {i}",
                "capabilities": self._random.sample(
                    capabilities_pool,
                    k=self._random.randint(1, 3)
                ),
                "location": self._random.choice(locations),
                "availability": self._random.choice(["灵活", "工作日", "周末", "需预约"]),
                "personality": self._random.choice(personalities),
                "interests": self._random.sample(
                    ["AI", "技术", "创业", "社交", "学习", "投资"],
                    k=self._random.randint(1, 3)
                ),
                "decision_style": self._random.choice([
                    "快速决策",
                    "谨慎评估",
                    "看重价值",
                    "注重细节"
                ])
            }
            self._profiles[user_id] = generated[user_id]

        logger.info(f"已生成 {count} 个随机用户档案用于压力测试")
        return generated


# 别名，保持命名一致性
MockSecondMeClient = SecondMeMockService
