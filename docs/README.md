# Engineering documentation

Users start with [installation](en/installation.md). Contributors read only the documents relevant to their change.

| Task | Reference |
|---|---|
| Understand product scope and defaults | [Intent](intent.md) |
| Change behavior or acceptance | [Specification](spec.md), then the owning Skill contract |
| Find unfinished work | [Plan](plan.md) |
| Develop, verify, or release | [Maintenance](maintenance.md) |
| Write Agent instructions | [Authoring](authoring.md) |
| Understand domain terms | [Vocabulary](../CONTEXT.md) |
| Operate content stages | [Usage](usage.md) |
| Diagnose a known class of failure | [Lessons](lessons.md) |
| Review installation design or evidence | [Storage ADR](adr/0001-project-selection-with-shared-runtime.md), [local checks](evidence/installation-readiness.md), [host observations](evidence/project-bindings.md) |

The public source includes implementation, tests, contracts, and necessary development guidance. `public-source.yaml` selects its engineering files. The installation artifact includes runtime support, the shared READMEs and six user guides, Agent installation instructions, and notices, as declared in `packs.yaml`. Engineering documents remain source-only. Every exported artifact has a revision-bound manifest.

The reviewed [installation comparison](research/installation-benchmarks.md) and [environment layouts](research/environment-layouts.md) explain installer design choices and are source-only.

Maintainer interviews, namespace-cutover notes, unrevised research archives, deployment records, and raw model logs are not public documentation. Keep them outside this tree; a file removed from the tree can still exist in Git history, which requires its own publication review.
