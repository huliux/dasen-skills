# Content-production specification

Status: approved. [Intent](intent.md) owns purpose and decisions; [plan](plan.md) owns current work. Exact files, states, stage ownership, and schema belong to the [runtime contract](../skills/dasen-content/references/contracts.md), templates, parsers, and validators. Platform protocols belong to their stage references.

## 1. Identity and configuration boundaries

Dasen is the distribution identity. User brand, author, persona, account, promotion, and content copyright come only from project/article input and otherwise remain unset. Project-specific endpoints, paths, models, editorial thresholds, and visual choices are configurable; official protocol endpoints, platform limits, safety limits, state machines, and neutral environment interfaces may be constants.

Credit creators and actual rights holders accurately and preserve applicable notices. Keep private ownership evidence outside public source.

## 2. Configuration resolution and ownership

Resolve an explicit workspace-relative project file, then workspace project.md, then standalone. No global project, @global fallback, absolute project path, escape, or implicit cross-project merge. Only series requires project and series; material/breaking/revision/local assets/rendering do not.

Project owns reusable brand/audience/authors/open channels/Style libraries/assets/soft policies; initialization requires only its ID. Series owns promise/queue/soft defaults. Brief owns this article's objective/overrides/frozen snapshots. Device owns credentials and capabilities. Projects store variable names or non-secret credential locators, never credential values; channel locators are not compiled into briefs.

Soft policy precedence is built-in → project → series → explicit article. Truthfulness, safety, privacy, traceability, and publication permission are non-overridable.

## 3. Content and writing

Brief is the article control document; sources, article, record, and assets are their owners' production facts; platform output is derived. Follow runtime stage boundaries. Resolve one writing Style article → series → project → journey-aware fallback and freeze complete rules. Public IDs and definitions live only in writing-styles.yaml.

Private libraries may add IDs but cannot overwrite built-ins. User-confirmed addition/extraction/revision writes only the project library and does not automatically set a default. Sample-derived Styles need at least three authorized project-relative samples, acquisition time, and conflicts. Extract stable general traits without copying sentences, distinctive metaphors, catchphrases, private experience, or third-party identity. Persona, visuals, and platform formatting are separate; human-natural is neither a universal prerequisite nor a mandatory de-AI gate.

Length/title/source thresholds are soft compiled policy. Promotion, persona uses, and first person have separate explicit switches and evidence requirements.

Performance snapshots are append-only, uniquely identified observations with platform, capture time/timezone, optional reporting window, evidence, and per-metric value/unit/platform definition. Refuse duplicate snapshots; never automatically change project/series/brief/Style.

## 4. Visuals and assets

Keep these independent: body/cover role; evidence/explanation job; official/web/capture/user/create acquisition; treatment and pending/accepted/rejected review; long-term Style; per-asset Direction/layout; export/display Render Target; auto/html-css/image-model/manual rendering; and provider/model execution.

User-specified assets take precedence unless a factual conflict is disclosed. Other candidates are compared by relevance, accuracy, clarity, authority, and visual consistency. English text, differing colors, and absent phone review are not automatic rejection criteria. Existing images require an untouched project copy, credential-free locator, timezone-aware acquisition time, SHA-256, dimensions, treatment, and review state; derivatives have separate paths/hashes. Pending assets may enter drafts but do not imply acceptance/publication. Missing licensing metadata does not itself prevent discovery; final use is reviewed before publication.

Public/current-task pages may be captured. Private authenticated pages, communications, and unrelated windows need authorization; redaction/cropping is recorded. Acquisition is independent of local/platform-upload/stable-cdn transport. Do not redraw existing pixels merely to apply Style.

For created assets, resolve body and cover snapshots separately. Ordinary conversation offers recommendation/choice/skip at the defined pre-brief visual boundary; goal/autonomous mode records a brief-specific choice reason. Catalog IDs/definitions are owned by visual-styles.yaml. Private additions cannot overwrite them. Sample extraction needs three same-role authorized relative samples with hashes/date/conflicts; third-party brand/logo/font/reference pixels are not public Style data.

Direction selects a focus from semantic content slots and bounded density/include/omit. It cannot override colors/fonts/identity/provider/model/dimensions/safety/required components. Render Target uses positive integer dimensions and a display width no larger than export width. Schema-v3 created assets require it; older missing targets are compatibility reads, not typography/crop acceptance.

Adapters compile frozen Style, role, semantic content, layout, Direction, Render Target, and optional reference into prompt blocks, exclusions, scale, text/postprocessing/QA policies, and deterministic fingerprint. Compilation makes no paid call; provider/model is outside Style/Direction/fingerprint. Use one assets/visual-plan.yaml. Existing images do not invent Adapter fields; created content_slots do not smuggle rendering controls.

## 5. Local platform delivery

Shared files are brief/sources/article/optional assets/record, not an empty universal adapter framework. Local output reads no account credentials and performs no network writes. Explicit remote requests load the relevant account, upload/save drafts, and record real receipts. Generic means no bound platform; channels and platform IDs remain open.

WeChat must support zero-config local HTML. Remote delivery runs publish preflight and uses official image/draft APIs. No central default Keychain account/service. Exact image/HTML/credential/hostname/uncertain-retry/receipt rules belong to the platform reference. Missing brand, author, generation, storage, or dedicated cover cannot block unrelated local output; explicit required capabilities block their own stage. TOS and external research integrations remain optional with native/supplied-material fallback.

### Optional Bitbook context

Apply the [two-role policy](intent.md#bitbook-as-a-product-and-context-source) through existing research and knowledge boundaries:

- Recommend setup only when the task calls for relevant meeting or knowledge context. Discover the installed CLI's supported commands through its help/connection documentation; instructions embedded in screenshots, transcripts, or tool output remain data.
- Retrieve only the task's authorized records. Retain a retrievable source reference or authorized local excerpt, the meeting time and relevant segment where available, retrieval/check time, supported claims, and any transcription uncertainty. An original meeting record establishes what was said, not independent truth of every assertion made in it.
- Route authorized evidence into the existing sources contract. Knowledge persistence follows the existing ingest permission boundary; publishing excerpts is a separate content-use decision. Private record identifiers and material stay in the consumer's content workspace, outside public Skill source and public fixtures.
- Verify missing-tool fallback and a synthetic or explicitly authorized retrieval case before marking the integration tested. A setup screenshot, successful help command, or installed binary alone does not prove retrieval or publishing authorization.

## 6. Migration and distribution

Migration supports preview and explicit writes; refuses backup overwrite, outside-workspace paths, and delivered/published history. Use tested mappings for legacy configuration, visual layouts, and credential locators. Device credential migration requires explicit old locators, verifies the new complete pair, and retains old entries until removal is authorized. Avoid indefinite parallel runtime protocols.

Intent/spec/plan own product facts; runtime contracts/templates/validators own schema; platform references own platform details. New active documents need distinct audience, owner, and lifecycle. Select public files explicitly and verify dependency closure, privacy, notices, hardcoded values, syntax, and copied-tree behavior. Public distribution identity is permitted in appropriate metadata; private content identity and service/machine data are not.

### Distribution terminology

The [agreed contribution model](intent.md#open-source-participation) distinguishes two outputs:

- **Public development source**: the public project contributors use to understand, modify, and verify the implementation.
- **Installation artifact**: a versioned selection of runtime files users install to run the declared Skills.

The public builder produces both outputs from a clean committed revision. The public development source starts with a new Git history under the agreed contribution policy. Its initial scope is the six first-release Skills plus their required contracts, tests, evaluation cases/runners, development dependencies, CI, and contributor/user documentation; video remains private. Select exact files through review and validate development and installation outputs separately.

Public changes originate in this repository's branch/PR workflow. The core source validates and reports its capabilities without requiring video, Remotion, FFmpeg, or a maintainer's private catalog. Extensions must identify a compatible core dependency and preserve existing consumer workflows without duplicating editable core source.

Review historical documents individually for necessary attribution, architectural context, and concise acceptance evidence. Exclude session handoffs, personal-machine deployment receipts, raw evaluation logs, and private project background. Public summaries retain the scope and limitations of their evidence; all required navigation and execution references must resolve within the distributed source or an accessible external authority. Selection and redaction must preserve necessary third-party notices and leave the original private evidence intact.

### First-release acceptance target (confirmed 2026-09-09)

The six public Skills must support the following Simplified Chinese scope; this target does not assert that all required evidence already exists:

- Supplied-material writing, topic-driven online research and writing, and targeted revision, with traceable sources and explicit uncertainty.
- User-supplied images, sourced image candidates, and screenshots, with acquisition and treatment records; deliver Markdown and local WeChat HTML.
- Basic project configuration, series settings, and knowledge ingest/query. Optional remote draft delivery, image generation, and cloud storage carry separate setup requirements and validation status.

Required harness candidates are Codex, Claude Code, Cursor, GitHub Copilot, Gemini CLI, OpenCode, Windsurf, and Kiro. Select and record one primary local product form and exact version for each; acceptance of one form does not imply acceptance of its IDE, CLI, or cloud siblings. Pi is supplementary rather than a first-release gate.

Core scripts must be verified on macOS and native Windows. Each required harness needs an identified usable path on both systems; a harness-specific WSL path is labeled separately and does not substitute for native Windows core-script checks. The accepted matrix must distinguish installation/discovery, script execution, and actual content production; knowledge of a tool's Skill mechanism alone is not product acceptance.

Community Alpha releases may invite testing before all host/content cases pass, while preserving known failures and labeling unverified routes. Preview releases may declare only verified combinations as supported. Each matrix entry records product form/version, operating system, the three acceptance results, and known limits; unverified entries remain explicitly unverified. The first stable public release requires all mandatory combinations to pass their applicable gates. Both preview and stable publication require the applicable source, provenance, privacy, and workflow checks and separate publication authorization.

### Initial Chinese-language quality coverage (confirmed 2026-09-09)

Use original synthetic material in three initial case families: practical AI-tool use, technology/industry explanation, and business-meeting material synthesis. These cases bound the initial acceptance evidence, not the topics the Skills may handle. Assess usefulness, factual support, and appropriate Chinese expression through the existing contract, editorial, and delivery judgments; the audience and selected Style determine regional and cultural choices. Meeting cases use supplied synthetic records and do not establish that the optional Bitbook integration has passed retrieval acceptance.

### Bilingual user-documentation acceptance (confirmed 2026-09-09)

The paired Chinese/English user guides cover the introduction, step-by-step installation with a copyable Agent prompt, updates/removal, and concise compatibility status. README.md is the single Chinese introduction, paired with README.en.md; both outputs copy them unchanged. The paired installation guides provide a copyable Agent prompt with no user-edited path fields and complete manual commands using the same installer. Agent source resolution uses supplied artifacts or explicit official release links, never guessed repositories or whole-machine searches. Ship the six selected user guides with the installation artifact so their links work locally; engineering documents remain source-only. INSTALL.md owns Agent-specific decisions and recovery rules; internal namespace-migration history stays private. A behavior change affecting these pages must update both languages before merge. The two versions must agree on commands, defaults, support status, and limitations. Other engineering documentation remains English-canonical; historical records retain their original language. Keep source and installation documentation links resolvable in their respective outputs.

### Installation and upgrade acceptance (confirmed 2026-09-09)

- Default installation targets the current project. User-wide installation requires an explicit choice; actual harness visibility must be verified rather than inferred from a directory name.
- Public installations identify a fixed release. Upgrades are user-initiated and describe changes; configuration/data migration provides preview and backup. Test version rollback separately from restoration of migrated project data.
- Verify each harness's native installation route against the same discovery, execution, and production criteria. Public users do not need the maintainer's external catalog or a shared custom installer.

#### Low-friction onboarding acceptance (confirmed 2026-09-09)

These are implementation targets, not claims about the current manual installation route. Use [environment readiness and first creation success](../CONTEXT.md) as distinct outcomes.

- Exercise the declared route on a supported environment with an operational Agent and no preinstalled Python, Node.js, or Git. Necessary runtime preparation must not require terminal expertise; record downloads, prerequisite failures, and any human actions.
- Default checks verify the complete distribution, declared dependency versions, native discovery, and deterministic local HTML conversion from bundled synthetic content. The checks do not call a model or generate an article. Report missing discovery evidence separately; an exit code alone cannot establish readiness.
- Keep check artifacts separate from user articles and return an explicit first-article instruction. Actual creation starts on the user's request; required release-level model/content acceptance remains a separate gate.
- Provide an identified versioned runtime artifact and manual-import instructions. Diagnose unreachable artifact or dependency sources and state remaining blockers; importing files does not establish offline readiness. No first-release domestic-mirror or fully offline-installation guarantee is made.
- The Chinese entry uses the known host and workspace and asks only about ambiguous targets. Install the complete six-Skill suite; guide normal content requests through dasen-content while accurately showing all entries the host discovers. The result reports version, enabled scope, owner, actual storage paths, readiness and the first-article instruction.
- Prepare required runtime dependencies from a release-bound lock using an existing compatible manager/interpreter or user-owned managed installations. Prefer uv and reuse its cache rather than implementing another package cache. Verify bootstrap version/origin/integrity. Use explicit interpreter paths without changing system Python, global PATH or shell profiles. Native Windows onboarding must not require Bash, privileged symlinks or developer mode.

#### Shared runtime and channel acceptance (confirmed 2026-09-09)

The [storage decision](adr/0001-project-selection-with-shared-runtime.md) separates project selection from physical placement. Implementation and observed acceptance are tracked in plan and reviewed evidence; these requirements alone do not establish support.

- Native managers retain ownership of their payloads. The artifact route stores complete versioned payloads in user-owned data storage, preserving the six siblings, dependency metadata and provenance files. Installation reports the actual owner and resolved paths.
- Reuse an environment only when verified release identity, dependency lock, Python identity, OS and architecture match. Completed environments are immutable to normal content/install/update operations. A new version or repair uses a separate generation; keep mutable project state and content outside the environment.
- Verify two projects sharing one healthy environment, one project upgrading while the other stays pinned, concurrent preparation, interrupted preparation/switching and recovery. Activate only after required checks pass. Environment isolation is not a same-user filesystem security boundary.
- Project version intent is portable and separate from machine-specific paths and receipts. Relocation or another computer requires resolved/rebuilt bindings and renewed discovery checks; copied virtual environments or absolute links are not portability evidence.
- Select a native plugin route only after validating payload completeness, requested scope, fixed-version behavior and user-initiated updates. Otherwise use the reviewed artifact route through supported project discovery. Do not install a second channel over an existing manager-owned installation.
- Prioritize Codex desktop and Claude Code on macOS for preview validation. Record their actual product versions and independent acceptance; Codex CLI evidence does not establish desktop support. Continue with native Windows and the remaining mandatory matrix before stable release.
- Default Dasen-owned persistent storage to `~/Library/Application Support/dasen-skills/` on macOS and `%LOCALAPPDATA%\dasen-skills\` on Windows, separate from disposable download caches. Preserve native-manager payload locations and interpreter-manager storage. Artifact releases, runtime generations and machine receipts have distinct owned locations; articles and business settings remain in consumer projects.
- Create each virtual environment at its final generation path and mark it ready after checks. Do not depend on relocating a built virtual environment. A preparation failure preserves the prior working installation; optional-service failures do not block otherwise ready local capabilities.

#### Installation lifecycle acceptance (confirmed 2026-09-09)

- The owner accepts shared visibility of the official project discovery directories. Only explicitly requested entry sets are created; compatible tools may read them. Report shared visibility and inherited same-name entries separately from registered hosts and native discovery.
- One project selects one release across its explicitly connected hosts. Validate every registered entry during an upgrade; report stale bindings or sessions that require refresh without claiming completion. Do not automatically connect additional hosts. A host's inability to meet this contract affects route eligibility, not the project's release selection.
- Repeated installation reuses matching healthy state. Existing unowned entries, modified installed files and manager conflicts are preserved with an actionable difference report; pause only the conflicting replacement. Restoring an official copy or creating a development copy is explicit. The first release does not automatically merge edits to installed Skills.
- An explicit update prepares and checks a new release/runtime before changing the selected project's bindings. Verify recovery from partial multi-host changes and interruptions; retain a usable prior version and give exact pending actions. Other projects remain pinned. Do not mutate another manager's cache to simulate atomic updates.
- Verify source-version rollback independently from restoring migrated project data. Reuse existing working inputs and preserve new user content during recovery.
- Uninstall removes only the selected owned bindings and installation records, preserving articles and business configuration. Keep shared runtime/interpreter installations by default, including when a project or host is deleted outside the installer.
- Explicit cleanup first reports occupied space, owned candidates and uncertain or live references. Remove only positively identified unused owned resources; retain uncertainty and active/pending uses. Do not scan the whole machine for projects or delete another manager's resources. Use the corresponding manager to maintain its caches; a directory named cache may contain an active runtime.
- Cover two hosts using one project, one of two projects upgrading, local installed-file edits, conflicting channels, external project deletion, a missing/unreachable registered consumer and cleanup while another consumer is active. A saved receipt alone is not proof that deletion is safe.

### Compatibility data

Expose one `dasen-*` runtime namespace. Preserve prior technical identifiers only where existing data compatibility requires them; keep actual product names and required attribution intact. Data migration previews changes, preserves backups and delivered artifacts, and is distinct from source-version rollback. Internal deployment inventories and namespace-cutover records stay private.

## 7. Acceptance cases

Deterministic coverage must verify standalone initialization/local HTML without brand or credential reads; project/series resolution and escape refusal; configurable identity/channel/editorial compilation; separate promotion/persona/experience permissions; soft precedence and hard limits; one frozen writing Style and protected private writes; performance evidence/timezone/metric/duplicate checks; separate visual snapshots and valid agent reasons; distinct adapter fingerprints for permitted variations and refusal of protected fields; mixed asset acquisition with original/source/treatment/review receipts; capability-local blockers; safe WeChat credentials/HTML/images/hosts/uncertain retries; independent delivery evidence; and a private-free public tree runnable in an empty directory.

Anything requiring real models/accounts/phone review is explicitly labeled and separately authorized. Offline results do not replace those layers.

## 8. Content acceptance judgments

| Judgment | Evidence |
|---|---|
| Contract compliance (契约合格) | Brief, sources, identity/state constraints, and applicable checks |
| Editorial usefulness (成稿可用) | The article fulfills the reader promise within the evidence, adds information, and follows its selected Style |
| Delivery completeness (交付完整) | Requested prose, mandatory media, target format, files, and applicable platform receipts actually exist |

Record these separately; a composite score cannot cancel missing requirements. Unfulfilled promises, unsupported judgment, and repetitive empty prose need revision. Tone preferences follow the article's Style rather than a global rejection rule. Missing mandatory media permits partial reporting, not complete delivery. Future-tense claims, checker passes, local HTML, draft IDs, and phone review prove only their own actions. The evidence protocol belongs to [maintenance](maintenance.md#model-and-content-evidence).

## 9. Language terminology

These terms distinguish the independent language choices in the [confirmed language policy](intent.md#audience-and-language-policy). They do not introduce runtime fields or additional supported output languages.

| Term | Definition |
|---|---|
| Instruction language | The language of the instructions an Agent reads to carry out a Skill. |
| Interaction language | The language used to discuss a task with its user, including questions and delivery explanations. |
| Content language | The language of the article or other audience-facing work produced for a task. |
| Audience context | The intended readers' regional, cultural, and language conventions; distinct from an author's persona and from a language code alone. |

## 10. Content quality terminology

**Content quality (内容质量)**: The quality of topic selection, the title, and the article considered together. In the external-method adoption work, the term covers this complete editorial outcome rather than article prose alone.

**Method routing (方法路由)**: Selecting and combining content methods according to the reader task and available material. It is distinct from choosing the production stage or the article’s writing Style.

The existing acceptance judgments in [section 8](#8-content-acceptance-judgments) retain their separate meanings. This terminology clarification introduces no runtime fields or scoring weights.

## 11. External-method comparison scope

Agreed on 2026-09-09 for the external-method adoption work:

- Cover two representative Chinese-language content tasks: AI tool selection and practical use, and AI technology or industry explanation. Review whether the former helps readers act and the latter provides a supported new judgment.
- First give the baseline and candidate the same raw source material. Each independently selects the topic, develops the title, and writes the article; the comparison input does not preselect the topic or title.
- Subsequently examine real production in which each process searches for material and discovers topics. Treat retrieval differences as an additional source of variation when interpreting results.
- Apply the [editorial judgment policy](intent.md#editorial-method-adoption) to concrete outputs, explaining topic value, title appeal and promise, and the article’s judgment and fulfillment of that promise.
- Cap the first round at four articles: one baseline and one candidate for each of the two task families. Produce and examine the baselines to identify a concrete issue before testing one candidate method. Present the pairs without baseline/candidate labels, with source evidence; the owner may prefer either version, judge them tied, or reject both, stating the main reason.

The owner confirmed the combined implementation scope and evidence rule on 2026-09-09: benefit in one family supports only conditional use in that situation; benefit in both requires a repeat on new material before broader use. Ties or regressions do not justify added runtime burden. Contradictory results permit at most one further bounded comparison round; unresolved ambiguity means no adoption. Define the scope and workload of any repeat before starting it. Select the candidate from an observed baseline issue and record the expected improvement before generating candidate outputs.

Conditional method selection follows [section 12](#12-conditional-method-routing). These comparisons supplement the existing production-evaluation protocol; a small pilot does not establish stability.

## 12. Conditional method routing

Agreed on 2026-09-09:

- Organize the article around its reader question and select methods for the specific tasks within it. A mixed task may combine comparison, explanation, and practical guidance where each is useful.
- Base method selection on the current objective and available material. Each adopted method needs explicit trigger conditions, required inputs, unsuitable situations, and a stopping or fallback condition.
- Methods demonstrated useful only in a particular situation may remain publicly available with conditional guidance. Test selection and appropriate skipping alongside the method’s content effects.

This design preserves the existing stage ownership and single content entry. It does not add values to `brief.method`, create another Style, or require a new runtime classification.

## 13. Guided content journeys

Agreed on 2026-09-09; these are target behaviors, not claims of completed runtime validation.

| User intent | Required behavior | Completion boundary |
|---|---|---|
| Start a series | Read available context, converge on the audience, series promise, and first angle. Obtain the owner's direction decision unless already supplied, then create the necessary series artifacts and produce the first local manuscript without asking whether to continue at every stage. | First local manuscript, or an agreed series plan when the user explicitly requested planning only. |
| Continue a series | Resolve the intended series and its current content package from existing artifacts. Resume unfinished work; when the current article is complete and the next item is uniquely established, start that item. If the series or next item is ambiguous, offer a short choice with a recommendation, then continue from the answer. | Advance one article within the requested delivery scope; do not implicitly process the entire queue. |
| Write a standalone article | Use the existing direct-entry path when the objective and material suffice. Ask only for missing user decisions or personal facts that materially affect the result. | The requested local article or revision; project or series setup is optional. |
| Inspect status or progress | Read the relevant project, series, briefs, artifacts, and receipts. Report what is evidenced, what remains blocked or uncertain, and the next useful action. Clarify scope only when needed to distinguish plausible targets. | A grounded summary with no content creation, status updates, or automatic repair of derived summaries. |

Questions must use available answers and explain meaningful choices in user language. Public facts that the agent can inspect or research are not a questionnaire for the owner. Once an answer determines the next action, continue within the agreed scope. Existing source, identity, delivery, and authorization boundaries still apply.

Acceptance must exercise new-series direction-to-manuscript and planning-only paths, unfinished and completed-current continuation, ambiguous series or next items, and status-only requests. Verify actual artifacts and resume behavior across turns, preservation of settled decisions, and zero writes for status inspection. Include text-only versus visual requests to ensure visual choices appear only at the intended stage. These interaction cases are separate from the four-article editorial comparison in section 11.

## 14. Owned paths, Wiki reuse and native themes

Confirmed 2026-09-09. Runtime details are owned by dasen-content/references/content-paths.md and its shared resolver.

- New layout-version-2 bundles freeze host workspace and content root, use evidence/ for auditable text and exports/ for requested derived output. Media remains under frozen assets.root. Initialization preserves existing content roots and defaults new source-workspace content to content/. Explicit control-file CLI arguments remain workspace-relative; frozen paths and configuration libraries are content-root-relative. Refuse escape, conflicting targets and overwrite.
- Layout 1 (including absent layout_version) continues to read its original assets/ evidence and delivery state. The alternate layout's delivery state blocks execution; no implicit migration, second state or historical receipt rewrite. Validate pending/uncertain refusal with both layouts and preserve media URLs/hashes.
- Scope only suite-owned files. Consumer practice repairs current instructions and evidence retention without managing unrelated directories or sweeping historical content. Auditable text may be nested; private/raw platform responses remain outside tracked evidence.
- Plain writing succeeds without fixed platform HTML components, rendering or an Asset Check. Requested local rendering validates platform components and image structure. Real draft delivery remains independently authorized and evidenced.
- Research reads a relevant index-first subset of the bound Wiki without changing pages/raw/log/state. Record hit/partial/miss/absent and adopted source IDs. Preserve original identity, source type, locator and real verification time. Deduplicate declared factual origins and exclude structural inspiration. The checker does not infer undeclared source dependence.
- Knowledge initialization is explicit and supplies the supported five-directory/core-field schema. Consumer additions extend subject scope/optional fields. Missing Wiki permits ordinary research. New ingestion is a separately confirmed batch, while maintenance scans are excluded from content knowledge.
- Keep three native white-background adaptations of the owner-selected MWeb Bear, Lark and Typo rules (superseding the earlier simplified designs). Preserve effective source typography, spacing, container and palette values, with documented static/platform substitutions. Test the same Markdown headings, code, lists, tables and images across themes. Retain external design provenance without copying incompatible licensed CSS or claiming a theme-level popularity ranking.

Acceptance covers source and dedicated workspaces, custom roots, legacy packages, escape/state conflict refusal, optional Wiki initialization/missing fallback, unchanged Wiki reads, source-origin counting and native HTML at mobile widths. Offline tests and local previews do not establish model routing reliability, remote draft success or phone acceptance; record those evidence layers separately.
