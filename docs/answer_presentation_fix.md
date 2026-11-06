# Answer presentation verification

Verified locally on 6 November 2026.

## Encoding finding

The source database, UTF-8 API bytes and actual browser response already contained correct Unicode. The previously reported `Â` / `â€™` artifacts were introduced by inspecting a UTF-8 JSON file with Windows' default legacy text encoding. Medical text was not repaired by guessing substitutions. The new `scripts/render_chat_verification.py` reads and writes UTF-8 explicitly and produces a readable report from the actual browser captures. Browser assertions now check for replacement characters and common mojibake patterns, and verify the typographic apostrophe in the safety instructions.

## Repetition fix

Answer planning now merges overlapping source ranges, so an introduction followed by its list appears once. Exact source offsets and medical wording are preserved. When sections directly match the requested topic, unrelated sections are omitted. Further passages are retained when they add a requested detail, another requested medicine, or an explicit safety instruction. Duplicate and contained supporting passages are removed before citation numbering, preserving the correspondence between each displayed citation and its source.

The three reviewed examples—cetirizine sleepiness, antibiotics and colds, and dehydration symptoms—now each have one focused source citation. The antibiotics answer no longer appends the types-of-antibiotics catalogue. The dehydration answer retains the symptom list without adding causes and treatment sections. No medical facts, citations or clinical answers were hardcoded. Retrieval thresholds, canonical citation validation, source eligibility, spelling confirmation, personal-dose restrictions and emergency escalation remain enabled.

## Actual checks

- Real corpus: 33/33 supported-question and safety checks passed.
- Existing backend regression suite: 57 passed.
- Focused answer-plan tests: 4 passed, including two new tests for overlap merging and topic-focused Unicode output.
- Actual Edge browser: 4/4 workflows passed, including 20 different medical questions. Checks covered rendered response IDs, source links, exact supporting quotations, no duplicate/contained quotations, no encoding artifacts, the warfarin warning, the antibiotics/viral-infections statement, medicine-name confirmation and unsupported-evidence abstention. No browser JavaScript errors occurred.

Full captured examples: `runtime/answer-presentation-results.md`. Machine-readable browser evidence: `runtime/expanded-browser-results.json`. These are software and source-grounding checks, not independent clinical validation. Existing saved conversation responses remain historical records; new questions use the updated answer planner.
