import io
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from config import settings
from services.ai_service import chat_completion
from services.cleaner_service import parse_questionnaire_response
from services.ops_service import record

logger = logging.getLogger(__name__)
router = APIRouter()

PARSE_SYSTEM_PROMPT = """你是一个专业的问卷解析助手。请将用户提供的问卷内容解析为结构化的 JSON 格式。

返回格式如下（只返回 JSON，不要其他说明）：
{
  "title": "问卷标题",
  "questions": [
    {
      "id": "q1",
      "text": "问题内容",
      "type": "single_choice | multiple_choice | rating | open_ended",
      "options": ["选项A", "选项B"],
      "required": true
    }
  ]
}

注意：
- type 只能是 single_choice、multiple_choice、rating、open_ended 之一
- 如果问题没有选项（开放题），options 为空数组
- id 按 q1, q2, q3... 顺序编号
"""


async def _extract_text(file: UploadFile) -> str:
    content = await file.read()
    ct = (file.content_type or "").lower()
    filename = (file.filename or "").lower()

    if "text" in ct or filename.endswith(".txt"):
        return content.decode("utf-8", errors="replace")

    if filename.endswith(".pdf") or "pdf" in ct:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            return content.decode("utf-8", errors="replace")

    if any(filename.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(img, lang="chi_sim+eng")
        except Exception as exc:
            logger.warning("OCR failed: %s", exc)
            return ""

    # Fallback: try utf-8 decode
    return content.decode("utf-8", errors="replace")


@router.post("/parse")
async def parse_questionnaire(
    request: Request,
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
):
    if file is None and not text:
        raise HTTPException(status_code=400, detail="Either file or text must be provided")

    user_id = request.client.host if request.client else "unknown"
    task_id = str(uuid.uuid4())

    raw_text = text or await _extract_text(file)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from the uploaded file")

    messages = [
        {"role": "system", "content": PARSE_SYSTEM_PROMPT},
        {"role": "user", "content": f"请解析以下问卷：\n\n{raw_text[:settings.max_questionnaire_text_length]}"},
    ]

    try:
        content, prompt_tokens, completion_tokens = await chat_completion(
            messages,
            model=settings.parse_model,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        success = True
    except Exception as exc:
        logger.error("AI parse failed: %s", exc)
        content = ""
        prompt_tokens = 0
        completion_tokens = 0
        success = False

    parsed = parse_questionnaire_response(content)

    # Store parsed questionnaire in Redis temporarily
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.setex(
            f"questionnaire:{task_id}",
            settings.redis_task_ttl,
            json.dumps(parsed),
        )
        await r.aclose()
    except Exception as exc:
        logger.warning("Redis store failed: %s", exc)

    await record(
        task_type="parse_questionnaire",
        model=settings.parse_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        success=success,
        user_id=user_id,
    )

    return {
        "success": True,
        "task_id": task_id,
        "questionnaire": parsed,
    }
