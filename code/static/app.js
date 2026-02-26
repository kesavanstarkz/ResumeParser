const form = document.getElementById("uploadForm");
const filesInput = document.getElementById("files");
const jdInput = document.getElementById("jd");
const scoreBtn = document.getElementById("scoreBtn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

let lastResults = [];

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    resultsEl.innerHTML = "";
    statusEl.textContent = "Uploading...";

    const files = filesInput.files;
    if (!files || files.length === 0) {
        statusEl.textContent = "Please select one or more files.";
        return;
    }

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }

    try {
        const resp = await fetch("/ocr/resumes", {
            method: "POST",
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json();
            statusEl.textContent = "Error: " + (err.detail || resp.statusText);
            return;
        }

        const body = await resp.json();
        statusEl.textContent = "Completed";

        if (body && body.results) {
            lastResults = body.results;
            body.results.forEach((r, idx) => {
                const card = document.createElement("div");
                card.className = "card";
                card.dataset.index = idx;
                const title = document.createElement("h3");
                title.textContent = r.filename || "unknown";
                card.appendChild(title);

                if (r.error) {
                    const err = document.createElement("div");
                    err.className = "error";
                    err.textContent = r.error;
                    card.appendChild(err);
                } else if (r.data) {
                    const pre = document.createElement("pre");
                    pre.textContent = JSON.stringify(r.data, null, 2);
                    card.appendChild(pre);

                    const btn = document.createElement("button");
                    btn.textContent = "Show formatted";
                    btn.addEventListener("click", () => {
                        const fm = document.createElement("pre");
                        fm.textContent = r.formatted_text || "";
                        card.appendChild(fm);
                        btn.disabled = true;
                    });
                    card.appendChild(btn);

                    const scoreDiv = document.createElement("div");
                    scoreDiv.className = "score";
                    card.appendChild(scoreDiv);
                }

                resultsEl.appendChild(card);
            });
        }
    } catch (err) {
        console.error(err);
        statusEl.textContent = "Upload failed: " + err.message;
    }
});

// scoring logic
scoreBtn.addEventListener("click", async () => {
    const jd = jdInput.value.trim();
    if (!jd) {
        alert("Please enter a job description");
        return;
    }
    statusEl.textContent = "Scoring...";
    for (let i = 0; i < lastResults.length; i++) {
        const r = lastResults[i];
        if (r.error) continue;
        const resumeText = r.formatted_text || JSON.stringify(r.data);
        try {
            const resp = await fetch("/score", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ jd_text: jd, resume_text: resumeText }),
            });
            const body = await resp.json();
            const card = resultsEl.querySelector(`.card[data-index='${i}']`);
            if (card && body.score !== undefined) {
                const scoreDiv = card.querySelector(".score");
                scoreDiv.textContent = `GPT Score: ${body.score}%`;
                if (body.reason) {
                    const reasonEl = document.createElement("div");
                    reasonEl.className = "reason";
                    reasonEl.textContent = `Reason: ${body.reason}`;
                    card.appendChild(reasonEl);
                }
                if (body.keyword_score !== undefined) {
                    const kEl = document.createElement("div");
                    kEl.className = "keyword";
                    kEl.textContent = `Keyword score: ${body.keyword_score}%`;
                    card.appendChild(kEl);
                }
            }
        } catch (err) {
            console.error("score error", err);
        }
    }
    statusEl.textContent = "Scoring completed";
});
