import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import settings
from services.ai_service import parallel_chat_completions
from services.cleaner_service import parse_survey_response
from services.export_service import build_dataframe, export_csv, export_excel
from services.ops_service import record
from services.population_service import generate_personas, persona_to_prompt

logger = logging.getLogger(__name__)
router = APIRouter()


class StartRequest(BaseModel):
    task_id: str
    sample_count: int = 100
    demographics_config: Optional[Dict[str, Any]] = None
    export_format: str = "csv"  # "csv" or "excel"


@router.post("/start")
async def start_generation(
    body: StartRequest,
    request: Request,
):
    user_id = request.client.host if request.client else "unknown"

    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        questionnaire_json_str = await r.get(f"questionnaire:{body.task_id}")
        if not questionnaire_json_str:
            raise HTTPException(status_code=404, detail="Task not found or expired")
        questionnaire = json.loads(questionnaire_json_str)

        gen_task_id = str(uuid.uuid4())
        await r.setex(
            f"gen_status:{gen_task_id}",
            settings.redis_task_ttl,
            json.dumps({"status": "pending", "total": body.sample_count, "done": 0, "user_id": user_id, "export_format": body.export_format}),
        )
    finally:
        await r.aclose()

    # Launch generation in background (pass no db — task creates its own session)
    asyncio.create_task(
        _run_generation(gen_task_id, questionnaire, body.sample_count, body.demographics_config, body.export_format, user_id)
    )

    return {"success": True, "gen_task_id": gen_task_id, "sample_count": body.sample_count}


async def _run_generation(
    gen_task_id: str,
    questionnaire: Dict,
    sample_count: int,
    demographics_config: Optional[Dict],
    export_format: str,
    user_id: str,
):
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await _update_status(r, gen_task_id, "running", 0, sample_count)

        personas = generate_personas(sample_count, demographics_config)
        prompts = [persona_to_prompt(p, questionnaire) for p in personas]
        questions = questionnaire.get("questions", [])

        # Run AI calls
        results = await parallel_chat_completions(prompts, model=settings.openai_model, concurrency=settings.ai_concurrency)

        # Parse and record
        all_answers = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        success_count = 0

        for i, (content, pt, ct) in enumerate(results):
            answers = parse_survey_response(content, questions)
            all_answers.append(answers)
            total_prompt_tokens += pt
            total_completion_tokens += ct
            if content:
                success_count += 1
            await _update_status(r, gen_task_id, "running", i + 1, sample_count)

        # Record ops
        try:
            await record(
                task_type="generate_response",
                model=settings.openai_model,
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
                success=(success_count > 0),
                user_id=user_id,
                metadata={"sample_count": sample_count, "success_count": success_count},
            )
        except Exception as exc:
            logger.error("Ops record failed: %s", exc)

        # Export
        df = build_dataframe(all_answers, personas, questions)
        if export_format == "excel":
            file_path = export_excel(df)
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = "survey_results.xlsx"
        else:
            file_path = export_csv(df)
            mime = "text/csv"
            filename = "survey_results.csv"

        download_token = str(uuid.uuid4())
        await r.setex(
            f"download:{download_token}",
            settings.download_token_ttl,
            json.dumps({"file_path": file_path, "mime": mime, "filename": filename}),
        )

        await _update_status(r, gen_task_id, "completed", sample_count, sample_count, download_token=download_token)

    except Exception as exc:
        logger.error("Generation failed: %s", exc)
        await _update_status(r, gen_task_id, "failed", 0, sample_count, error=str(exc))
    finally:
        await r.aclose()


async def _update_status(r, gen_task_id: str, status: str, done: int, total: int, **extra):
    data = {"status": status, "done": done, "total": total, **extra}
    await r.setex(f"gen_status:{gen_task_id}", settings.redis_task_ttl, json.dumps(data))


@router.get("/status/{gen_task_id}")
async def get_status(gen_task_id: str):
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw = await r.get(f"gen_status:{gen_task_id}")
        if not raw:
            raise HTTPException(status_code=404, detail="Task not found or expired")
        data = json.loads(raw)
    finally:
        await r.aclose()
    return {"success": True, **data}
