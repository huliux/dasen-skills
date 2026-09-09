# Content journeys

This file owns request-to-delivery behavior; fields and safety belong to contracts.md.

## 1. Resolve intent before production

Read the user's request and relevant existing project artifacts before asking questions. Use explicit file or series references first; otherwise inspect series files and their linked content packages within the current project. Do not infer the active series from modification time alone.

| Intent | Next action |
|---|---|
| Inspect content progress | Summarize the evidence through the read-only path below, then stop. |
| Start a series | Follow the startup path in section 2. A planning-only request stops with the plan. |
| Continue a series or article | Resolve the existing target and follow the continuation path in section 2. |
| Write or revise one article | Use available context directly; project and series setup are optional. |

Only production requests need the independent brief axes: `journey` (series / breaking / material), `length`, and `method` (original / pattern-adapt / revise). Infer them from the task instead of presenting schema fields as a questionnaire.

### Read-only progress inspection

Read the applicable series queue, briefs, receipts, and deliverable files. Use the status authority in `contracts.md`; report missing artifacts, stale queue entries, and uncertainty rather than silently repairing them. Explain the scope, evidenced progress, blockers or pending decisions, available outputs, and next useful action. Omit empty categories. If several scopes remain plausible, give a short choice with a recommendation.

Completion is the summary. Do not initialize a project or bundle, run mutating preflight, update status, append a receipt, repair a queue, or start the suggested next action. This branch concerns the user's content work; pure industry-news lookup remains outside this Skill.

### Ask for decisions, inspect facts

Reuse the user's answers and saved constraints. Researchable facts are the agent's work; personal experience and unresolved editorial intent may require the user. Present necessary independent choices together when useful, with a recommendation and a brief explanation of what changes. Ask sequentially when a later choice depends on the answer. Resume after the answer without replaying settled questions or asking “continue?” at each stage.

| Available input | Useful next action |
|---|---|
| A vague idea or personal experience | Propose concrete directions; ask for missing user-only actions or results when needed. Do not invent lived experience. |
| A claim without development | Build an outline whose sections earn their space. |
| An unfinished draft | Determine whether the gap is structure, evidence, or an unsupported topic; retain valid existing work. |
| Links, notes, or transcripts | Identify each source's contribution and find a supported common reader question. |
| A topic without an angle | Offer a few substantively different angles and recommend one for the reader and material. |
| A complete but unsatisfactory draft | Diagnose the specific failure and revise the affected parts. |

Proceed when the objective and inputs determine the next action. Brief Gate conditions in section 5 still apply; an already explicit decision satisfies the corresponding gate.

## 2. Series journey

Read project.md → series.md → this article's brief. Project and series supply defaults; brief owns the concrete objective.

### Startup

Converge on the audience, series promise, and first article angle. If the user already specified or accepted that direction, proceed; otherwise present a recommendation and resolve the remaining direction decision. Then create only the necessary project and series artifacts using the existing initializer and `templates/series-template.md`, compile the first brief, and advance through the required stages to the first local manuscript. Explicit planning-only requests end with the plan, without creating an article package. Remote delivery requires its own requested scope.

### Continuation

1. Identify the requested series and current package by `series_file`, brief identity, queue references, and actual files. When several series or unfinished packages are plausible, ask the smallest meaningful choice rather than selecting by recency or creating a duplicate.
2. Check brief status, the requested deliverable, and receipts together. Resume an unfinished article from the last evidenced valid stage. For `blocked`, inspect `blocker` and `resume_from`; newly supplied input may unblock that stage without restarting setup.
3. If the current article is complete and the next item is uniquely established by the agreed queue or user request, compile that next article. A candidate list alone is not an ordered commitment: offer a recommended choice when the next item is unsettled. With no next candidate, propose a direction from the series promise and available material.
4. Advance one article within the requested scope, preserving its identity and valid work. Synchronize uniquely matched series progress when status changes, following the contract. Completion does not authorize processing the rest of the queue.

If the user changes the reader, promise, or delivery scope, update the affected brief and record the decision; recheck only outputs whose validity depends on the change. Retain source material, valid assets, and prior receipts. Never mark an output valid merely because the file exists.


### Series phases and capacity

| Phase | Purpose and action | Evidence to advance |
|---|---|---|
| validating | Test the promise with 3–5 different angles, not a locked 20-article schedule | At least one angle clearly exceeds the account's own baseline or receives explicit reader feedback |
| establishing | Fix the useful promise, title pattern, deliverable, priority audience, and boundaries | Consecutive articles reliably fulfill the promise |
| expanding | Extend roles/difficulty/tools without repeatedly proving the same point | New scenarios still have material and feedback, rather than rewritten filler |
| compounding | Reuse, update, collect, adapt, close, or renew | Explicit continue/pivot/archive decision |

Choose useful content types without requiring all in every article: actionable templates/code/prompts/steps; mechanisms/comparison/selection/data judgment; real outcomes/role scenarios/before-after cases; and failures/costs/risks/applicability limits.

Schedule 70–80% of available capacity, reserving the rest for unexpected timely work rather than requiring a news quota. Commit to one current article plus three next candidates; distant ideas stay in the topic backlog. Validate a judgment with short content, expand to standard/deep only with a signal, and adapt into video/collections/tools only with continuing value. Human-reviewed data/comments update series hypotheses. Stop without evidence; series completeness does not justify filler.

## 3. Breaking journey

Read optional project → brief. Leave series unchanged; one-off voice/angle is not a long-term default.

| Response stage | Suggested length | Content |
|---|---|---|
| alert | quick | Event, three confirmed facts, one unknown, next observation |
| take | quick/standard | Importance, affected readers, current judgment and limits |
| demo | standard | Initial reproducible trial, process, results, pitfalls |
| deep | deep | Full evaluation, tutorial, mechanism, or industry impact |

Not every event needs all stages. Stop when evidence or feedback does not support the next step. Prefer official announcements, original video/participant text, or reproducible trials; seek an independent second source. One official source can suffice under policy, with explicit single-source disclosure in article and record. Maintain checked_at and separate confirmed, unconfirmed, and author judgment. Visible corrections must reach previously delivered platforms within actual account authorization; do not disguise a correction as an “update” or “adjustment.”

## 4. Pattern adaptation

Register the reference in sources. Analyze only reader promise, hook, information order, evidence density, rhythm, and CTA. Build a new outline from this article's facts, then write. Check for copied sentences, stories, metaphors, catchphrases, and identity. Record borrowed mechanisms and unborrowed content. The reference does not replace factual sources.

## 5. Decision gates

### Conditional Brief Gate

Pause for an unresolved decision about initial series direction/core promise change; unclear placement functionality/fact anchors/share; first-person persona without verified experience; unclear adaptation boundary/reference; a sensitive event, single anonymous source, or major unconfirmed claim; or requested formal publication/mass sending. An already explicit decision satisfies its gate. Otherwise proceed with safe defaults rather than adding an approval checkpoint.

### Publish Gate

After platform checks, authorized automation may reach the draft box. Formal publication/mass sending always requires explicit user confirmation.

## 6. Revision limit

Allow at most two automatic write/check/revise rounds. If still unsuccessful, record the blocker and required user decision rather than polishing indefinitely.

## 7. Completion

Inspection and planning-only stop at their boundaries above. Production requires clear axes/objective/temporary requirements/identity switches in brief; evidence meeting source policy; traceable prose without placeholders; applicable text/local-output readiness; and actual requested files, video, or draft ID at delivery with path/time recorded. Manual copying into an unintegrated platform does not justify a fabricated remote receipt.
