# Local installation evidence

Reviewed 2026-09-09. Evidence is tied to the source revisions below; rerun applicable checks after changes. Raw machine paths and logs remain private.

| Scope | Recorded result |
|---|---|
| Source `f9088aba4349a6fca27e299a1272818bfcbc3642` | 278 offline tests and 35 consumer examples passed; source and installation builds passed |
| Installation lifecycle | 20 cases within the offline suite cover shared runtimes, independent project selection, conflict preservation, recovery, rebinding, and uninstall |
| macOS preparation | A process with empty PATH/cache/managed-Python storage prepared dependencies and sample HTML; this is not clean-machine evidence |
| Artifact checks | Manifest hashes, complete six-Skill payload, locked dependencies, and deterministic local HTML checked; failures block readiness |

Preparation does not enable a host. The project installer records filesystem bindings; native discovery needs separate host evidence. Installation checks make no model call, generate no user article, and read no account credentials. Windows CI is defined but remote execution has not been observed.

The original corrupted-artifact case and runtime correction are summarized in [host evidence](project-bindings.md). Final release acceptance must identify its actual commit and inventory rather than inheriting this older result by implication.
