# 📄 CV Optimizer AI

🇬🇧 English | [🇫🇷 Français](README.fr.md)

> Upload a CV and (optionally) a job description → get an ATS-optimized CV, a tailored cover letter, a detailed analysis, and an explanation of every change made. Fully AI-powered, multi-language, multi-provider.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚠️ Disclaimer

AI-generated content can contain mistakes or inaccuracies. **You are responsible for
reviewing and validating the final CV and cover letter** before sending them to an
employer. This tool assists in CV writing — it does not replace your own judgment.

---

## ✨ Features

- **ATS-optimized CV** — rewrites your CV with the exact keywords and structure ATS systems scan for
- **Works with or without a job description** — provide one for a tailored result, or skip it for a general ATS optimization
- **Tailored cover letter** — unique to the job, no generic templates
- **CV analysis** — score, strengths, gaps, ATS issues, priority actions
- **Change log** — explains every modification and why it was made
- **AI refinement chat** — give instructions to adjust any output in natural language
- **Visual style picker** — 3 ready-made templates or an advanced mode (text color, heading color, font), with an instant, free, local preview that never consumes AI tokens
- **Bilingual interface** — the whole UI switches between English and French with one toggle, independent of the output language
- **Output language** — French, English, Spanish, German, Italian (independent of the interface language)
- **Session AI quota** — capped at 10 AI generations per session to keep the app sustainable
- **Multi-provider** — Anthropic Claude, Google Gemini (free), Groq (free)
- **DOCX & PDF export** — download CV and cover letter as `.docx` or `.pdf`, styled per your chosen visual style
- **Inline AI refinement with diff review** — refine the CV or cover letter by chat from the Results tab; CV changes are shown as a line-by-line diff you accept or ignore individually (or all at once) before they become permanent
- **Bundle download** — get everything in a single `.zip`
- **PII anonymization** — optionally strips name, email, phone, links before anything is sent to the AI

---

## 🏗️ Architecture

```
cv-optimizer/
├── app.py                  ← Streamlit UI + orchestration logic
├── src/
│   ├── parsers.py          ← PDF / DOCX / TXT extraction
│   ├── llm_client.py       ← Unified LLM interface (Anthropic / Gemini / Groq)
│   ├── prompts.py          ← All prompt templates with language injection
│   ├── utils.py            ← strip_fences() — cleans stray ``` fences from LLM output
│   ├── differ.py           ← Line-based diff + accept/ignore rebuild for CV refine
│   ├── exporters.py        ← Markdown → DOCX conversion (style-aware)
│   ├── pdf_exporter.py     ← Markdown → PDF conversion (style-aware, fpdf2)
│   ├── styles.py           ← Visual style definitions (templates, fonts, colors)
│   ├── preview.py          ← Free, local HTML live preview (no AI call)
│   ├── anonymizer.py       ← PII detection & placeholder substitution
│   ├── i18n.py             ← EN/FR UI string dictionary
│   └── guide_content.py    ← "How to Use" tab long-form content (EN/FR)
├── requirements.txt
├── Dockerfile
├── .env.example
├── README.md
└── README.fr.md
```

**Data flow:**

```
[CV file + optional job description]
         │
         ▼
    parsers.py  (extract text)
         │
         ▼
    prompts.py  (build prompts)
         │
         ▼
   llm_client.py  (call LLM API) → utils.strip_fences()
         │
         ├── CV Analysis            →  Tab "CV Analysis"
         ├── Optimized CV + Changes →  Tab "Results" › CV sub-tab
         └── Cover Letter           →  Tab "Results" › Cover Letter sub-tab
                  │                       │
                  │                       └─ refine chat → differ.py (CV diff review)
                  ▼
     exporters.py / pdf_exporter.py + styles.py  (→ styled .docx / .pdf)
```

---

## 💰 Costs & Providers

| Provider | Model | Cost | Free tier |
|---|---|---|---|
| **Anthropic** | claude-3-5-haiku | ~$0.01 / generation | ❌ |
| **Anthropic** | claude-3-5-sonnet | ~$0.04 / generation | ❌ |
| **Google** | gemini-2.5-flash | $0.00 | ✅ rate-limited |
| **Google** | gemini-2.0-flash | $0.00 | ✅ rate-limited |
| **Groq** | llama-3.1-8b | $0.00 | ✅ rate-limited |
| **Groq** | llama-3.3-70b | $0.00 | ✅ rate-limited |

**Recommendation for zero cost:** Google Gemini 2.5 Flash or Groq Llama 3.3 70B.
**Recommendation for best quality:** Anthropic claude-3-5-sonnet (~€0.04 per full run).

To keep the app sustainable regardless of provider, each browser session is capped at
**10 AI generations** (the initial "Generate" click counts as 1, each refinement chat
instruction also counts as 1).

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- An API key from at least one provider (see links below)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/cv-optimizer.git
cd cv-optimizer
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables (optional)

```bash
cp .env.example .env
# Edit .env and add your API key(s)
```

> API keys can also be entered directly in the app sidebar — no `.env` required.

### 5. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🐳 Docker

```bash
# Build
docker build -t cv-optimizer .

# Run
docker run -p 8501:8501 cv-optimizer

# With environment variables
docker run -p 8501:8501 \
  -e GOOGLE_API_KEY=your_key \
  cv-optimizer
```

---

## ☁️ Deploy to Streamlit Community Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io/)
3. Connect your GitHub repo
4. Set `app.py` as the main file
5. Add your API keys in **Settings → Secrets** (format: `GOOGLE_API_KEY = "your_key"`)
6. Deploy

---

## 🔑 Getting API Keys

| Provider | URL | Free? |
|---|---|---|
| Anthropic | https://console.anthropic.com/ | No (pay-as-you-go) |
| Google AI Studio | https://aistudio.google.com/app/apikey | Yes |
| Groq | https://console.groq.com/keys | Yes |

---

## 📋 Usage Guide

The app itself includes a **"📘 How to Use" tab** with the same walkthrough. The whole
interface — including this guide — switches between English and French with the toggle
at the very top of the page.

### Step 1 — Pick the interface and output language (top of the page)

These are the first two controls on the page: the **interface language** (English/French,
affects every label and button) and the **output language** (English, Français, Español,
Deutsch, Italiano — affects only the *generated* documents, independent of the interface
language and of the language of your input CV/job description).

### Step 2 — Provide inputs (tab "📤 Input")

- **CV**: upload a PDF, DOCX, or TXT file — or paste the text directly
- **Job description**: same options, **optional** — without it you still get a general
  ATS analysis and a generally optimized CV
- Click **🚀 Generate**

Processing takes 30–90 seconds (3 API calls), and counts as 1 of your 10 AI generations
for the session.

### Step 3 — Review results (tab "✨ Results")

At the top: pick one of 3 ready-made visual styles, or switch to Advanced mode to set your
own main text color, heading color, and font (4 choices) — the preview updates instantly
and never calls the AI. Below that, two sub-tabs:

- **CV** — the ATS-optimized CV, DOCX/PDF download buttons, the change log, and a
  collapsible **"🔄 Refine this CV with AI"** chat. Each refinement instruction shows its
  proposed changes as a line-by-line diff: accept or ignore each change individually, or
  use Accept All / Ignore All. Accepting is final for that session — a one-time warning
  reminds you before the first acceptance.
- **Cover Letter** — the letter, DOCX/PDF download buttons, and a similar refine chat;
  each response can replace the current letter with one confirmation click.

A "Download everything" ZIP button bundles both current documents.

### Step 4 — Check the analysis (tab "🔍 CV Analysis")
- Match score (0-100)
- Key strengths relative to the job
- Missing keywords and skills
- ATS technical issues
- Top 5 priority actions

Each refinement instruction (CV or cover letter) counts as 1 of the 10 AI generations
per session.

---

## 🔧 Technical Details

### Document parsing

| Format | Library | Notes |
|---|---|---|
| PDF | `pdfplumber` | Text-based PDFs only. Scanned images require OCR (not included). |
| DOCX | `python-docx` | Extracts paragraphs + table cells |
| TXT | built-in | UTF-8 with latin-1 fallback |

### LLM prompt design

Each prompt:
- Enforces output language at the top
- Uses strict section structure (forces markdown headings)
- Requests quantified outputs
- Uses a `---CHANGES---` delimiter to split CV from explanation in one call
- Falls back to a general-purpose version of the task when no job description is provided

### Visual style & DOCX/PDF export

`styles.py` defines `StyleConfig` (main text color, heading color, accent color, font,
plus per-template `heading_uppercase`/`heading_border` flags) and 3 ready-made templates
and 4 font choices. `preview.py` renders any `StyleConfig` as local HTML for an instant,
zero-token preview. `exporters.py` (DOCX) and `pdf_exporter.py` (PDF, via `fpdf2`) both
apply the same `StyleConfig` when building the export, parsing the markdown produced by
the LLM:
- `#` → H1 (centered, heading color)
- `##` → H2 (uppercase + bottom border, both togglable per style)
- `###` → H3
- `-` / `*` → bullet list
- `1.` → numbered list
- `**text**` → bold inline
- `*text*` → italic inline
- `---` → horizontal rule (border)

ATS-safe: no tables, no text boxes, no floating elements. LLM responses are also passed
through `utils.strip_fences()` to drop any stray ` ``` ` code-fence wrapper before display
or export.

### Diff-based CV refinement

`differ.py` computes a line-level diff (`difflib`) between the current accepted CV and a
new AI-refined version. Each chunk (`equal` / `added` / `removed` / `replaced`) gets a
`chunk_id`; per-chunk accept/ignore decisions are stored in session state and
`rebuild_text()` reconstructs the working CV from those decisions — nothing is applied
until explicitly accepted, and pure deletions only take effect via "Accept all".

---

## 🤝 Contributing

Pull requests welcome. For major changes, open an issue first.

```bash
# Run locally with hot reload
streamlit run app.py --server.runOnSave true
```

---

## 📜 License

MIT — see [LICENSE](LICENSE) file.
