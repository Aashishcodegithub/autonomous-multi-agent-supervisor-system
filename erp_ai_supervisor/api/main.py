# api/main.py
import os
import json
import logging
import base64
import math
from typing import Optional, Any, Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import your supervisor entry point
from supervisor.supervisor_agent import run_supervisor



# Company list tool
from tools.company_list_tool import get_company_list

# API key dependency (commented to run without API key; re-enable if needed)
# from .security import validate_api_key

# --------------------------------------------------
# CONFIG & LOGGING
# --------------------------------------------------
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("erp-api")

API_PREFIX = os.getenv("API_PREFIX", "/api")
GRAPH_DIR = os.getenv("GRAPH_DIR", "generated_graphs")

# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------
app = FastAPI(
    title="ERP Agentic Pipeline API",
    description="Wrapper API around your ReAct Supervisor",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep static mount (optional, not used anymore by UI)
if not os.path.exists(GRAPH_DIR):
    os.makedirs(GRAPH_DIR, exist_ok=True)

app.mount("/graphs", StaticFiles(directory=GRAPH_DIR), name="graphs")

# --------------------------------------------------
# Pydantic Models
# --------------------------------------------------
class RunRequest(BaseModel):
    query: str
    company: Optional[str] = None
    report: Optional[str] = None
    graph_type: Optional[str] = None
    title: Optional[str] = None

    class Config:
        extra = "allow"


class RunResponse(BaseModel):
    success: bool
    raw_output: Optional[Dict[str, Any]] = None
    summary_text: Optional[str] = None
    image_base64: Optional[str] = None
    sample_rows: Optional[Any] = None
    message: Optional[str] = None


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------
@app.get(f"{API_PREFIX}/health", tags=["health"])
def health():
    return {"status": "ok"}


# --------------------------------------------------
# COMPANY LIST ENDPOINT
# --------------------------------------------------
@app.get(f"{API_PREFIX}/companies", tags=["companies"])
def get_companies():  # previously: api_key: str = Depends(validate_api_key)
    try:
        companies = get_company_list.invoke({})
        return {"success": True, "companies": companies}
    except Exception as e:
        logger.exception("Failed to fetch company list")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# HUMANIZE COLUMN NAMES (NEW — PRESENTATION FIX)
# --------------------------------------------------
def humanize_key(col: str) -> str:
    col_upper = col.upper()

    if "DSPDISPNAME" in col_upper:
        return "Item Name"
    if "DSPCLQTY" in col_upper:
        return "Quantity"
    if "DSPCLRATE" in col_upper:
        return "Rate"
    if "DSPCLAMTA" in col_upper or "BSMAINAMT" in col_upper:
        return "Amount"
    if "BSSUBAMT" in col_upper:
        return "Sub Amount"

    # Fallback: clean snake-like names
    return col.replace("_", " ").title()


def humanize_sample_rows(rows):
    if not isinstance(rows, list):
        return rows

    cleaned = []
    for row in rows:
        if not isinstance(row, dict):
            cleaned.append(row)
            continue

        new_row = {}
        for k, v in row.items():
            new_row[humanize_key(k)] = v
        cleaned.append(new_row)

    return cleaned


# --------------------------------------------------
# JSON SANITIZER (NEW — API SAFETY FIX)
# --------------------------------------------------
def sanitize_for_json(obj):
    """
    Recursively convert NaN / Inf / -Inf to None
    so FastAPI can safely serialize the response.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    else:
        return obj


# --------------------------------------------------
# MAIN RUN ENDPOINT
# --------------------------------------------------
@app.post(f"{API_PREFIX}/run", response_model=RunResponse, tags=["run"])
def run_endpoint(payload: RunRequest):  # previously: api_key: str = Depends(validate_api_key)
    try:
        structured_input = payload.dict(exclude_none=True)

        logger.info(
            "Received run request: %s",
            {k: structured_input.get(k) for k in ("query", "company", "report")}
        )

        
        raw_result = run_supervisor(structured_input)

        logger.info(f"📨 Raw result from supervisor - Type: {type(raw_result).__name__}")
        if isinstance(raw_result, dict):
            logger.info(f"📨 Raw result keys: {list(raw_result.keys())}")
        else:
            logger.info(f"📨 Raw result (first 300 chars): {str(raw_result)[:300]}")

        # Parse supervisor output safely
        if isinstance(raw_result, dict):
            parsed_result = raw_result
            logger.info(f"✅ raw_result is dict, using directly")
        elif isinstance(raw_result, str):
            logger.info(f"🔄 raw_result is string, attempting JSON parse")
            try:
                parsed_result = json.loads(raw_result)
                logger.info(f"✅ Successfully parsed JSON string")
            except Exception as e:
                logger.warning(f"❌ Failed to parse JSON: {e}")
                parsed_result = {"message": raw_result}
                logger.info(f"✅ Using fallback message wrapper")
        else:
            logger.warning(f"⚠️ raw_result is {type(raw_result).__name__}, converting to string")
            parsed_result = {"message": str(raw_result)}

        logger.info(f"📊 Parsed result keys: {list(parsed_result.keys()) if isinstance(parsed_result, dict) else 'not a dict'}")

        # 🔒 SANITIZE RAW OUTPUT (NEW FIX)
        parsed_result = sanitize_for_json(parsed_result)

        summary_text = parsed_result.get("summary_text")
        sample_rows = None
        image_base64 = None

        logger.info(f"📄 summary_text: {summary_text[:100] if summary_text else 'None'}")

        # ✅ SUMMARY FALLBACK FIX (UNCHANGED)
        if not summary_text and isinstance(parsed_result, dict):
            summary_text = parsed_result.get("message")
            if summary_text:
                logger.info(f"📄 Using message as summary_text: {summary_text[:100]}")

        # Extract sample rows
        # COMMENTED OUT - Sample rows no longer needed in graph output
        # summary_block = parsed_result.get("summary")
        # if isinstance(summary_block, dict):
        #     sample_rows = summary_block.get("sample_rows")
        #     if sample_rows:
        #         logger.info(f"📋 Extracted sample_rows with {len(sample_rows)} rows")

        # 🚫 SUPPRESS SAMPLE ROWS FOR TABLE AGENT (UNCHANGED)
        # if isinstance(parsed_result, dict) and "table" in parsed_result:
        #     logger.info(f"🚫 Table detected, suppressing sample_rows")
        #     sample_rows = None

        # ✅ HUMANIZE SAMPLE DATA (NEW FIX)
        # if sample_rows:
        #     sample_rows = humanize_sample_rows(sample_rows)

        # 🔒 SANITIZE SAMPLE ROWS (NEW FIX)
        # if sample_rows:
        #     sample_rows = sanitize_for_json(sample_rows)

        # 🔑 BASE64 IMAGE FIX (HANDLES BOTH SINGLE AND MULTI-INTENT)
        img_path = parsed_result.get("image_path") or parsed_result.get("image")
        
        logger.info(f"🖼️ Looking for image_path: {img_path}")
        
        if img_path and isinstance(img_path, str) and os.path.exists(img_path):
            logger.info(f"✅ Found image file: {img_path}")
            try:
                with open(img_path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode("utf-8")
                logger.info(f"✅ Image converted to base64: {len(image_base64)} chars")
            except Exception as e:
                logger.error(f"❌ Failed to read/encode image: {e}")
        else:
            if not img_path:
                logger.warning(f"⚠️ No image_path in result")
            elif not isinstance(img_path, str):
                logger.warning(f"⚠️ image_path is not a string: {type(img_path)}")
            elif not os.path.exists(img_path):
                logger.warning(f"⚠️ Image file does not exist: {img_path}")

        logger.info(f"📤 Returning response - image_base64: {len(image_base64) if image_base64 else 'None'}, summary_text: {len(summary_text) if summary_text else 'None'}")

        return RunResponse(
            success=True,
            raw_output=parsed_result,
            summary_text=summary_text,
            image_base64=image_base64,
            sample_rows=sample_rows,
            message=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error while running supervisor")
        raise HTTPException(status_code=500, detail=str(e))
