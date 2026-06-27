# 📄 CV Optimizer AI

> Upload a CV and a job description → get an ATS-optimized CV, a tailored cover letter, a detailed analysis, and an explanation of every change made. Fully AI-powered, multi-language, multi-provider.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- **ATS-optimized CV** — rewrites your CV with the exact keywords and structure ATS systems scan for
- **Tailored cover letter** — unique to the job, no generic templates
- **CV analysis** — score, strengths, gaps, ATS issues, priority actions
- **Change log** — explains every modification and why it was made
- **AI refinement chat** — give instructions to adjust any output in natural language
- **Multi-language** — French, English, Spanish, German, Italian
- **Multi-provider** — Anthropic Claude, Google Gemini (free), Groq (free)
- **DOCX export** — download CV and cover letter as `.docx` files
- **Bundle download** — get everything in a single `.zip`

---

## 🏗️ Architecture

```
cv-optimizer/
├── app.py              ← Streamlit UI + orchestration logic
├── src/
│   ├── parsers.py      ← PDF / DOCX / TXT extraction
│   ├── llm_client.py   ← Unified LLM interface (Anthropic / Gemini / Groq)
│   ├── prompts.py      ← All prompt templates with language injection
│   └── exporters.py    ← Markdown → DOCX conversion
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

**Data flow:**

```
[CV file + Job description]
         │
         ▼
    parsers.py  (extract text)
         │
         ▼
    prompts.py  (build prompts)
         │
         ▼
   llm_client.py  (call LLM API)
         │
         ├── CV Analysis  →  Tab "Analyse"
         ├── Optimized CV + Changes  →  Tab "Sortie optimisée"
         └── Cover Letter  →  Tab "Sortie optimisée"
                  │
                  ▼
           exporters.py  (→ .docx)
```

---

## 💰 Costs & Providers

| Provider | Model | Cost | Free tier |
|---|---|---|---|
| **Anthropic** | claude-3-5-haiku | ~$0.01 / generation | ❌ |
| **Anthropic** | claude-3-5-sonnet | ~$0.04 / generation | ❌ |
| **Google** | gemini-1.5-flash | $0.00 | ✅ 15 req/min, 1M tokens/day |
| **Google** | gemini-2.0-flash | $0.00 | ✅ |
| **Groq** | llama-3.1-8b | $0.00 | ✅ rate-limited |
| **Groq** | llama-3.3-70b | $0.00 | ✅ rate-limited |

**Recommendation for zero cost:** Google Gemini 1.5 Flash or Groq Llama 3.3 70B.
**Recommendation for best quality:** Anthropic claude-3-5-sonnet (~€0.04 per full run).

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

### Step 1 — Configure (sidebar)

- Select your LLM provider and model
- Enter your API key
- Choose the output language

### Step 2 — Provide inputs (tab "Entrée")

- **CV**: upload a PDF, DOCX, or TXT file — or paste the text directly
- **Job description**: same options
- Click **🚀 Générer**

Processing takes 30–90 seconds (3 API calls).

### Step 3 — Review results

**Tab "🔍 Analyse du CV"**
- Match score (0-100)
- Key strengths relative to the job
- Missing keywords and skills
- ATS technical issues
- Top 5 priority actions

**Tab "✨ Sortie optimisée"**
- Full ATS-optimized CV with download button
- Side panel explaining every change and why
- Complete cover letter with download button
- "Download all" ZIP button

### Step 4 — Refine (tab "💬 Affiner avec l'IA")

Type natural language instructions to adjust the outputs. Examples:

- `"Rends le ton plus formel"`
- `"Ajoute des mots-clés liés à la gestion de projet Agile"`
- `"Raccourcis la lettre de motivation de 30%"`
- `"Reformule le résumé pour un poste senior"`
- `"Make the cover letter sound less formal"`

Each refined version can be downloaded as DOCX.

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

### DOCX export

The exporter parses markdown produced by the LLM:
- `#` → H1 (centered, dark blue)
- `##` → H2 (uppercase, with bottom border)
- `###` → H3
- `-` / `*` → bullet list
- `1.` → numbered list
- `**text**` → bold inline
- `*text*` → italic inline
- `---` → horizontal rule (border)

ATS-safe: no tables, no text boxes, no floating elements.

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

---

## ⚠️ Disclaimer

This tool assists in CV writing. Always review AI-generated content before submitting an application. Do not present AI-generated text as your own without verification and personalization.
