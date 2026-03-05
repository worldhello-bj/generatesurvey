import random
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Demographic dimension pools (Chinese context)
# ---------------------------------------------------------------------------

AGE_GROUPS = [
    {"label": "18-24岁", "weight": 0.12},
    {"label": "25-34岁", "weight": 0.22},
    {"label": "35-44岁", "weight": 0.20},
    {"label": "45-54岁", "weight": 0.18},
    {"label": "55-64岁", "weight": 0.15},
    {"label": "65岁及以上", "weight": 0.13},
]

GENDERS = [
    {"label": "男性", "weight": 0.49},
    {"label": "女性", "weight": 0.51},
]

EDUCATION_LEVELS = [
    {"label": "初中及以下", "weight": 0.20},
    {"label": "高中/中专", "weight": 0.28},
    {"label": "大专", "weight": 0.18},
    {"label": "本科", "weight": 0.26},
    {"label": "硕士及以上", "weight": 0.08},
]

INCOME_LEVELS = [
    {"label": "月收入3000元以下", "weight": 0.18},
    {"label": "月收入3000-6000元", "weight": 0.28},
    {"label": "月收入6000-10000元", "weight": 0.24},
    {"label": "月收入10000-20000元", "weight": 0.18},
    {"label": "月收入20000元以上", "weight": 0.12},
]

REGIONS = [
    {"label": "华东（上海/江苏/浙江等）", "weight": 0.22},
    {"label": "华北（北京/天津/河北等）", "weight": 0.15},
    {"label": "华南（广东/广西/海南等）", "weight": 0.16},
    {"label": "华中（湖北/湖南/河南等）", "weight": 0.14},
    {"label": "西南（四川/重庆/云南等）", "weight": 0.12},
    {"label": "东北（辽宁/吉林/黑龙江）", "weight": 0.08},
    {"label": "西北（陕西/甘肃/新疆等）", "weight": 0.08},
    {"label": "华东农村地区", "weight": 0.05},
]

OCCUPATIONS = [
    {"label": "企业职员", "weight": 0.25},
    {"label": "自由职业者", "weight": 0.10},
    {"label": "学生", "weight": 0.12},
    {"label": "政府/事业单位人员", "weight": 0.10},
    {"label": "个体经营者", "weight": 0.10},
    {"label": "农民/农业从业者", "weight": 0.12},
    {"label": "工人/蓝领", "weight": 0.11},
    {"label": "退休人员", "weight": 0.10},
]


def _weighted_choice(pool: List[Dict]) -> str:
    labels = [item["label"] for item in pool]
    weights = [item["weight"] for item in pool]
    return random.choices(labels, weights=weights, k=1)[0]


def generate_persona() -> Dict[str, str]:
    return {
        "age": _weighted_choice(AGE_GROUPS),
        "gender": _weighted_choice(GENDERS),
        "education": _weighted_choice(EDUCATION_LEVELS),
        "income": _weighted_choice(INCOME_LEVELS),
        "region": _weighted_choice(REGIONS),
        "occupation": _weighted_choice(OCCUPATIONS),
    }


def persona_to_prompt(persona: Dict[str, str], questionnaire_json: Dict[str, Any]) -> list:
    """Build the system+user message list for one respondent, ready for the chat completion API."""
    persona_desc = (
        f"你是一位来自{persona['region']}的{persona['age']}的{persona['gender']}，"
        f"职业是{persona['occupation']}，学历为{persona['education']}，"
        f"{persona['income']}。"
    )
    questions_text = _format_questions(questionnaire_json.get("questions", []))
    system_msg = (
        "你是一位真实的问卷调查受访者，请根据你的个人背景，认真且自然地回答以下问卷中的每一道题目。"
        "你的回答应该符合你的年龄、教育程度、职业和收入水平，体现真实的个体差异。"
        "请以 JSON 格式返回，格式如下：\n"
        '{"answers": [{"question_id": "q1", "answer": "你的回答"}, ...]}'
    )
    user_msg = (
        f"{persona_desc}\n\n请回答以下问卷：\n\n{questions_text}"
    )
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def _format_questions(questions: List[Dict]) -> str:
    lines = []
    for i, q in enumerate(questions, 1):
        qid = q.get("id", f"q{i}")
        qtype = q.get("type", "open")
        text = q.get("text", "")
        options = q.get("options", [])
        line = f"{qid}. [{qtype}] {text}"
        if options:
            line += "\n   选项：" + "、".join(options)
        lines.append(line)
    return "\n".join(lines)


def generate_personas(count: int, demographics_config: Dict[str, Any] = None) -> List[Dict[str, str]]:
    """Generate `count` persona dicts, optionally constrained by demographics_config."""
    return [generate_persona() for _ in range(count)]
