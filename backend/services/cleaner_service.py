import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Optional[Dict]:
    """Try to extract a JSON object from a potentially noisy string."""
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding a top-level JSON object in the string
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def parse_questionnaire_response(raw: str) -> Dict[str, Any]:
    """Parse AI questionnaire structure response into canonical format."""
    data = _extract_json(raw)
    if not data:
        logger.warning("Could not parse questionnaire JSON from AI response")
        return {"questions": []}
    questions = data.get("questions", [])
    cleaned = []
    for i, q in enumerate(questions):
        cleaned.append({
            "id": q.get("id", f"q{i+1}"),
            "text": q.get("text", q.get("question", "")),
            "type": q.get("type", "single_choice"),
            "options": q.get("options", []),
            "required": q.get("required", True),
        })
    return {"title": data.get("title", ""), "questions": cleaned}


def parse_survey_response(raw: str, questions: List[Dict]) -> List[Dict[str, Any]]:
    """Parse one respondent's AI-generated answers into structured records."""
    data = _extract_json(raw)
    if not data:
        logger.warning("Could not parse survey response JSON")
        return _fallback_answers(questions)

    answers_raw = data.get("answers", [])
    # Build lookup by question_id
    answer_map = {}
    for item in answers_raw:
        qid = item.get("question_id", "")
        answer_map[qid] = item.get("answer", "")

    result = []
    for q in questions:
        qid = q.get("id", "")
        result.append({
            "question_id": qid,
            "question_text": q.get("text", ""),
            "answer": answer_map.get(qid, ""),
        })
    return result


def _fallback_answers(questions: List[Dict]) -> List[Dict[str, Any]]:
    return [
        {"question_id": q.get("id", ""), "question_text": q.get("text", ""), "answer": ""}
        for q in questions
    ]
