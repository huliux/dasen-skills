# Contributing

Chinese or English Issues and PRs are welcome. You can report a problem without writing code. Maintenance is best-effort; there is no fixed response-time commitment.

## Report a problem or test an environment

Include the Dasen release/revision, operating system, Agent product/version, installation method, reproduction steps, expected result, and actual result. For content problems, supply redistributable or synthetic material and identify the unsupported claim or missing output. Redact credentials, private meeting content, personal paths, and account details before sharing logs.

Report installation, native discovery, script execution, and article quality separately. An untested environment is a useful contribution opportunity; a directory or successful process exit alone does not establish working content production.

## Send a change

1. For behavior changes, explain a concrete use case or reproducible failure. Start with the relevant [engineering document](docs/README.md); small wording fixes need no architecture proposal.
2. Branch from `main`, make one focused change, and open a PR. Use Conventional Commits. Preserve existing code style and applicable source notices.
3. Run the applicable [maintenance checks](docs/maintenance.md) and report results and unverified limits. CI runs offline checks; maintainers coordinate any necessary model evaluation.

Engineering text is maintained in English; Chinese content examples remain Chinese. Update paired user guides together when their behavior changes. Maintainers can help with translation. Contributors retain applicable rights; covered contributions use the root [MIT license](LICENSE).
