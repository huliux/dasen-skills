# Release work

Current goal: prepare a community Alpha with six content Skills and a usable installation artifact. This page tracks unfinished work; [intent](intent.md) and [spec](spec.md) own scope and acceptance.

## Alpha release candidate

- Version: `v0.1.0-alpha.1` (`0.1.0a1` in Python metadata). Destination authorized by the owner: `huliux/dasen-skills`.
- Original-project notices use `dasen and contributors`; contributor rights and external notices remain intact. Supporting ownership records stay private.
- The two reviewed installation research reports are explicitly selected in public-source.yaml. The runtime artifact excludes engineering and research documents.
- Publish only the reviewed source with fresh Git history; archive predecessor history privately. Build both outputs from the public release commit, package the installation ZIP with SHA256SUMS, and verify the downloaded assets and fixed installation links.
- Inspect actual offline CI results. A published Alpha remains experimental under the limitations below; publication does not establish missing platform or content acceptance.

## Community testing and known gaps

Remaining platform and content testing can come through Issues and PRs; it need not delay an explicitly experimental Alpha. Existing failures remain failures until independently corrected and verified.

- Codex desktop native discovery and end-to-end creation remain unverified. Native Windows preparation/binding and other Agent adapters remain unfinished.
- Claude Code can prefer a personal same-name Skill. Complete production attempts timed out; semantic overstatement and unsupported receipt times need focused regression work.
- Clean-user onboarding and the initial Chinese content case families need broader evidence. Tests of optional retrieval, meeting context, images, storage, and remote drafts are separate from the local core.
- Shared-resource cleanup currently inventories and retains files. Deletion needs stronger active-use evidence before implementation.

Implemented boundaries and scoped results are summarized in [local installation evidence](evidence/installation-readiness.md) and [host evidence](evidence/project-bindings.md). Stable support claims retain the mandatory acceptance matrix in spec. Deferred work does not authorize automatic paid runs, account writes, or additional features.

## Content layout and research integration

The confirmed contract is implemented in spec §14: three native white themes, layout-2 evidence paths with legacy state preservation, bounded content roots, and Wiki-first research with original-source counting. See [scoped evidence](evidence/content-layout.md). Broader model editorial acceptance and real mobile/platform delivery remain outside this local change's evidence.

The first simplified theme designs were superseded by the owner-selected Bear/Lark/Typo conversion. Renderer fidelity fixes and local acceptance are recorded in the scoped evidence above; cross-platform pixel equivalence is not claimed.
