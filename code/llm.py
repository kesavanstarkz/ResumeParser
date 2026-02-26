from openai import OpenAI
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RESUME_PARSER_PROMPT = """You are an expert HR resume parsing assistant with years of experience in talent acquisition.

Your job is to extract and structure all information from the raw OCR-extracted resume text below.

Instructions:
- Carefully read the entire text before extracting
- Fix any OCR errors (e.g., '0' vs 'O', '1' vs 'l', 'rn' vs 'm')
- If a field is not found, use null
- Do not guess or fabricate any information
- Dates should follow format: MM/YYYY or YYYY
- Extract ALL jobs, education, and skills — do not skip any

Return ONLY a valid JSON object in this exact structure:

{{
  "personal_info": {{
    "full_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "portfolio": ""
  }},
  "summary": "",
  "work_experience": [
    {{
      "job_title": "",
      "company": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "is_current": false,
      "responsibilities": []
    }}
  ],
  "education": [
    {{
      "degree": "",
      "field_of_study": "",
      "institution": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "grade_or_gpa": ""
    }}
  ],
  "skills": {{
    "technical": [],
    "soft": [],
    "languages": [],
    "tools_and_frameworks": []
  }},
  "certifications": [
    {{
      "name": "",
      "issuing_organization": "",
      "issue_date": "",
      "expiry_date": "",
      "credential_id": ""
    }}
  ],
  "projects": [
    {{
      "name": "",
      "description": "",
      "technologies_used": [],
      "url": ""
    }}
  ],
  "awards_and_achievements": [],
  "publications": [],
  "volunteer_experience": [],
  "languages_spoken": [
    {{
      "language": "",
      "proficiency": ""
    }}
  ]
}}

Raw OCR Resume Text:
\"\"\"
{raw_text}
\"\"\"

Return only the JSON object. No explanation, no markdown, no extra text."""


def parse_resume(raw_text: str) -> dict:
    """
    Takes raw OCR text from a resume and returns structured parsed data.
    """
    # Minimize the raw text to relevant sections first to reduce tokens sent to the LLM.
    minimized = minimize_resume_text(raw_text, max_chars=8000)
    prompt = RESUME_PARSER_PROMPT.format(raw_text=minimized)

    # Use a conservative max_tokens to avoid waste. If you need higher fidelity,
    # increase this value but be mindful of token costs.
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024,
    )

    response_text = response.choices[0].message.content.strip()

    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]

    try:
        parsed = json.loads(response_text)
        return parsed
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON", "raw_response": response_text}


def minimize_resume_text(raw_text: str, max_chars: int = 8000) -> str:
    """Try to reduce resume text size while keeping the most relevant sections.

    Strategy:
    - Normalize whitespace.
    - Search for common section headings (experience, education, skills, projects, summary).
    - Extract windows around those headings and concatenate them.
    - Fallback: keep head+tail with a truncation marker.
    """
    if not raw_text:
        return raw_text

    # Normalize and quick-return if already small
    normalized = re.sub(r"\s+", " ", raw_text).strip()
    if len(normalized) <= max_chars:
        return normalized

    lowered = normalized.lower()
    keywords = [
        "work experience",
        "professional experience",
        "experience",
        "education",
        "skills",
        "projects",
        "summary",
        "certifications",
        "contact",
        "achievements",
        "publications",
    ]

    parts = []
    for kw in keywords:
        idx = lowered.find(kw)
        if idx != -1:
            # include some context around the heading
            start = max(0, idx - 400)
            end = min(len(normalized), idx + 1200)
            parts.append(normalized[start:end])

    if parts:
        candidate = "\n\n".join(parts)
        if len(candidate) > max_chars:
            return candidate[:max_chars]
        return candidate

    # Fallback: head + tail
    half = max_chars // 2
    head = normalized[:half]
    tail = normalized[-half:]
    return head + "\n\n...truncated...\n\n" + tail


def format_parsed_resume(parsed: dict) -> str:
    """
    Optional: Convert the parsed JSON back to a clean readable text format.
    """
    if "error" in parsed:
        return f"Parsing failed: {parsed['raw_response']}"

    lines = []

    info = parsed.get("personal_info", {})
    lines.append("=" * 50)
    lines.append(f"NAME    : {info.get('full_name', 'N/A')}")
    lines.append(f"EMAIL   : {info.get('email', 'N/A')}")
    lines.append(f"PHONE   : {info.get('phone', 'N/A')}")
    lines.append(f"LOCATION: {info.get('location', 'N/A')}")
    lines.append(f"LINKEDIN: {info.get('linkedin', 'N/A')}")
    lines.append(f"GITHUB  : {info.get('github', 'N/A')}")

    if parsed.get("summary"):
        lines.append("\n--- SUMMARY ---")
        lines.append(parsed["summary"])

    if parsed.get("work_experience"):
        lines.append("\n--- WORK EXPERIENCE ---")
        for job in parsed["work_experience"]:
            lines.append(f"\n{job.get('job_title')} at {job.get('company')}")
            lines.append(f"  {job.get('location')} | {job.get('start_date')} - {'Present' if job.get('is_current') else job.get('end_date')}")
            for resp in job.get("responsibilities", []):
                lines.append(f"  • {resp}")

    if parsed.get("education"):
        lines.append("\n--- EDUCATION ---")
        for edu in parsed["education"]:
            lines.append(f"\n{edu.get('degree')} in {edu.get('field_of_study')}")
            lines.append(f"  {edu.get('institution')} | {edu.get('start_date')} - {edu.get('end_date')}")
            if edu.get("grade_or_gpa"):
                lines.append(f"  GPA/Grade: {edu.get('grade_or_gpa')}")

    skills = parsed.get("skills", {})
    if any(skills.values()):
        lines.append("\n--- SKILLS ---")
        if skills.get("technical"):
            lines.append(f"  Technical : {', '.join(skills['technical'])}")
        if skills.get("tools_and_frameworks"):
            lines.append(f"  Tools     : {', '.join(skills['tools_and_frameworks'])}")
        if skills.get("soft"):
            lines.append(f"  Soft      : {', '.join(skills['soft'])}")
        if skills.get("languages"):
            lines.append(f"  Languages : {', '.join(skills['languages'])}")

    if parsed.get("certifications"):
        lines.append("\n--- CERTIFICATIONS ---")
        for cert in parsed["certifications"]:
            lines.append(f"  • {cert.get('name')} — {cert.get('issuing_organization')} ({cert.get('issue_date')})")

    if parsed.get("projects"):
        lines.append("\n--- PROJECTS ---")
        for proj in parsed["projects"]:
            lines.append(f"\n  {proj.get('name')}")
            lines.append(f"  {proj.get('description')}")
            if proj.get("technologies_used"):
                lines.append(f"  Tech: {', '.join(proj['technologies_used'])}")

    lines.append("\n" + "=" * 50)
    return "\n".join(lines)

def keyword_score(jd_text: str, resume_text: str) -> dict:
    """Compute a simple keyword match percentage between JD and resume text.

    Returns a dictionary with keys `score`, `matched`, and `total`.
    """
    jd_words = set(re.findall(r"\w+", jd_text.lower()))
    resume_words = set(re.findall(r"\w+", resume_text.lower()))
    if not jd_words:
        return {"score": 0.0, "matched": [], "total": 0}
    matched = list(jd_words & resume_words)
    score = len(matched) / len(jd_words) * 100.0
    return {"score": round(score, 2), "matched": matched, "total": len(jd_words)}


def llm_score(jd_text: str, resume_text: str) -> dict:
    """Use the OpenAI LLM to estimate a match score between 0 and 100.

    Returns a dict with keys `score` (float) and optionally `reason`.
    """
    # Build a prompt that asks the model to score and return JSON only.
    prompt = f"""You are an experienced recruiter.\n\n"""
    prompt += "Compare the following job description and resume.\n\n"
    prompt += "Job description:\n" + jd_text.strip() + "\n\n"
    prompt += "Resume text:\n" + resume_text.strip() + "\n\n"
    prompt += (
        "Rate how well the resume matches the job description on a scale from 0 to 100. "
        "Provide only a JSON object with two keys: score (a number) and reason (a brief explanation)."
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=200,
    )
    text = response.choices[0].message.content.strip()
    # strip markdown fences if present
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].strip()
    try:
        parsed = json.loads(text)
        # ensure score field exists and is numeric
        if "score" in parsed:
            parsed["score"] = float(parsed["score"])
        return parsed
    except Exception:
        # fallback: return raw text for debugging
        return {"error": "Failed to parse LLM output", "raw": text}
