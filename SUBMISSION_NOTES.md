# Submission Notes

## 1. Repository Analysis

### Existing Application Purpose

The application is a resume screening tool for recruiters. It compares a candidate resume with a job description, extracts skills and experience, calculates a match score, and then either generates interview questions or rejection feedback. During initial analysis, I found that the documentation and tests were out of sync with the actual code. The README described an LLM-based app, but the real app used a rule-based ResumeAnalyzer. The tests referenced a missing call_llm function, so they were outdated. The UI was also basic and paste-only, PII warnings were not clearly displayed, validation was weak, and raw resume text could appear in logs. So the project needed reliability, safety, documentation, and UX improvements.


### Current Architecture / Flow

- Frontend: `templates/index.html` collects job description text and either uploaded or pasted resume text.
- Upload API: `POST /upload-resume` extracts text from `.txt`, `.pdf`, and `.docx` without storing files.
- API: `POST /analyze` in `app.py` validates input and runs safety checks.
- Safety: `pii_validator.py` redacts PII; `SafetyGuard` blocks prompt-injection style text.
- Analysis: `ResumeAnalyzer` performs deterministic skill, experience, education, and score analysis.
- Chat Assistant: `POST /chat-assistant` answers follow-up recruiter questions from the latest analysis data.
- Persistence: SQLAlchemy stores analysis history in SQLite.
- History: `/history` renders previous analyses.

### Problems / Issues Identified

- Tests referenced a removed `call_llm` function and no longer matched the app.
- The backend accepted invalid or non-JSON request bodies too easily.
- The app could fail for first-time users if the SQLite tables were not initialized.
- The app later showed a `no such table: analysis_result` SQLite error when the DB existed without the expected table.
- Original resume text, including PII, was printed in debug logs.
- The frontend received PII warnings but did not display them.
- Error handling relied on browser alerts instead of persistent inline feedback.
- Dependencies included unused Hugging Face packages and missed `pytest`.

### Missing Capabilities

- No authenticated recruiter accounts.
- No analytics dashboard.
- No calibrated scoring from real hiring outcomes.
- No live LLM integration in the active app path.

### Risks Observed

- Privacy risk from resumes containing PII.
- Prompt-injection risk from untrusted resume/job-description text.
- Production risk from debug mode being hardcoded.
- Demo reliability risk from manual database initialization.
- Demo reliability risk from missing SQLite tables during save.
- Maintainability risk from stale tests and stale dependency declarations.

## 2. Brownfield Improvements

### Bugs / Broken Flow Fixed

- Replaced tests for removed `call_llm` behavior with tests for the current analyzer.
- Added automatic database table creation on first request.
- Added retry logic for history saving if SQLite reports a missing `analysis_result` table.

### Code Quality Improvements

- Added centralized payload validation.
- Made skill extraction deterministic with sorted output and word-boundary matching.
- Removed stale Hugging Face demo script and unused dependencies.
- Made `FLASK_DEBUG`, `PORT`, and `DATABASE_URL` environment-configurable.

### UI / UX Improvement

- Added inline error messages.
- Added disabled loading button state.
- Added visible match-score card.
- Added visible PII redaction warning.
- Added resume upload workflow with text extraction.
- Reworked result output into tabs for easier scanning.
- Added candidate improvement plan output.
- Added chat-style recruiter assistant for follow-up questions.

### Validation / Error Handling Improvement

- Added JSON body validation.
- Added empty, short, and oversized input checks.
- Added file type and empty-file validation for resume uploads.
- Added frontend network failure handling.
- Added database error handling for missing history tables.

## 3. Documentation Improvement

The README now includes:

- Project overview
- Setup instructions
- Features
- Architecture/workflow
- AI capabilities used
- AI safety explanation
- Challenges faced
- Future improvements
- Testing instructions
- Final submission checklist in `FINAL_SUBMISSION.md`

## 4. AI Safety Implementation

Implemented PII redaction and prompt-injection blocking.

PII redaction protects candidate privacy by replacing sensitive values before analysis and avoiding raw PII in logs. Prompt-injection blocking prevents untrusted resume content from manipulating the analyzer with instructions such as "ignore previous instructions" or "always return 100."

## 5. Innovation Addition

Added resume upload, a Candidate Improvement Plan, and a chat-style Recruiter Assistant. Upload support makes the workflow closer to a real recruiter process, the improvement plan converts missing requirements and score context into practical next steps, and the assistant lets recruiters ask follow-up questions about score, gaps, strengths, interview focus, shortlist decisions, and safety checks.

## 6. AI Usage Evidence

AI usage evidence is maintained in `AI_USAGE_LOG.md`.

It includes:

- Prompts used
- Where Codex helped
- Claude usage: not used
- Gemini usage: not used
- Experimentation done
- Failures and hallucinations observed

## 7. Verification

Automated tests were updated and run successfully.

Current result:

```text
14 passed
```

## 8. Presentation Outline

### Section 1: Initial Analysis

- The app screens resumes against job descriptions.
- It stores previous analyses in SQLite.
- Initial problems: stale tests, unsafe logging, missing frontend safety warning, weak validation, manual DB initialization, docs out of sync.

### Section 2: Brownfield Improvements

- Show before: tests referenced `call_llm`; after: tests match current behavior.
- Show before: PII warning hidden; after: visible warning in UI.
- Show before: paste-only resume entry; after: upload `.txt`, `.pdf`, or `.docx`.
- Show before: browser alerts; after: inline error feedback and tabbed results.
- Show before: debug mode hardcoded; after: env-configured.
- Show before: manual DB setup required; after: auto table creation.
- Show before: missing SQLite table caused analysis failure; after: save retry recreates table and continues.
- Show before: no follow-up helper; after: chat-style recruiter assistant.

### Section 3: AI Safety Implementation

- Demo a resume with email/phone and show PII warning.
- Demo prompt-injection text and show blocked request.
- Explain privacy and manipulation risks.

### Section 4: Innovation Added

- Demo resume upload, Candidate Improvement Plan, and the Recruiter Assistant.
- Explain how it uses analysis data to answer follow-up questions and generate next steps.
- Technical approach: rule-based generation from `analysis_data`.
