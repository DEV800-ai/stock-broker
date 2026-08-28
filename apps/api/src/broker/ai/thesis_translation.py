import hashlib
import json
import time

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from broker.config import settings
from broker.models.thesis import AgentRun, StockThesis


class ThesisTranslation(BaseModel):
    thesis_id: int
    language: str
    why_interesting: str
    risk_factors: str
    sector_context: str | None = None
    peer_comparison: str | None = None
    elliott_wave_context: str | None = None
    news_summary: str | None = None
    catalysts: str | None = None


_AGENT_NAME = "thesis_translation_hebrew"

_SYSTEM_PROMPT = """\
You translate financial research text from English to Hebrew.

Keep the meaning faithful and descriptive. Do not add financial advice, do not
add buy/sell recommendations, and do not change uncertainty or risk language.
Keep stock tickers, model names, percentages, prices, and technical indicator
names recognizable.

Respond ONLY with valid JSON matching this schema:
{
  "why_interesting": "<Hebrew translation>",
  "risk_factors": "<Hebrew translation>",
  "sector_context": "<Hebrew translation or null>",
  "peer_comparison": "<Hebrew translation or null>",
  "elliott_wave_context": "<Hebrew translation or null>",
  "news_summary": "<Hebrew translation or null>",
  "catalysts": "<Hebrew translation or null>"
}
"""


class _TranslationPayload(BaseModel):
    why_interesting: str
    risk_factors: str
    sector_context: str | None = None
    peer_comparison: str | None = None
    elliott_wave_context: str | None = None
    news_summary: str | None = None
    catalysts: str | None = None


class ThesisTranslationError(Exception):
    pass


def _source_payload(thesis: StockThesis) -> dict:
    return {
        "thesis_id": thesis.id,
        "generated_at": thesis.generated_at.isoformat() if thesis.generated_at else None,
        "why_interesting": thesis.why_interesting,
        "risk_factors": thesis.risk_factors,
        "sector_context": thesis.sector_context,
        "peer_comparison": thesis.peer_comparison,
        "elliott_wave_context": thesis.elliott_wave_context,
        "news_summary": thesis.news_summary,
        "catalysts": thesis.catalysts,
    }


def _input_hash(thesis: StockThesis) -> str:
    payload = json.dumps(_source_payload(thesis), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _cached_translation(db: Session, thesis: StockThesis, ihash: str) -> ThesisTranslation | None:
    run = db.scalars(
        select(AgentRun)
        .where(AgentRun.agent == _AGENT_NAME)
        .where(AgentRun.ticker == thesis.ticker)
        .where(AgentRun.input_hash == ihash)
        .where(AgentRun.error == None)  # noqa: E711
        .order_by(desc(AgentRun.created_at))
    ).first()
    if not run or not run.output_json:
        return None
    return ThesisTranslation.model_validate(run.output_json)


def translate_thesis_to_hebrew(db: Session, thesis: StockThesis) -> ThesisTranslation:
    ihash = _input_hash(thesis)
    cached = _cached_translation(db, thesis, ihash)
    if cached:
        return cached

    run = AgentRun(
        agent=_AGENT_NAME,
        ticker=thesis.ticker,
        input_hash=ihash,
        input_json=_source_payload(thesis),
        model=settings.openai_model,
    )
    db.add(run)
    db.flush()

    client = OpenAI(api_key=settings.openai_api_key)
    t0 = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            max_completion_tokens=1200,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(_source_payload(thesis), ensure_ascii=False)},
            ],
        )
        run.prompt_tokens = response.usage.prompt_tokens if response.usage else None
        run.completion_tokens = response.usage.completion_tokens if response.usage else None
        raw_text = response.choices[0].message.content or "{}"
        try:
            parsed = _TranslationPayload.model_validate(json.loads(raw_text))
        except (json.JSONDecodeError, ValidationError) as exc:
            run.output_json = {"raw_text": raw_text}
            raise ThesisTranslationError(f"Hebrew translation response was invalid: {exc}") from exc

        translation = ThesisTranslation(thesis_id=thesis.id, language="he", **parsed.model_dump())
        run.output_json = translation.model_dump()
        return translation
    except Exception as exc:
        run.error = str(exc)
        raise
    finally:
        run.latency_ms = int((time.monotonic() - t0) * 1000)
        db.commit()
