# Resume Parser with UI and ATS Scoring

This project provides a FastAPI-based resume parser using OCR + OpenAI LLM, along with a simple web UI that supports:

- Uploading single or multiple resumes (images or PDFs)
- Viewing parsed JSON data and formatted summary
- Entering a job description to compute a basic ATS-style keyword match score

Token usage is optimized by minimizing resume text before sending to the LLM and using conservative `max_tokens`.

## Getting Started

1. **Install dependencies** (from workspace root):

    ```powershell
    python -m venv .venv
    . .venv\Scripts\Activate
    pip install -r requirements.txt
    ```

2. **Configure environment**

    Create a `.env` file with your OpenAI API key:

    ```env
    OPENAI_API_KEY=sk-...
    ```

3. **Run the server**

    ```powershell
    uvicorn code.main:app --reload
    ```

4. **Open the UI**

    Visit `http://localhost:8000/ui` in your browser. From there you can:
    - Paste a job description at the top
    - Choose one or more resumes to upload
    - Click **Upload & Parse**

- After parsing completes, click **Compute GPT Score** to have the model evaluate each resume (a keyword score is shown alongside for comparison)
    - `POST /ocr/resumes` - multiple files
    - `POST /score` - JSON body: `{ "jd_text": "...", "resume_text": "..." }`

## Notes

- Scoring is simple keyword overlap; feel free to replace with embeddings/semantic similarity.
- The UI is intentionally minimal and can be extended with drag-and-drop, progress bars, etc.

Enjoy!
