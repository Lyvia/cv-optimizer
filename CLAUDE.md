# CV Optimizer — CLAUDE.md

## Stack
Python · Streamlit · Anthropic SDK
CSS custom injecté via `src/styles.py` → `st.markdown(unsafe_allow_html=True)`

## Commandes
```
streamlit run app.py                  # démarrer l'app
pip install -r requirements.txt       # installer les dépendances
pip install -r requirements-dev.txt   # + pytest pour lancer les tests
python -m pytest -v                   # lancer tous les tests (test_*.py)
docker build -t cv-optimizer .        # build Docker
```

## Structure
```
app.py                  # entry point Streamlit — orchestration UI
src/
  prompts.py            # system prompts LLM — fichier critique
  llm_client.py         # appels API Claude — point d'entrée unique
  parsers.py            # parsing des CVs entrants
  anonymizer.py         # anonymisation des données
  exporters.py          # export PDF/DOCX
  preview.py            # prévisualisation du CV
  guide_content.py      # contenu de guidage utilisateur
  styles.py             # CSS custom Streamlit
test_anonymizer.py      # tests unitaires anonymizer
.env                    # ne jamais lire ni modifier
```

## API Claude
Clé d'API : variable d'env `ANTHROPIC_API_KEY` uniquement.
Tous les appels API passent par `src/llm_client.py` — ne jamais appeler l'API ailleurs.
Modèle par défaut : `claude-sonnet-4-6`
Utiliser Opus uniquement si raisonnement complexe explicitement demandé.

## Style de code
- Typage Python systématique (type hints)
- Fonctions courtes, une responsabilité
- Commentaires en français

## Interdictions
- Ne jamais hardcoder une clé API ou donnée sensible
- Ne jamais modifier `src/prompts.py` sans confirmation explicite
- Ne jamais créer de nouveaux appels API Claude hors `src/llm_client.py`
- Ne pas introduire de dépendances absentes de `requirements.txt` sans demander
- Ne pas refactorer du code hors scope de la tâche demandée
- Ne pas utiliser `st.experimental_*` (APIs dépréciées)

## Avant toute tâche longue
- Poser 1 question si l'intention est ambiguë
- Annoncer les fichiers qui vont être modifiés
- Signaler si une modification touche `src/prompts.py` ou `src/llm_client.py`

# CV Optimizer AI — Claude Code Prompt (Passe 1)

## Context

This is a Streamlit app: CV + job description → ATS-optimized resume, cover letter, analysis.
All code, comments, prompts, and docstrings must be in English.
UI is bilingual EN/FR via `src/i18n.py`.

Start by reading all files in the repo before touching anything.

---

# CV Optimizer AI — Claude Code Task Prompt

## Before starting
Read every file in the repo. Work from what exists, not from assumptions.

---

## ⛔ API quota rule — read this first

**Never call any real LLM API during development or testing.**
The free tier daily quota is shared and limited. One accidental test run can block all testing for hours.

- Mock all `LLMClient.generate()` calls with `unittest.mock.MagicMock`
- Never run `streamlit run` to test LLM features
- Never write throwaway scripts that hit the API
- If a validation test requires a real API call, skip it and comment `# Requires live API`

Zero-cost tests (no mocking needed): `strip_fences`, `compute_diff`, `anonymize`, `parse_document`, `build_preview_html`, `DOCXExporter`, `PDFExporter`, `i18n` checks, syntax checks.

---

## Bug fixes

**BUG 1 — LLM output contains ```markdown fences**
Create `src/utils.py` with `strip_fences(text: str) -> str`.
Strip ` ```markdown `, ` ```md `, or ` ``` ` wrappers from the first and last lines.
Apply to all three LLM outputs in `app.py` immediately after each `.generate()` call.

**BUG 2 — `---CHANGES---` separator not found**
The current `_split_cv_and_changes()` in `app.py` is too brittle.
Try these patterns in order: `---CHANGES---`, `--- CHANGES ---`, then any heading matching
`r"^#{1,3}\s*(change|modification|modif|änder|cambio|modific)"` (case-insensitive, any language).
If nothing matches: store full text as `optimized_cv`, store `""` as `changes`. No fallback error string.

**BUG 3 — `style` keyword error in DOCXExporter**
`cv_to_docx()` and `cover_letter_to_docx()` must accept `style: CVStyle | None = None`.
Default to `TEMPLATES["classic"]` if None. Apply font, colors, heading_uppercase, heading_border from the style object.

---

## New features

### F1 — Gemini automatic model fallback on quota error

When a Gemini API call returns a 429 or quota-exceeded error, automatically retry with the next model in this priority list:

```
gemini-2.5-flash       → primary (250 req/day)
gemini-2.5-flash-lite  → fallback (1000 req/day, most generous)
```

In `llm_client.py`, update `_gemini()`:
- Catch exceptions where `"429"` or `"quota"` or `"resource exhausted"` appears in the error string (case-insensitive)
- Retry once with the next model in the fallback list
- If all models are exhausted, raise a clear `RuntimeError` explaining which models were tried
- Log which model is actually being used (return it alongside the response, or store in `st.session_state.active_model`)

Update `PROVIDERS["Google (Gemini)"]["models"]` to: `["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]`.
Remove `gemini-2.0-flash` (deprecated June 2026, shut down).

In `app.py`, show the active model name in the session counter line so the user knows which model is running.

### F2 — Real CV content in style preview

`build_preview_html()` in `src/styles.py` currently shows hardcoded mock content.
Add optional param `cv_markdown: str = ""`.
If provided and non-empty: extract the first 3-4 non-empty lines of actual content (strip markdown syntax, show as plain text) to replace the mock body.
In `app.py` Results tab, pass `st.session_state.optimized_cv` to the preview.
Preview must still update instantly on style change (no API call).

### F3 — PDF export via fpdf2

Add `fpdf2>=2.7.0` to `requirements.txt`.
Create `src/pdf_exporter.py` with `PDFExporter` class, methods `cv_to_pdf()` and `cover_letter_to_pdf()`, both accepting `(markdown_text: str, style: CVStyle) -> bytes`.
Parse the same markdown elements as `DOCXExporter`: H1, H2, H3, bullets, bold, italic, blank lines.
Font mapping (fpdf2 built-ins only): Calibri/Arial → Helvetica, Georgia/Times New Roman → Times.
Page size A4. Apply style colors and heading options.
Add PDF download buttons in Results tab alongside existing DOCX buttons.
Add i18n keys `dl_cv_pdf` and `dl_letter_pdf` in both EN and FR in `src/i18n.py`.

### F4 — Refine chat integrated in Results tab (Refine tab removed)

Remove the standalone Refine tab. The app now has 4 tabs: Guide | Input | Analysis | Results.

In Results tab, create two sub-tabs: **CV** and **Cover Letter**.

**CV sub-tab:**
- Display `current_cv` (starts as `optimized_cv`, updated on accept)
- DOCX + PDF download buttons
- Changes & explanations section
- Collapsible `🔄 Refine this CV` expander with chat input below

**Cover Letter sub-tab:**
- Display `current_cl` (starts as `cover_letter`)
- DOCX + PDF download buttons
- Collapsible `🔄 Refine this cover letter` expander with chat input

Session state: `cv_messages`, `cl_messages`, `current_cv`, `current_cl`.
Each chat message counts toward the 10-use session limit.

### F5 — Diff view with Accept/Reject (CV only)

Create `src/differ.py` using `difflib` (stdlib, no new dependency).

Behavior: after AI returns a refined CV, compute line-by-line diff between `current_cv` and the response.
- Equal lines: normal display
- Removed lines: red/pink background, no buttons
- Added/replaced lines: green background, `[✓ Accept]` and `[✗ Ignore]` buttons per chunk
- Global `[✓ Accept all]` and `[✗ Ignore all]` buttons at the top

State: store each chunk's decision in `st.session_state` (pending / accepted / ignored).
Rebuild and display the merged document live as decisions are made.
Always show a download button reflecting the current merged state.

**Irreversibility:** on any accept action, show once per session:
`st.warning("⚠️ Once accepted, this cannot be undone. The accepted version becomes your new baseline for future refinements.")`

**Reference:** always diff against `current_cv` (the last accepted state — sliding reference, Option B).

**Cover letter:** no diff. Show refined version below with `[Replace cover letter]` button + same warning.

---

## Constraints

- All code, comments, docstrings in English
- Add all new UI strings to `src/i18n.py` in both `en` and `fr`
- Mobile: no side-by-side columns in diff view
- `fpdf2` is the only new allowed dependency

---

## Validation (all checks must pass with zero real API calls)

```bash
# Syntax check
for f in app.py src/*.py; do python3 -m py_compile "$f" && echo "OK: $f"; done

# strip_fences
python3 -c "
from src.utils import strip_fences
assert strip_fences('\`\`\`markdown\nhello\n\`\`\`') == 'hello'
assert strip_fences('\`\`\`\nhello\n\`\`\`') == 'hello'
assert strip_fences('plain text') == 'plain text'
print('strip_fences OK')
"

# differ
python3 -c "
from src.differ import compute_diff
chunks = compute_diff('a\nb\nc', 'a\nB\nc')
assert any(c.type in ('replaced','removed','added') for c in chunks)
print('differ OK')
"

# Gemini fallback (mocked — no real API call)
python3 -c "
from unittest.mock import MagicMock, patch
from src.llm_client import LLMClient
client = LLMClient('Google (Gemini)', 'fake-key', 'gemini-2.5-flash')
# Simulate 429 on first model, success on second
call_count = 0
def fake_generate(*a, **kw):
    global call_count
    call_count += 1
    if call_count == 1:
        raise Exception('429 quota exceeded')
    return MagicMock(text='fallback response')
with patch('google.generativeai.GenerativeModel') as MockModel:
    MockModel.return_value.generate_content = fake_generate
    try:
        result = client._gemini('sys', 'user', 1000)
        assert call_count == 2, 'Should have retried once'
        print('Gemini fallback OK')
    except Exception as e:
        print(f'Gemini fallback test error: {e}')
"

# i18n completeness
python3 -c "
from src.i18n import UI
missing = set(UI['en']) - set(UI['fr'])
assert not missing, f'Missing FR keys: {missing}'
print('i18n OK')
"
```