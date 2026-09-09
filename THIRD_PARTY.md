# External components and research references

No external Skill source is distributed from this repository. `packs.yaml` names two separate classes:

- `external_tools`: software, libraries or platform APIs called by original dasen code.
- `optional_skills`: enhancements whose source, version, license and patches remain with their external source manager.

## Runtime tools and libraries

| Component | Role | Source / license boundary |
|---|---|---|
| uv | macOS runtime bootstrap and managed Python/dependency preparation | [astral-sh/uv](https://github.com/astral-sh/uv) · MIT OR Apache-2.0; downloaded from a pinned official release, not bundled |
| Python | Skill scripts | [python.org](https://www.python.org/) · PSF License |
| PyYAML | YAML contracts and themes | [yaml/pyyaml](https://github.com/yaml/pyyaml) · MIT |
| markdown-it-py | Markdown tokenization | [executablebooks/markdown-it-py](https://github.com/executablebooks/markdown-it-py) · MIT |
| Pygments | Syntax tokenization and inline code colors | [pygments/pygments](https://github.com/pygments/pygments) · BSD-2-Clause |
| packaging | Version and platform requirement checks | [pypa/packaging](https://github.com/pypa/packaging) · Apache-2.0 OR BSD-2-Clause |
| Pillow | Image reading and transformation | [python-pillow/Pillow](https://github.com/python-pillow/Pillow) · MIT-CMU; installed wheels include their dependency notices |
| mdurl | Markdown URL handling | [executablebooks/mdurl](https://github.com/executablebooks/mdurl) · MIT |
| tzdata | Timezone data on Windows | [python/tzdata](https://github.com/python/tzdata) · package and database notices accompany the installed version |
| WeChat Official Account API | image and draft delivery service | [WeChat developer documentation](https://developers.weixin.qq.com/doc/service/api/) · platform terms and account permissions apply |

These components are not copied into this repository. The root MIT license covers dasen source only; users install and use each dependency under its own terms.

Runtime version bounds are maintained in `pyproject.toml`; `requirements.txt` is the generated hash-locked runtime inventory. The dependency set includes transitive and platform-specific packages. Package contents retain their own notices.

## Optional external Skills

Agent Reach and AIHot are optional research enhancements, not bundled Skill code. Bitbook CLI is an optional source of authorized meeting context. Their absence does not block supplied-material writing or local HTML. Project-specific adapters remain in consumer projects.

## Removed Human Writing source receipt

The removed implementation originated from [KKKKhazix/human-writing v1.1.0](https://github.com/KKKKhazix/human-writing/releases/tag/v1.1.0), revision `cd879d22c8588125c1869d0b443f5d8df74b4192`, under MIT with copyright “2026 Human Writing Skill contributors.” Its fork-derived files are absent from the current tree and installation artifact. The current writing stage is independently implemented and has no Human Writing runtime or Skill dependency. Detailed historical comparison records are retained privately; this notice does not relicense predecessor material.

## WeChat renderer research receipt

The native WeChat pipeline was designed from the platform task and official API. During implementation, Wenyan CLI 2.0.11 (`414c921d5bd5280690e9529b5a8cb918af73f3ff`) and Wenyan core 3.0.11 (`12bd55e158779753a8668bc0d3c67a54c1969625`), both Apache-2.0, were inspected to compare the public high-level flow. Wenyan source, its theme files, registry and CSS applier are not distributed or executed here. The maintained implementation boundary and official API links live in `skills/dasen-wechat/references/implementation-research.md`.
