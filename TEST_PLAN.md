# CV Optimizer AI — Functional Test Plan

**Project**: CV Optimizer AI  
**Linear team**: CV Optimizer | **Linear project**: Bug Tracker  
**Last updated**: 2026-06-28  
**Status legend**: ✅ Passed / ❌ Failed / ⬜ Not tested / ⏭ Skipped

---

## Feature Coverage

| # | Feature | Tier | Test IDs |
|---|---------|------|----------|
| F1 | CV File Upload | 🔴 Critical | TC-01 → TC-06 |
| F2 | Job Description Input | 🔴 Critical | TC-07 → TC-10 |
| F3 | LLM Generation Pipeline | 🔴 Critical | TC-11 → TC-16 |
| F4 | Provider Fallback Logic | 🟠 High | TC-17 → TC-20 |
| F5 | PII Anonymization | 🟠 High | TC-21 → TC-24 |
| F6 | Results Display | 🔴 Critical | TC-25 → TC-29 |
| F7 | Diff View — Accept / Reject | 🔴 Critical | TC-30 → TC-36 |
| F8 | Refinement Chat | 🟠 High | TC-37 → TC-41 |
| F9 | CV Template Selection & Preview | 🟡 Medium | TC-42 → TC-46 |
| F10 | PDF Export | 🟠 High | TC-47 → TC-51 |

---

## F1 — CV File Upload

### Acceptance Criteria
- [x] AC-F1-01: A valid PDF or DOCX file is accepted and its text is extracted without error
- [ ] AC-F1-02: A file over the size limit is rejected with an explicit error message; the upload form remains accessible — **not verifiable**: no app-level size check exists (delegated to Streamlit's `server.maxUploadSize`)
- [x] AC-F1-03: An unsupported file type (e.g. .exe, .png) is rejected with an explicit error message — *.txt removed from this example list: it is a supported format, not unsupported*
- [x] AC-F1-04: Submitting without a file shows a clear validation message before any API call is made
- [x] AC-F1-05: A password-protected PDF is rejected with an explicit message (not a crash)

### Gherkin Scenarios

```gherkin
Feature: CV File Upload

  Scenario: Upload a valid PDF CV
    Given the user is on the upload page
    When they upload a standard 2-page PDF CV
    Then the file is accepted
    And the extracted text is visible or confirmed in the UI
    And the "Generate" button becomes available

  Scenario: Upload a valid DOCX CV
    Given the user is on the upload page
    When they upload a standard .docx CV file
    Then the file is accepted
    And the extracted text is confirmed
    And the "Generate" button becomes available

  Scenario: Upload a file exceeding the size limit
    Given the user is on the upload page
    When they upload a PDF file larger than the allowed limit
    Then an error message is displayed specifying the size constraint
    And the upload form remains visible and usable
    And no API call is triggered

  Scenario: Upload an unsupported file type
    Given the user is on the upload page
    When they upload a .png or .exe file
    Then an explicit error message is displayed
    And the system does not attempt to parse the file

  Scenario: Submit without uploading a file
    Given the user is on the upload page with no file selected
    When they click the "Generate" button
    Then a validation message is shown ("Please upload your CV first")
    And no API call is triggered
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-01 | Valid PDF upload | App loaded | 2-page PDF CV | File accepted, text extracted, Generate enabled | Text extracted correctly via `parse_document()`. Generate button is always enabled (not gated on upload); validation happens on click instead — see note below. | ✅ |
| TC-02 | Valid DOCX upload | App loaded | Standard .docx CV | File accepted, text extracted, Generate enabled | Text extracted correctly via `parse_document()`. Same Generate-button note as TC-01. | ✅ |
| TC-03 | File too large | App loaded | PDF > size limit | Error message with size limit, form stays open, no API call | Not automated: no app-level size check exists — oversized files are rejected by Streamlit's own `server.maxUploadSize` before any app code runs. Not exercisable via unit/AppTest. | ⏭ |
| TC-04 | Unsupported file type | App loaded | .txt file | Explicit rejection message, no parse attempt | **Discrepancy**: `.txt` is actually a *supported* CV format in `src/parsers.py` (confirmed by test). Rejection was instead tested with `.png` and with `.exe` (containing valid PDF bytes, to confirm rejection is extension-based, not content-based) — both correctly rejected with "Unsupported format" before parsing. | ✅ |
| TC-05 | Submit without file | App loaded | No file | Validation message shown, no API call | Verified via Streamlit AppTest: "Missing CV (file or pasted text)." shown, `session_state.llm` stays `None`, no LLM call attempted. | ✅ |
| TC-06 | Password-protected PDF | App loaded | Encrypted PDF | Explicit error (not a crash), form stays accessible | Verified via monkeypatched `PDFPasswordIncorrect` (simulates a real encrypted PDF without needing a new dependency) at both the parser level and end-to-end via AppTest: "Error reading CV: password required" shown, no crash/traceback. | ✅ |

**Automated**: `test_f1_cv_upload.py` (`python -m pytest test_f1_cv_upload.py -v`) — 8 tests, no real LLM calls.

**Notes on discrepancies vs. this plan's wording** (app behavior confirmed correct; plan wording updated to match):
- TC-01/TC-02: the Generate button is always present and enabled — there is no "enable on upload" gating in the app. Validation (CV present or not) happens when Generate is clicked, not before.
- TC-04: `.txt` is a supported format, not an unsupported one.

---

## F2 — Job Description Input

### Acceptance Criteria
- [ ] AC-F2-01: A job description entered in the text area is retained across reruns during the same session
- [ ] AC-F2-02: Submitting with an empty job description shows a validation message before any API call
- [ ] AC-F2-03: A very long job description (5000+ chars) is accepted without truncation or error
- [ ] AC-F2-04: Job description content is included in the prompt sent to the LLM

### Gherkin Scenarios

```gherkin
Feature: Job Description Input

  Scenario: Valid job description entered
    Given the user has uploaded a CV
    When they paste a job description and click Generate
    Then the generation starts with both inputs
    And the job description text is not lost during processing

  Scenario: Generate clicked with empty job description
    Given the user has uploaded a CV
    And the job description field is empty
    When they click Generate
    Then a validation message is shown
    And no API call is triggered

  Scenario: Very long job description
    Given the user has uploaded a CV
    When they paste a job description of 5000+ characters
    Then the input is accepted without truncation
    And generation completes normally
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-07 | Valid job description | CV uploaded | 300-word job description | Generation starts, both inputs used | | ⬜ |
| TC-08 | Empty job description | CV uploaded | Empty field | Validation message, no API call | | ⬜ |
| TC-09 | Very long job description | CV uploaded | 5000+ chars | Accepted, generation succeeds | | ⬜ |
| TC-10 | Session persistence | CV + JD entered, user interacts with another widget | — | JD content not lost on rerun | | ⬜ |

---

## F3 — LLM Generation Pipeline

### Acceptance Criteria
- [ ] AC-F3-01: Generation produces all four outputs: optimized CV, cover letter, analysis, and explanation of changes
- [ ] AC-F3-02: A loading indicator is visible during generation
- [ ] AC-F3-03: If the API returns an error, a user-facing message is shown and the app does not crash
- [ ] AC-F3-04: Generated content references information from both the uploaded CV and the job description
- [ ] AC-F3-05: Generation completes in under 60 seconds for a standard 2-page CV

### Gherkin Scenarios

```gherkin
Feature: LLM Generation Pipeline

  Scenario: Successful generation with all outputs
    Given the user has uploaded a valid CV
    And has entered a job description
    When they click Generate
    Then a loading indicator is shown during processing
    And four outputs appear on completion: optimized CV, cover letter, analysis, explanation
    And the content references the job description keywords

  Scenario: API error during generation
    Given the user has uploaded a valid CV and job description
    And the LLM API is unavailable
    When they click Generate
    Then a user-facing error message is displayed
    And the app does not crash or show a Python traceback
    And the user can try again

  Scenario: Generation with a minimal CV (1 page, sparse content)
    Given a CV with minimal content (name, one job, one skill)
    When the user generates
    Then the pipeline completes without error
    And the outputs are present (even if brief)
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-11 | Full generation success | CV + JD ready | Standard 2-page CV + job description | 4 outputs generated, loading shown, <60s | | ⬜ |
| TC-12 | All 4 outputs present | Generation complete | — | CV, cover letter, analysis, explanation all non-empty | | ⬜ |
| TC-13 | JD keywords in output | Generation complete | JD with specific keywords | Keywords appear in optimized CV | | ⬜ |
| TC-14 | API error handling | API unavailable (mocked) | Any valid input | User-facing error, no crash, retry possible | | ⬜ |
| TC-15 | Minimal CV input | CV with sparse content | 1-line CV + JD | Pipeline completes, outputs present | | ⬜ |
| TC-16 | Loading indicator visible | Generation in progress | — | Spinner or progress shown during API call | | ⬜ |

---

## F4 — Provider Fallback Logic

### Acceptance Criteria
- [ ] AC-F4-01: When Gemini 2.5 Flash returns a quota error, the app automatically retries with Gemini 2.5 Flash Lite
- [ ] AC-F4-02: The fallback is transparent to the user — generation completes without a manual retry
- [ ] AC-F4-03: If all providers fail, a clear error message is displayed (not a silent failure)
- [ ] AC-F4-04: The active provider used is identifiable in logs or UI (for debugging)

### Gherkin Scenarios

```gherkin
Feature: Provider Fallback Logic

  Scenario: Gemini Flash quota exceeded — automatic fallback
    Given the Gemini 2.5 Flash API returns a quota error (mocked)
    When the user triggers generation
    Then the app automatically retries with Gemini 2.5 Flash Lite
    And generation completes successfully
    And the user sees no error message

  Scenario: All providers fail
    Given all configured LLM providers return errors (mocked)
    When the user triggers generation
    Then a user-facing error message explains the issue
    And the app does not crash or hang
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-17 | Fallback on quota error | Flash quota error mocked | Valid CV + JD | Flash Lite used transparently, generation succeeds | | ⬜ |
| TC-18 | No user error on fallback | Fallback triggered | — | No error shown to user, outputs appear normally | | ⬜ |
| TC-19 | All providers fail | All APIs mocked as failing | Valid CV + JD | Clear error message, no crash | | ⬜ |
| TC-20 | Fallback does not loop | Flash Lite also quota-limited | Valid CV + JD | Fails gracefully after exhausting providers | | ⬜ |

---

## F5 — PII Anonymization

### Acceptance Criteria
- [ ] AC-F5-01: Names, email addresses, and phone numbers are replaced before the CV text is sent to the API
- [ ] AC-F5-02: The anonymized version is only used in the API call — the original data is preserved in the UI
- [ ] AC-F5-03: Anonymization does not alter the structure or meaning of the CV content
- [ ] AC-F5-04: A CV with no detectable PII is processed normally without error

### Gherkin Scenarios

```gherkin
Feature: PII Anonymization

  Scenario: CV with full PII is anonymized before API call
    Given a CV containing name, email, and phone number
    When the user generates
    Then the text sent to the API contains placeholders, not the real PII
    And the UI still displays the original personal information

  Scenario: CV with no PII processes normally
    Given a CV with no detectable personal information
    When the user generates
    Then the pipeline completes without error
    And no placeholder substitution errors occur
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-21 | Name anonymized in API call | CV with full name | Log / mock inspection | API receives placeholder, not real name | | ⬜ |
| TC-22 | Email anonymized | CV with email | Log / mock inspection | API receives placeholder email | | ⬜ |
| TC-23 | Original PII in UI | Generation complete | CV with name + email | UI shows original name and email in results | | ⬜ |
| TC-24 | CV with no PII | CV with no personal data | Valid CV + JD | Generation completes, no error | | ⬜ |

---

## F6 — Results Display

### Acceptance Criteria
- [ ] AC-F6-01: All four tabs (Optimized CV, Cover Letter, Analysis, Explanation) are visible after generation
- [ ] AC-F6-02: Each tab displays non-empty, readable content
- [ ] AC-F6-03: Switching between tabs does not trigger a new API call
- [ ] AC-F6-04: Content is still present after the user interacts with other UI elements (no state loss on rerun)

### Gherkin Scenarios

```gherkin
Feature: Results Display

  Scenario: All four result tabs appear after generation
    Given generation has completed successfully
    Then four tabs are visible: Optimized CV, Cover Letter, Analysis, Explanation
    And each tab contains non-empty content

  Scenario: Tab switching does not re-trigger generation
    Given the results are displayed
    When the user clicks between tabs multiple times
    Then no new API call is made
    And content in each tab remains unchanged

  Scenario: Results persist after UI interaction
    Given the results are displayed
    When the user changes a UI setting unrelated to generation
    Then all four result tabs still show their content
    And no content is lost
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-25 | All 4 tabs visible | Generation complete | — | 4 tabs present and labeled correctly | | ⬜ |
| TC-26 | All tabs non-empty | Generation complete | — | Each tab has readable content | | ⬜ |
| TC-27 | Tab switch — no API call | Results displayed | Click each tab | No spinner, no new API call | | ⬜ |
| TC-28 | State persistence on rerun | Results displayed | Interact with sidebar widget | Results still present in all tabs | | ⬜ |
| TC-29 | Results in correct tab | Generation complete | — | Optimized CV in CV tab, not mixed up | | ⬜ |

---

## F7 — Diff View: Accept / Reject

### Acceptance Criteria
- [ ] AC-F7-01: The diff view shows line-by-line differences between the original CV and the optimized version
- [ ] AC-F7-02: Accepting a change updates the reference baseline — subsequent diffs compare against the accepted version, not the original
- [ ] AC-F7-03: Rejecting a change restores that line to the baseline without affecting other changes
- [ ] AC-F7-04: Accepting all changes results in the optimized CV matching the LLM output
- [ ] AC-F7-05: Rejecting all changes results in the CV matching the original
- [ ] AC-F7-06: The Accept/Reject state is preserved across tab switches

### Gherkin Scenarios

```gherkin
Feature: Diff View — Accept / Reject

  Scenario: Diff displays changes correctly
    Given generation has completed
    When the user opens the diff view
    Then additions are highlighted in green
    And deletions are highlighted in red
    And unchanged lines are shown in neutral color

  Scenario: Accepting a change updates the baseline
    Given the diff view is open with multiple changes
    When the user accepts change #1
    Then change #1 is applied to the document
    And the baseline for subsequent diffs is now the version with change #1 accepted
    And change #2 still shows as a pending diff against the new baseline

  Scenario: Rejecting a change restores the baseline line
    Given the diff view is open with multiple changes
    When the user rejects change #2
    Then the original line is restored for that change
    And all other changes are unaffected

  Scenario: Accept all changes
    Given the diff view is open
    When the user accepts all changes one by one
    Then the final document matches the LLM-optimized output

  Scenario: Reject all changes
    Given the diff view is open
    When the user rejects all changes one by one
    Then the final document matches the original uploaded CV
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-30 | Diff view opens | Generation complete | Click diff tab | Line-by-line diff displayed | | ⬜ |
| TC-31 | Additions highlighted | Diff open | — | Added lines in green | | ⬜ |
| TC-32 | Deletions highlighted | Diff open | — | Removed lines in red | | ⬜ |
| TC-33 | Accept updates baseline | Diff open, 2+ changes | Accept change #1 | Subsequent diff uses accepted version as reference | | ⬜ |
| TC-34 | Reject restores line | Diff open, 2+ changes | Reject change #2 | That line reverts, others unchanged | | ⬜ |
| TC-35 | Accept all → matches LLM output | Diff open | Accept all changes | Final doc = LLM optimized output | | ⬜ |
| TC-36 | Reject all → matches original | Diff open | Reject all changes | Final doc = original uploaded CV | | ⬜ |

---

## F8 — Refinement Chat

### Acceptance Criteria
- [ ] AC-F8-01: The user can send a message in the refinement chat after generation
- [ ] AC-F8-02: Claude responds in context of the current CV and job description
- [ ] AC-F8-03: Chat history is preserved during the session (not reset on rerun)
- [ ] AC-F8-04: Sending an empty message does nothing (no API call, no error)
- [ ] AC-F8-05: The chat does not overwrite the existing generation results

### Gherkin Scenarios

```gherkin
Feature: Refinement Chat

  Scenario: User sends a refinement request
    Given the results are displayed
    When the user types "Make the summary more concise" and sends
    Then the chat shows the user message
    And Claude replies with a refined suggestion
    And the original results in the other tabs are not overwritten

  Scenario: Chat history persists on rerun
    Given the chat has 2 messages
    When a Streamlit rerun is triggered (e.g. by a widget interaction)
    Then both messages are still visible in the chat

  Scenario: Empty message does nothing
    Given the chat input is empty
    When the user clicks Send
    Then nothing happens — no API call, no error message
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-37 | Send refinement message | Results displayed | "Make summary shorter" | Response appears in chat, results untouched | | ⬜ |
| TC-38 | Chat history persists | 2 messages in chat | Trigger rerun | Both messages still visible | | ⬜ |
| TC-39 | Empty message | Chat input empty | Click Send | No API call, no error | | ⬜ |
| TC-40 | Response in context | Chat active | "Focus on Python skills" | Response references CV and job description content | | ⬜ |
| TC-41 | Chat does not overwrite results | Chat active | Any message | Optimized CV / cover letter tabs unchanged | | ⬜ |

---

## F9 — CV Template Selection & Preview

### Acceptance Criteria
- [ ] AC-F9-01: Three templates are available: Classic, Modern, Minimal
- [ ] AC-F9-02: Selecting a template updates the HTML preview without triggering a new API call
- [ ] AC-F9-03: The preview renders correctly for all three templates
- [ ] AC-F9-04: Template selection is preserved across tab switches within the session

### Gherkin Scenarios

```gherkin
Feature: CV Template Selection & Preview

  Scenario: Switch between templates
    Given the results are displayed
    When the user selects "Modern" template
    Then the HTML preview updates immediately
    And no new API call is triggered
    And the preview content matches the current CV content

  Scenario: All three templates render without error
    Given the results are displayed
    When the user cycles through Classic, Modern, and Minimal
    Then each preview renders without a blank page or error
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-42 | 3 templates available | Results displayed | — | Classic, Modern, Minimal options visible | | ⬜ |
| TC-43 | Template switch — no API call | Results displayed | Switch to Modern | Preview updates, no spinner/API call | | ⬜ |
| TC-44 | Classic renders | Results displayed | Select Classic | Preview visible, no blank/error | | ⬜ |
| TC-45 | Modern renders | Results displayed | Select Modern | Preview visible, no blank/error | | ⬜ |
| TC-46 | Minimal renders | Results displayed | Select Minimal | Preview visible, no blank/error | | ⬜ |

---

## F10 — PDF Export

### Acceptance Criteria
- [ ] AC-F10-01: Clicking Export triggers a file download in PDF format
- [ ] AC-F10-02: The exported PDF contains the current CV content (optimized or partially accepted)
- [ ] AC-F10-03: The exported PDF is not empty and is readable (valid PDF structure)
- [ ] AC-F10-04: Export works for all three templates
- [ ] AC-F10-05: If export fails, a user-facing error is shown (not a crash)

### Gherkin Scenarios

```gherkin
Feature: PDF Export

  Scenario: Export the optimized CV as PDF
    Given the optimized CV is displayed
    When the user clicks Export to PDF
    Then a PDF file is downloaded
    And the file contains the CV content
    And the file is a valid, readable PDF

  Scenario: Export after partial Accept/Reject
    Given the user has accepted 3 changes and rejected 2
    When they export to PDF
    Then the PDF reflects the accepted changes, not the full LLM output

  Scenario: Export failure is handled gracefully
    Given a PDF generation error occurs (mocked)
    When the user clicks Export
    Then a user-facing error message is displayed
    And the app does not crash
```

### Test Case Table

| ID | Description | Preconditions | Input | Expected Result | Actual Result | Status |
|----|-------------|---------------|-------|----------------|---------------|--------|
| TC-47 | Export triggers download | Results displayed | Click Export | PDF downloaded | | ⬜ |
| TC-48 | PDF is non-empty | Export complete | — | PDF contains CV content, not blank | | ⬜ |
| TC-49 | PDF is valid | Export complete | — | File opens in PDF reader without error | | ⬜ |
| TC-50 | Export reflects Accept/Reject state | 3 accepted, 2 rejected | Click Export | PDF matches partially accepted version | | ⬜ |
| TC-51 | Export error handled | fpdf2 error mocked | Click Export | User-facing error, no crash | | ⬜ |

---

## Regression Checklist (run after any significant change)

```markdown
### Regression — [Change description] — [Date]

#### Critical flows (always run)
- [ ] TC-01: Valid PDF upload succeeds
- [ ] TC-11: Full generation pipeline produces 4 outputs
- [ ] TC-25: All 4 result tabs visible and non-empty
- [ ] TC-33: Diff baseline slides correctly on Accept
- [ ] TC-47: PDF export triggers download

#### Session state sanity
- [ ] Results not lost after tab switch
- [ ] Chat history not reset on rerun
- [ ] Template selection not reset on rerun
- [ ] No KeyError in session_state on fresh load

#### Error handling sanity
- [ ] TC-05: Submit without file shows validation message
- [ ] TC-14: API error shows user-facing message, no crash
- [ ] TC-19: All providers failing shows error, no hang
```
