# AI Usage Log / Prompt Reference Notes

This file records AI assistance, prompt experiments, and observed failures for the final submission.

## Tools Used

- Codex: repository analysis, code improvement, test repair, documentation drafting, and presentation-note structuring.
- Claude: not used in this implementation session.
- Gemini: not used in this implementation session.

## Prompts Used

### Prompt 1

> Please understand the code base.

Outcome:

- Identified Flask app structure.
- Found active rule-based analyzer in `app.py`.
- Found stale `main.py` Hugging Face snippet.
- Found tests referencing removed `call_llm`.
- Found frontend did not display `pii_warning`.

### Prompt 2

> Now the tasks that I have assigned is this is my friend project what I need to do is [mandatory deliverables...]

Outcome:

- Implemented brownfield fixes.
- Added AI safety feature.
- Added innovation feature.
- Updated README.
- Added this AI usage log and submission notes.

### Prompt 3

> Please add the upload resume thing and improve the UI.

Outcome:

- Added `/upload-resume`.
- Added `.txt`, `.pdf`, and `.docx` parsing.
- Rebuilt the UI into a recruiter workspace.
- Added upload validation and tests.

### Prompt 4

> Please add a chat bot type thing can we do this?

Outcome:

- Added `/chat-assistant`.
- Added `RecruiterAssistant`.
- Added chat UI in the results panel.
- Added tests and documentation for the assistant.

### Prompt 5

> An error occurred during analysis: sqlite3.OperationalError no such table: analysis_result.

Outcome:

- Hardened database initialization.
- Added `save_analysis_result()` retry logic.
- Added regression tests for missing SQLite tables.

## Experimentation Done

- Reviewed app routes, templates, tests, README, requirements, and vulnerability notes.
- Tested the existing test command path.
- Compared documented LLM architecture against the actual rule-based code.
- Reworked tests to target real behavior instead of mocking a missing LLM function.
- Tested resume upload and unsupported file handling.
- Tested chat assistant responses.
- Tested missing SQLite table recovery.

## Failures / Hallucinations Observed

- Existing README claimed Hugging Face / LLM behavior, but the active app path did not call an LLM.
- Existing tests hallucinated an `app.call_llm` function that did not exist.
- Existing vulnerability notes described prompt engineering mitigations that were not present in the actual code.
- Initial test execution failed because `pytest` was not available on PATH in the current shell.
- SQLite history save failed when the local database existed without the expected `analysis_result` table.

## Where AI Helped

- Codex helped trace the architecture and identify mismatches between docs, tests, and code.
- Codex helped design a scoped brownfield plan aligned with the required deliverables.
- Codex helped implement validation, safety checks, UI feedback, and test coverage.
- Codex helped implement resume upload, chat assistant, and SQLite recovery.
- Codex helped draft final README and presentation-ready notes.

## Notes for Final Presentation

- Be transparent that this version is deterministic/rule-based, not a live LLM app.
- Emphasize that safety improvements still matter because resumes are untrusted and often contain sensitive data.
- Use before/after examples:
  - hidden PII warning to visible PII warning
  - broken tests to current tests
  - manual DB setup to auto DB setup
  - pass/fail output to actionable improvement plan
  - no follow-up helper to chat-style recruiter assistant
  - missing SQLite table error to automatic recovery
