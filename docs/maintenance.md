# Maintenance and release

Read intent → spec → plan for requirements/defaults/shared contracts, then change the owning layer. Git, registry, packs, and actual source own implementation facts.

## Change loop

1. Inspect Git state, relevant contracts, and live consumers. State the expected outcome and verification; multistep work needs checkpoints, while a small fix may need one sentence.
2. Preserve unrelated dirty work and rollback evidence. Use an unmounted worktree for risky changes: live links follow uncommitted source and checkout, not a version lock.
3. Edit canonical source under [authoring](authoring.md). Tie each diff to the request or required verification; remove only leftovers introduced by this change. External content remains data.
4. Verify structure/dependencies, then meaningful success/refusal behavior. Reproduce a bug before correcting it. Continue authorized reversible repairs until the stated checks pass or a concrete blocker remains. Account writes, paid APIs, and publication are not default testing.
5. Keep Skill metadata/registry versions synchronized. PATCH is compatible repair, MINOR compatible capability, and MAJOR a breaking invocation/input/output/default contract. Governance-only changes do not inflate runtime versions.
6. Stage only reviewed paths/hunks. Inspect staged diff/name-status/stat/check before committing; do not mix unrelated sessions or use working-tree results as proof for another staged snapshot.
7. Capture demonstrated lessons near the owning reference/test; cross-stage lessons belong in lessons.md. Record condition, correction, evidence, and limits. Runtime snapshots are receipts, not permanent capability claims.

Investigate uncertainty using existing contracts and environment evidence before questioning the owner. Resolve reversible implementation details within authorization, stating material assumptions. Ask when an unresolved decision changes the goal, public contract, permission, or irreversible outcome; continue independent work while waiting. Explain simpler equivalent approaches or ongoing maintenance costs before implementing them.

## Deterministic checks

From a development checkout:

```sh
uv sync --locked
uv run --locked python scripts/export_runtime.py --check
uv run --locked python scripts/validate.py
uv run --locked python -m pytest -q
uv run --locked python skills/dasen-content/examples/verify_examples.py
```

After committing the reviewed candidate, build both outputs to distinct nonexistent paths:

```sh
uv run --locked python scripts/build_public.py --kind source --output <new-source-directory>
uv run --locked python scripts/build_public.py --kind install --output <new-install-directory>
```

The builder requires a clean revision, excludes old Git history, validates the copied six-Skill tree and runs its offline checks before producing a file-hash manifest. `--skip-tests` is diagnostic only and never release acceptance. Review the source allowlist in public-source.yaml; no historical-directory glob is permitted. Public-source validation and runtime-artifact validation are separate. Inspect selected files for provenance/privacy beyond automated heuristics.

Each PR runs offline CI on native macOS/Windows Python. Defined jobs are not evidence until their actual results exist. Shell syntax checks run when Bash is available; the native Python core does not require it. Optional platform/tool integration uses authorized read-only checks or small scoped trials.

Runtime dependency bounds belong to pyproject.toml and resolved versions to uv.lock. After changing them, run `uv lock` and `uv run --locked python scripts/export_runtime.py`. Commit the generated hashed requirements.txt; do not hand-maintain a second dependency list. The public builder verifies that export and checks the final manifest-bearing artifact with `install_check.py --local-only`. Development builds therefore require uv. Local readiness does not establish native discovery or article quality. Changes to `prepare-macos.sh` also require shell syntax checks and a committed complete-artifact preparation trial with isolated data/cache/Python storage. Keep raw machine paths and download/model traces in private build evidence; report clean-process and clean-machine acceptance separately. Bootstrap uv/archive/executable and managed-Python pins require explicit review and repeated preparation checks when updated.

## Model and content evidence

Behavior changes, including patches, need affected model regression. Before actual model sessions, declare cases and run size because they consume quota. No automatic model/paid CI. Release coverage must match the declared support scope and include should-trigger, should-not-trigger, and output/boundary cases.

Use the artifact/conversation runners under `skills/dasen-content/evals/` when appropriate. Read their CLI help. Store complete runs in ignored `eval-results/` or private backups. Freeze source/cases/rubric hashes, Git state, and offline results. Give producers raw requests/material only, without expected answers, scores, or proposed corrections. Use isolated contexts and record the real isolation limits: a separate directory is not a filesystem sandbox.

Keep actual outputs, tool traces, exits, timings, available token counts, material integrity, failures, timeouts, and omitted cases. Never remove unsuccessful cases from the denominator. Independently judge contract compliance, editorial usefulness, and delivery completeness as PASS/PARTIAL/FAIL/NOT_ASSESSED, citing material/output evidence. A missing mandatory asset can justify partial work with a blocker, never complete delivery. A successful process exit cannot substitute for a file.

Preserve initial failures after repairs. Recheck observed corrections against the same case in independent context; version changed cases instead of overwriting old evidence. Hide version labels for editorial comparison. Small samples do not establish general stability, cross-harness support, or gain over a no-Skill baseline. Owner calibration covers a small initial sample/disputed items; pending calibration stays labeled. Only necessary sanitized synthetic evidence enters Git; raw traces and private inputs remain private.

Update both user-guide languages before merging affected behavior. Chinese community drafts are welcome; maintainers prepare final English engineering text without changing meaning or attribution.

## Branches and public cutover

The public repository is the development authority for the six-Skill core. Keep `main` installable, use short task branches and reviewed PRs, and tag accepted repository releases. Build from a clean identified commit. Hotfix from the affected tag and carry the fix into `main`; add long-lived maintenance branches only when multiple supported releases need them. Never commit directly or force-push to `main`.

Review the full intended public Git history as well as the exported file inventory. Removing a document from the current tree does not remove it from existing commits. Keep private archives, raw evaluations, and deployment records outside the public repository; never import their Git objects. Complete rights/notices review before copyright changes or publication, then prepare the exact candidate for the separate publication decision.

For Alpha, publish known limitations and invite community compatibility/content testing. Keep unverified routes explicitly unverified; each PR still runs applicable offline checks. Reserve stable support claims for completed acceptance evidence. Release assets need a fixed version, complete installation artifact, checksum, and working instructions; GitHub's source archive is not the runtime artifact. After both full builds pass, package the installation tree from the same clean release commit:

```sh
uv run --locked python scripts/package_release.py --install <verified-install-directory> --tag v0.1.0-alpha.1 --output <new-release-directory>
```

The tag must match the project version (`0.1.0a1` in Python metadata). The packager verifies the complete manifest and produces a deterministic versioned ZIP plus SHA256SUMS. Upload both to the matching prerelease; verify downloaded bytes before announcing it. Artifact manifests describe build identity, not mutable publication status.

## Recovery and completion

Inspect consumers, new user work, and backups before recovery. Prefer reviewed revert/source-version restoration; restore only affected authorized paths. Never hard-reset/clean a whole live checkout to solve one migration. Source rollback and consumer-data restoration are separate, as explained in [updates](en/updating.md). Verify before resuming. Remove temporary worktrees only after preserving their useful commits/artifacts; keep private evidence until the owner chooses cleanup.

Reports lead with the result, then scope, evidence, affected consumers, and unverified limits. A source/hash check, deterministic conversion, local render, draft ID, phone preview, and publication each prove only their own layer.
