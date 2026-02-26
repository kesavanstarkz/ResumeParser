from fastapi import FastAPI, HTTPException, File, UploadFile, status
from typing import List
from fastapi.staticfiles import StaticFiles
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from ocr_utils import extract_and_parse_resume
from llm import parse_resume, format_parsed_resume, llm_score, keyword_score

app = FastAPI(
    title="Resume Parser API",
    description="Extract and parse resume data from images and PDFs using OCR + OpenAI LLM",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Serve a simple static UI if present at code/static mounted at /ui
BASE_DIR = os.path.dirname(__file__)
static_dir = os.path.join(BASE_DIR, "static")
if os.path.isdir(static_dir):
    app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")

@app.post("/ocr/resume", summary="Parse Resume File", tags=["Resume Parser"])
async def ocr_img(file: UploadFile = File(...)):
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg", "application/pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: {file.content_type}. Allowed: PNG, JPEG, JPG, PDF"
        )

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit"
        )

    try:
        extracted_text = extract_and_parse_resume(image_bytes, file.content_type)

        parsed = parse_resume(extracted_text)

        if "error" in parsed:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM parsing failed: {parsed['error']}"
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "filename": file.filename,
                "data": parsed,                          
                "formatted_text": format_parsed_resume(parsed)   
            }
        )

    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err)
        )


@app.post("/ocr/resumes", summary="Parse Multiple Resume Files", tags=["Resume Parser"])
async def ocr_resumes(files: List[UploadFile] = File(...)):
    """Accept multiple resume files and process them sequentially.
    Returns an array of results with parsed JSON and an optional formatted text.
    This processes files one-by-one to keep memory and token usage predictable.
    """
    results = []
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "application/pdf"]

    for file in files:
        entry = {"filename": file.filename}

        if file.content_type not in allowed_types:
            entry["error"] = f"Unsupported file format: {file.content_type}."
            results.append(entry)
            continue

        image_bytes = await file.read()
        if len(image_bytes) > 10 * 1024 * 1024:
            entry["error"] = "File size exceeds 10MB limit"
            results.append(entry)
            continue

        try:
            extracted_text = extract_and_parse_resume(image_bytes, file.content_type)

            parsed = parse_resume(extracted_text)

            if isinstance(parsed, dict) and "error" in parsed:
                entry["error"] = f"LLM parsing failed: {parsed.get('error')}"
                entry["raw_response"] = parsed.get("raw_response")
            else:
                entry["data"] = parsed
                entry["formatted_text"] = format_parsed_resume(parsed)

        except Exception as err:
            entry["error"] = str(err)

        results.append(entry)

    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "results": results})


from pydantic import BaseModel


class ScoreRequest(BaseModel):
    jd_text: str
    resume_text: str


@app.post("/score", summary="Calculate resume match score (GPT)", tags=["Resume Parser"])
async def score_resume(req: ScoreRequest):
    """Use GPT to predict how well the resume matches the job description.

    The response may also include a `reason` field with model rationale; we
    additionally include the simple keyword score for comparison.
    """
    llm_result = llm_score(req.jd_text, req.resume_text)
    keyword_result = keyword_score(req.jd_text, req.resume_text)
    # merge results, preserve llm_result keys (score/reason)
    return {"success": True, **llm_result, "keyword_score": keyword_result.get("score")}


@app.get("/", summary="Health Check", tags=["General"])
async def index():
    return {"success": True, "message": "Resume Parser API is running"}