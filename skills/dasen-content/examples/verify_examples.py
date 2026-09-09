#!/usr/bin/env python3
"""Reproducible, no-network acceptance checks for dasen content contracts."""
from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import types
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required", file=sys.stderr)
    raise SystemExit(2)

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
from style_profiles import resolve_style  # noqa: E402
from visual_styles import resolve_visual_style  # noqa: E402

SKILLS_ROOT = SKILL.parent
PREFLIGHT = SCRIPTS / "preflight.py"
INIT = SCRIPTS / "init_content.py"
PUBLISH = SKILLS_ROOT / "dasen-wechat/scripts/publish.sh"
NATIVE_PUBLISH = SKILLS_ROOT / "dasen-wechat/scripts/native_publish.py"
PREPARE_WECHAT = SKILLS_ROOT / "dasen-wechat/scripts/prepare_article.py"
CHECKS: list[tuple[str, bool, str]] = []


def note(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")


def dump_frontmatter(meta: dict, body: str = "") -> str:
    return "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n\n" + body


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)


def project_files(root: Path) -> None:
    (root / ".git").mkdir()
    project = {
        "schema_version": 3,
        "project": "example",
        "brand": {"name": "Northstar", "aliases": []},
        "channels": {
            "wechat": {
                "display_name": "Example", "default_author": "Example",
                "required_tags": ["Example"], "image_policy": "platform-upload",
            }
        },
        "authors": {
            "default": "lin",
            "profiles": {"lin": {"name": "Lin", "contacts": ["lin@example.test"]}},
        },
        "writing": {"style_library": None},
        "defaults": {"profile": "practical"},
        "assets": {"root": "assets", "remote": {"provider": "none"}},
        "hard_rules": {},
    }
    series = {"series": "demo", "project": "example", "phase": "validating", "profile": "practical"}
    (root / "project.md").write_text(dump_frontmatter(project, "# Project\n"), encoding="utf-8")
    (root / "series.md").write_text(dump_frontmatter(series, "# Series\n"), encoding="utf-8")


def make_bundle(root: Path, slug: str, brief: dict, sources: list[dict], body: str,
                *, single_source: bool, author: str = "Example") -> Path:
    bundle = root / "writing/2026-09-04" / slug
    (bundle / "assets").mkdir(parents=True)
    binary_dir = root / "assets/2026-09-04" / slug
    binary_dir.mkdir(parents=True)
    (binary_dir / "cover.png").write_bytes(b"not-an-image-but-contained-fixture")
    title = "这项已经确认的变化影响哪些普通职场工作"
    article_meta = {
        "title": title,
        "author": author,
        "digest": "只讲已经确认的事实、影响范围和未知项",
        "cover": f"../../../assets/2026-09-04/{slug}/cover.png",
        "tags": ["Example"],
    }
    if brief["journey"] == "breaking":
        article_meta["checked_at"] = brief["checked_at"]
    (bundle / "brief.yaml").write_text(yaml.safe_dump(brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
    sources_meta = {
        "content_id": brief["id"],
        "checked_at": "2026-09-04T17:00:00+08:00",
        "single_source": single_source,
        "sources": sources,
    }
    (bundle / "sources.md").write_text(dump_frontmatter(sources_meta, "# Sources\n"), encoding="utf-8")
    (bundle / "article.md").write_text(dump_frontmatter(article_meta, f"# {title}\n\n{body}\n"), encoding="utf-8")
    (bundle / "record.md").write_text(dump_frontmatter({"content_id": brief["id"], "status": "brief"}, "# Record\n"), encoding="utf-8")
    return bundle


def base_brief(content_id: str, journey: str, length: str, method: str) -> dict:
    profile = "flash" if journey == "breaking" else "practical"
    body_style = resolve_visual_style(
        role="body", requested=None, project_config={}, series_config={},
        project_root=SKILL,
    )
    cover_style = resolve_visual_style(
        role="cover", requested=None, project_config={}, series_config={},
        project_root=SKILL,
    )
    return {
        "schema_version": 3,
        "configuration": "project",
        "id": content_id,
        "brand": {"name": "Northstar", "aliases": []},
        "journey": journey,
        "length": length,
        "method": method,
        "platform": "wechat",
        "project": "example",
        "project_file": "project.md",
        "series": "demo" if journey == "series" else None,
        "series_file": "series.md" if journey == "series" else None,
        "profile": profile,
        "style_profile": resolve_style(
            requested=profile,
            project_config={},
            series_config={},
            project_root=SKILL,
            journey=journey,
        ),
        "image_policy": "platform-upload",
        "assets": {"root": "assets", "remote": {"provider": "none"}},
        "visual": {
            "selection": {"mode": "default", "reason": None},
            "body": {
                "style_id": body_style["id"], "style": body_style, "render_method": "auto",
            },
            "cover": {
                "style_id": cover_style["id"], "style": cover_style,
                "render_method": "auto", "reference": None,
            },
            "cover_size": None,
            "layout_library": None,
            "generation": {"required": False, "provider": "none"},
        },
        "response_stage": "alert" if journey == "breaking" else None,
        "status": "brief",
        "objective": "验证内容契约",
        "audience": "普通职场人",
        "deliverable": "一篇可核验内容",
        "topic_label": None,
        "checked_at": "2026-09-04T17:00:00+08:00" if journey == "breaking" else None,
        "requirements": {"must_include": [], "required_phrases": [], "avoid": [], "forbidden_phrases": [], "tone": None},
        "word_count": {"min": None, "max": None},
        "source_policy": {"minimum": 1 if journey == "breaking" else 5 if length == "deep" else 2,
                          "primary_required": journey == "breaking", "second_source_preferred": True},
        "pattern_reference": {"url": None, "borrow": [], "avoid_copying": []},
        "product_placement": {"enabled": False, "product_name": "Orbit", "aliases": [], "mode": "soft", "max_ratio": 0.05, "required_facts": []},
        "author_persona": {"enabled": False, "profile_id": "lin", "name": "Lin", "contacts": ["lin@example.test"], "uses": [], "verified_experiences": []},
        "channel": {"display_name": "Example", "default_author": "Example", "required_tags": ["Example"]},
        "blocker": None,
        "resume_from": None,
    }


def source(i: int, kind: str = "official", url: str | None = None) -> dict:
    return {
        "id": f"S{i}", "type": kind, "title": f"Source {i}",
        "url": url or f"https://example.com/source-{i}",
        "checked_at": "2026-09-04T17:00:00+08:00",
        "supports": [f"fact-{i}"], "confidence": "high",
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="dasen-verify-") as tmp:
        root = Path(tmp)
        project_files(root)

        standalone_root = root / "standalone"
        standalone_root.mkdir()
        p = run(
            sys.executable, str(INIT),
            "--id", "2026-09-04-standalone-export", "--journey", "material",
            "--length", "quick", "--method", "original", "--platform", "wechat",
            "--objective", "验证零配置本地排版", "--audience", "普通读者", "--deliverable", "微信 HTML",
            cwd=standalone_root,
        )
        standalone_bundle = standalone_root / "writing/2026-09-04/standalone-export"
        standalone_brief = yaml.safe_load((standalone_bundle / "brief.yaml").read_text(encoding="utf-8")) if standalone_bundle.exists() else {}
        note(
            "zero-config standalone bundle created without content brand",
            p.returncode == 0
            and standalone_brief.get("configuration") == "standalone"
            and (standalone_brief.get("brand") or {}).get("name") is None,
            p.stderr.strip(),
        )
        standalone_sources = {
            "content_id": "2026-09-04-standalone-export",
            "checked_at": "2026-09-04T17:00:00+08:00",
            "single_source": False,
            "sources": [source(1), source(2)],
        }
        (standalone_bundle / "sources.md").write_text(
            dump_frontmatter(standalone_sources, "# Sources\n"), encoding="utf-8"
        )
        standalone_title = "零配置也能生成可复制的微信排版文件"
        standalone_article = {
            "title": standalone_title,
            "author": "",
            "digest": "验证无账号、无项目配置的本地交付路径",
            "cover": "",
            "tags": [],
        }
        (standalone_bundle / "article.md").write_text(
            dump_frontmatter(
                standalone_article,
                "两条已核验来源支撑这篇示例。正文完成后，用户可以保存本地排版文件并人工复制。\n",
            ),
            encoding="utf-8",
        )
        standalone_output = standalone_root / "exports/article-wechat.html"
        before_brief = (standalone_bundle / "brief.yaml").read_bytes()
        before_record = (standalone_bundle / "record.md").read_bytes()
        environment = {
            key: value for key, value in os.environ.items()
            if key not in {"WECHAT_APP_ID", "WECHAT_APP_SECRET"}
        }
        environment["DASEN_PYTHON"] = sys.executable
        p = run(
            "bash", str(PUBLISH), "--dry-run", "--output", str(standalone_output),
            str(standalone_bundle), cwd=standalone_root, env=environment,
        )
        standalone_html = standalone_output.read_text(encoding="utf-8") if standalone_output.is_file() else ""
        note(
            "zero-config standalone exports local WeChat HTML without credentials",
            p.returncode == 0
            and before_brief == (standalone_bundle / "brief.yaml").read_bytes()
            and before_record == (standalone_bundle / "record.md").read_bytes()
            and 'data-dasen-renderer="native-v1"' in standalone_html,
            p.stdout.splitlines()[-1] if p.stdout else p.stderr,
        )

        deep = base_brief("2026-09-04-series-verify", "series", "deep", "original")
        deep_body = "\n\n".join(f"第{i}段记录了实际步骤、来源和结果。" for i in range(1, 280))
        (root / "local-evidence.md").write_text("local evidence", encoding="utf-8")
        deep_sources = [source(i) for i in range(1, 5)]
        local_source = source(5, "first-party")
        local_source.pop("url")
        local_source["path"] = "local-evidence.md"
        deep_sources.append(local_source)
        deep_bundle = make_bundle(root, "series-verify", deep, deep_sources, deep_body, single_source=False)
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(deep_bundle), "--stage", "draft", cwd=root)
        note("series deep + 5 sources", p.returncode == 0, p.stdout.splitlines()[0] if p.stdout else p.stderr)

        heading_root = root / "heading-project"
        heading_root.mkdir()
        (heading_root / ".git").mkdir()
        heading_template = heading_root / "assets/heading.html"
        heading_template.parent.mkdir()
        heading_template.write_text(
            '<section aria-label="{{marker}}"><img src="{{image_url}}" alt="{{image_alt}}" /><h2>{{title}}</h2></section>\n',
            encoding="utf-8",
        )
        heading_project = {
            "schema_version": 3,
            "project": "heading-example",
            "channels": {},
            "hard_rules": {
                "section_heading": {
                    "required": True,
                    "level": 2,
                    "marker": "section-heading",
                    "template": "assets/heading.html",
                    "image_url": "https://example.com/heading.png",
                    "image_alt": "mascot",
                }
            },
        }
        (heading_root / "project.md").write_text(dump_frontmatter(heading_project, "# Project\n"), encoding="utf-8")
        heading_bundle = heading_root / "writing/2026-09-04/heading-example"
        heading_bundle.mkdir(parents=True)
        (heading_bundle / "brief.yaml").write_text(
            "schema_version: 3\nconfiguration: project\nplatform: wechat\nproject: heading-example\nproject_file: project.md\n",
            encoding="utf-8",
        )
        heading_source = "## First <step>\n\n```md\n## Keep in fence\n```\n\n## Second\n"
        (heading_bundle / "article.md").write_text(heading_source, encoding="utf-8")
        heading_output = heading_bundle / "prepared.md"
        p = run(
            sys.executable, str(PREPARE_WECHAT), "--article", str(heading_bundle / "article.md"),
            "--bundle", str(heading_bundle), "--output", str(heading_output), cwd=heading_root,
        )
        prepared = heading_output.read_text(encoding="utf-8") if heading_output.exists() else ""
        note(
            "WeChat project heading template applied safely",
            p.returncode == 0
            and prepared.count('aria-label="section-heading"') == 2
            and "First &lt;step&gt;" in prepared
            and "## Keep in fence" in prepared
            and "## First" not in prepared
            and "## Second" not in prepared,
            p.stdout.strip() or p.stderr.strip(),
        )

        label_project = {
            "schema_version": 3,
            "project": "label-example",
            "brand": {"name": "Northstar", "aliases": []},
            "channels": {
                "wechat": {
                    "display_name": "Example", "default_author": "Example",
                    "required_tags": ["Example"], "image_policy": "platform-upload",
                }
            },
            "authors": {"default": None, "profiles": {}},
            "writing": {"style_library": None},
            "defaults": {"profile": "practical"},
            "assets": {"root": "assets", "remote": {"provider": "none"}},
            "visual": {
                "style_library": None,
                "defaults": {
                    "body_style": "body-whiteboard-clarity",
                    "cover_style": "cover-clean-editorial",
                },
                "rendering": {"body": "auto", "cover": "image-model"},
                "cover_size": [1200, 510],
                "layout_library": "cover-templates",
                "generation": {"required": True, "provider": "example-provider", "model": "example-image-model"},
            },
            "hard_rules": {
                "topic_label_required": True,
                "topic_label_in_title": True,
                "topic_label_in_cover": True,
            },
        }
        (root / "label-project.md").write_text(dump_frontmatter(label_project, "# Label Project\n"), encoding="utf-8")
        (root / "cover-templates").mkdir()
        template_reference = root / "assets/template-reference.png"
        template_reference.parent.mkdir(exist_ok=True)
        template_reference.write_bytes(b"template-reference")
        template_reference_hash = hashlib.sha256(template_reference.read_bytes()).hexdigest()
        template_meta = {
            "id": "t01-example",
            "reference_path": "assets/template-reference.png",
            "reference_url": "https://example.com/template-reference.png",
            "reference_sha256": template_reference_hash,
            "status": "verified",
        }
        (root / "cover-templates/t01-example.md").write_text(
            dump_frontmatter(template_meta, "# t01 example\n"), encoding="utf-8"
        )
        p = run(
            sys.executable, str(INIT), "--id", "2026-09-04-init-missing-label", "--journey", "material",
            "--length", "standard", "--method", "original", "--platform", "wechat",
            "--project-file", "label-project.md", "--objective", "x", "--audience", "y", "--deliverable", "z",
            "--root", "init-label", cwd=root,
        )
        note("init requires project topic label", p.returncode == 2 and "--topic-label" in p.stderr)
        p = run(
            sys.executable, str(INIT), "--id", "2026-09-04-init-with-label", "--journey", "material",
            "--length", "standard", "--method", "original", "--platform", "wechat",
            "--project-file", "label-project.md", "--objective", "x", "--audience", "y", "--deliverable", "z",
            "--topic-label", "确认", "--root", "init-label", cwd=root,
        )
        created_brief = root / "init-label/2026-09-04/init-with-label/brief.yaml"
        created_label = yaml.safe_load(created_brief.read_text(encoding="utf-8")).get("topic_label") if created_brief.exists() else None
        note("init persists topic label", p.returncode == 0 and created_label == "确认")

        labelled = base_brief("2026-09-04-labelled-cover", "material", "standard", "original")
        labelled.update({
            "project": "label-example",
            "project_file": "label-project.md",
            "assets": label_project["assets"],
            "channel": label_project["channels"]["wechat"],
        })
        labelled["visual"].update({
            "cover_size": [1200, 510],
            "layout_library": "cover-templates",
            "generation": {"required": True, "provider": "example-provider", "model": "example-image-model"},
        })
        labelled_body = "\n\n".join(f"确认主题标签对应的真实步骤和结果，第{i}次记录。" for i in range(1, 100))
        labelled_bundle = make_bundle(root, "labelled-cover", labelled, [source(1), source(2)], labelled_body, single_source=False)
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(labelled_bundle), "--stage", "draft", cwd=root)
        note("required topic label blocked", p.returncode == 1 and "topic_label" in p.stdout)
        labelled["topic_label"] = "确认"
        (labelled_bundle / "brief.yaml").write_text(yaml.safe_dump(labelled, allow_unicode=True, sort_keys=False), encoding="utf-8")
        labelled_binary = root / "assets/2026-09-04/labelled-cover"
        source_bytes = b"generated-source"
        final_bytes = (labelled_binary / "cover.png").read_bytes()
        (labelled_binary / "cover-source-example.png").write_bytes(source_bytes)
        (labelled_bundle / "assets/cover-prompt.md").write_text("prompt", encoding="utf-8")
        source_sha = hashlib.sha256(source_bytes).hexdigest()
        final_sha = hashlib.sha256(final_bytes).hexdigest()
        cover_meta = {
            "model": "example-image-model",
            "style_id": labelled["visual"]["cover"]["style_id"],
            "style_revision": labelled["visual"]["cover"]["style"]["revision"],
            "adapter": "image-model", "layout": "t01-example", "topic_label": "确认",
            "title": "这项已经确认的变化影响哪些普通职场工作",
            "source_path": "assets/2026-09-04/labelled-cover/cover-source-example.png",
            "source_width": 1200, "source_height": 510, "source_sha256": source_sha,
            "prompt_path": "assets/cover-prompt.md",
            "final_path": "assets/2026-09-04/labelled-cover/cover.png", "final_sha256": final_sha,
            "width": 1200, "height": 510, "generated_at": "2026-09-04T17:00:00+08:00",
        }
        (labelled_bundle / "assets/cover.yaml").write_text(yaml.safe_dump(cover_meta, allow_unicode=True, sort_keys=False), encoding="utf-8")
        with (labelled_bundle / "record.md").open("a", encoding="utf-8") as fh:
            fh.write(f"\n- source_sha256: {source_sha}\n- final_sha256: {final_sha}\n")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(labelled_bundle), "--stage", "publish", "--skip-remote-check", cwd=root)
        note("topic cover manifest attested", p.returncode == 0, p.stdout.splitlines()[0] if p.stdout else p.stderr)

        record_path = labelled_bundle / "record.md"
        record_original = record_path.read_text(encoding="utf-8")
        record_path.write_text(record_original.replace(source_sha, "missing-source-receipt"), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(labelled_bundle), "--stage", "publish", "--skip-remote-check", cwd=root)
        note("cover record hash receipt required", p.returncode == 1 and "record 缺 source_sha256" in p.stdout)
        record_path.write_text(record_original, encoding="utf-8")

        manifest_path = labelled_bundle / "assets/cover.yaml"
        manifest_original = manifest_path.read_text(encoding="utf-8")
        missing_layout = dict(cover_meta, layout="t99-missing")
        manifest_path.write_text(yaml.safe_dump(missing_layout, allow_unicode=True, sort_keys=False), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(labelled_bundle), "--stage", "publish", "--skip-remote-check", cwd=root)
        note("cover layout existence required", p.returncode == 1 and "layout 不存在" in p.stdout)
        ad_hoc = dict(cover_meta, layout="ad-hoc")
        manifest_path.write_text(yaml.safe_dump(ad_hoc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(labelled_bundle), "--stage", "publish", "--skip-remote-check", cwd=root)
        note("ad-hoc layout reason required", p.returncode == 1 and "layout_reason" in p.stdout)
        manifest_path.write_text(manifest_original, encoding="utf-8")

        source_path = labelled_binary / "cover-source-example.png"
        final_path = labelled_binary / "cover.png"
        labelled_brief_path = labelled_bundle / "brief.yaml"
        labelled_brief_original = labelled_brief_path.read_text(encoding="utf-8")
        labelled_article_path = labelled_bundle / "article.md"
        labelled_article_original = labelled_article_path.read_text(encoding="utf-8")
        stable_brief = yaml.safe_load(labelled_brief_original)
        stable_brief["image_policy"] = "stable-cdn"
        labelled_brief_path.write_text(yaml.safe_dump(stable_brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
        stable_url = "https://example.com/labelled-cover.png"
        labelled_article_path.write_text(
            labelled_article_original.replace("../../../assets/2026-09-04/labelled-cover/cover.png", stable_url),
            encoding="utf-8",
        )
        stable_meta = dict(cover_meta, cdn_url=stable_url)
        manifest_path.write_text(yaml.safe_dump(stable_meta, allow_unicode=True, sort_keys=False), encoding="utf-8")
        source_path.unlink()
        final_path.unlink()
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(labelled_bundle), "--stage", "publish", "--skip-remote-check", cwd=root)
        note("stable CDN clone may omit binaries", p.returncode == 0 and "本地生产图片缺失" in p.stdout)
        source_path.write_bytes(source_bytes)
        final_path.write_bytes(final_bytes)
        labelled_brief_path.write_text(labelled_brief_original, encoding="utf-8")
        labelled_article_path.write_text(labelled_article_original, encoding="utf-8")
        manifest_path.write_text(manifest_original, encoding="utf-8")

        breaking = base_brief("2026-09-04-breaking-verify", "breaking", "quick", "pattern-adapt")
        breaking["pattern_reference"]["url"] = "https://example.com/reference"
        breaking_body = (
            "核验时间是 2026-09-04。官方确认功能已经公布，目前能确认开放说明。\n\n"
            "当前为单一事实来源。参考文章只用于信息顺序。\n\n"
            "还不知道完整开放时间。下一步观察官方文档。"
        )
        breaking_sources = [source(1), source(2, "secondary", "https://example.com/reference")]
        breaking_bundle = make_bundle(root, "breaking-verify", breaking, breaking_sources, breaking_body, single_source=True)
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("breaking quick pattern-adapt", p.returncode == 0, p.stdout.splitlines()[0] if p.stdout else p.stderr)

        brief_path = breaking_bundle / "brief.yaml"
        breaking_brief_original = brief_path.read_text(encoding="utf-8")
        invalid_policy = yaml.safe_load(breaking_brief_original)
        invalid_policy["image_policy"] = "platform-uplaod"
        brief_path.write_text(yaml.safe_dump(invalid_policy, allow_unicode=True, sort_keys=False), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("invalid image policy blocked", p.returncode == 1 and "brief.image_policy" in p.stdout)
        brief_path.write_text(breaking_brief_original, encoding="utf-8")

        article = breaking_bundle / "article.md"
        original = article.read_text(encoding="utf-8")
        article.write_text(original + "\n![remote](https://example.com/remote.png)\n", encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("platform-upload remote Markdown image blocked", p.returncode == 1 and "platform-upload" in p.stdout)
        article.write_text(original, encoding="utf-8")
        meta, body = re.match(r"^---\n(.*?)\n---\n?(.*)", original, re.S).groups()
        wrong_author = yaml.safe_load(meta); wrong_author["author"] = "Wrong Author"
        article.write_text(dump_frontmatter(wrong_author, body), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("project default author enforced", p.returncode == 1 and "channel.default_author" in p.stdout)
        article.write_text(original, encoding="utf-8")

        article.write_text(original + "\n使用 Orbit 产品。\n", encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("unauthorized configured product blocked", p.returncode == 1 and "未显式开启产品植入" in p.stdout)
        article.write_text(original, encoding="utf-8")

        # Product at the ending is forbidden even when placement is enabled and fact-anchored.
        brief_path = breaking_bundle / "brief.yaml"
        placement_brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
        placement_brief["product_placement"] = {
            "enabled": True, "product_name": "Orbit", "aliases": [],
            "mode": "soft", "max_ratio": 0.05, "required_facts": ["已核验功能"]
        }
        brief_path.write_text(yaml.safe_dump(placement_brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
        article.write_text(original + "\n\n已核验功能来自 Orbit。\n", encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("configured product ending placement blocked", p.returncode == 1 and "不得作为文章最后一段" in p.stdout)
        placement_brief["product_placement"] = {
            "enabled": False, "product_name": "Orbit", "aliases": [],
            "mode": "soft", "max_ratio": 0.05, "required_facts": []
        }
        brief_path.write_text(yaml.safe_dump(placement_brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
        article.write_text(original, encoding="utf-8")

        article.write_text(original + "\n联系 lin@example.test。\n", encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("unauthorized configured contact blocked", p.returncode == 1 and "author_persona" in p.stdout)
        article.write_text(original + "\n我曾在团队里负责过这项测试。\n", encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("unauthorized first person blocked", p.returncode == 1 and "第一人称" in p.stdout)
        article.write_text(original, encoding="utf-8")

        # Persona enabled for byline does not implicitly authorize contact.
        persona_brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
        persona_brief["author_persona"] = {"enabled": True, "name": "Lin", "contacts": ["lin@example.test"], "uses": ["byline"], "verified_experiences": []}
        brief_path.write_text(yaml.safe_dump(persona_brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
        meta, body = re.match(r"^---\n(.*?)\n---\n?(.*)", original, re.S).groups()
        article_meta = yaml.safe_load(meta); article_meta["author"] = "Example"
        article.write_text(dump_frontmatter(article_meta, body + "\n联系 lin@example.test。\n"), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("persona uses independently enforced", p.returncode == 1 and "uses 未开启 contact" in p.stdout)
        persona_brief["author_persona"] = {
            "enabled": True,
            "name": "Lin",
            "contacts": ["lin@example.test"],
            "uses": ["first-person"],
            "verified_experiences": ["我曾负责另一项工作"],
        }
        brief_path.write_text(yaml.safe_dump(persona_brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
        article.write_text(original + "\n我曾在团队里负责过这项测试。\n", encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("first-person experience must be verified", p.returncode == 1 and "verified_experiences" in p.stdout)
        persona_brief["author_persona"] = {"enabled": False, "name": "Lin", "contacts": ["lin@example.test"], "uses": [], "verified_experiences": []}
        brief_path.write_text(yaml.safe_dump(persona_brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
        article.write_text(original, encoding="utf-8")
        saved = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
        saved["source_policy"]["minimum"] = 0
        brief_path.write_text(yaml.safe_dump(saved, allow_unicode=True, sort_keys=False), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("source minimum can be configured", p.returncode == 0, p.stdout.strip())
        saved["source_policy"]["minimum"] = 1
        saved["requirements"]["required_phrases"] = ["必须逐字出现"]
        brief_path.write_text(yaml.safe_dump(saved, allow_unicode=True, sort_keys=False), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("required phrase enforced", p.returncode == 1 and "required_phrase" in p.stdout)
        saved["requirements"]["required_phrases"] = []
        brief_path.write_text(yaml.safe_dump(saved, allow_unicode=True, sort_keys=False), encoding="utf-8")

        sources_path = breaking_bundle / "sources.md"
        sources_text = sources_path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n?(.*)", sources_text, re.S)
        source_meta = yaml.safe_load(match.group(1)); source_meta["single_source"] = False
        sources_path.write_text(dump_frontmatter(source_meta, match.group(2)), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("single-source declaration enforced", p.returncode == 1 and "single_source" in p.stdout)
        source_meta["single_source"] = True
        source_meta["sources"][0]["supports"] = []
        sources_path.write_text(dump_frontmatter(source_meta, match.group(2)), encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("source evidence fields enforced", p.returncode == 1 and "缺 supports" in p.stdout)
        source_meta["sources"][0]["supports"] = ["fact-1"]
        sources_path.write_text(dump_frontmatter(source_meta, match.group(2)), encoding="utf-8")

        # Accept a natural disclosure observed in an independent Chinese production case.
        disclosed = re.sub(r"单一.{0,6}来源|仅.{0,8}来源", "只有一份来源", original)
        article.write_text(disclosed, encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("natural single-source disclosure accepted", p.returncode == 0, p.stdout.strip())
        article.write_text(original, encoding="utf-8")

        # Local traversal must fail even if target exists.
        (breaking_bundle.parent / "outside.png").write_bytes(b"secret")
        article.write_text(original + "\n![x](../outside.png)\n", encoding="utf-8")
        p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
        note("local asset traversal blocked", p.returncode == 1 and "assets.root" in p.stdout)
        article.write_text(original, encoding="utf-8")

        link = root / "assets/2026-09-04/breaking-verify/escape.png"
        try:
            link.symlink_to(breaking_bundle.parent / "outside.png")
            article.write_text(original + "\n![x](../../../assets/2026-09-04/breaking-verify/escape.png)\n", encoding="utf-8")
            p = run(sys.executable, str(PREFLIGHT), "--bundle", str(breaking_bundle), "--stage", "draft", cwd=root)
            note("local asset symlink escape blocked", p.returncode == 1 and "路径逃逸" in p.stdout)
            article.write_text(original, encoding="utf-8")
        except OSError:
            note("local asset symlink escape optional", True, "SKIP: symlink unavailable")

        spec = importlib.util.spec_from_file_location("preflight", PREFLIGHT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        note("SSRF loopback blocked", module.public_url_error("https://127.0.0.1/metadata") is not None)

        # init record must reflect enabled controls.
        p = run(
            sys.executable, str(INIT), "--id", "2026-09-04-init-record", "--journey", "material",
            "--length", "standard", "--method", "revise", "--platform", "wechat",
            "--project-file", "project.md", "--objective", "x", "--audience", "y", "--deliverable", "z",
            "--product-placement", "--product-name", "Orbit", "--product-fact", "verified",
            "--author-persona", "byline,contact", "--root", "init", cwd=root,
        )
        record = root / "init/2026-09-04/init-record/record.md"
        text = record.read_text(encoding="utf-8") if record.exists() else ""
        note("init record reflects opt-ins", p.returncode == 0 and "产品植入：开启" in text and "byline, contact" in text)

        if PUBLISH.is_file() and NATIVE_PUBLISH.is_file():
            # Prove dry-run changes no files.
            before_brief = brief_path.read_bytes()
            before_record = (breaking_bundle / "record.md").read_bytes()
            env = {**os.environ, "DASEN_PYTHON": sys.executable}
            p = run("bash", str(PUBLISH), "--dry-run", str(breaking_bundle), cwd=root, env=env)
            unchanged = before_brief == brief_path.read_bytes() and before_record == (breaking_bundle / "record.md").read_bytes()
            note("WeChat dry-run has no state side effects", p.returncode == 0 and unchanged, p.stdout.splitlines()[-1] if p.stdout else p.stderr)

            local_html = root / "exports/wechat-breaking.html"
            p = run(
                "bash", str(PUBLISH), "--dry-run", "--output", str(local_html),
                str(breaking_bundle), cwd=root, env=env,
            )
            rendered_local = local_html.read_text(encoding="utf-8") if local_html.is_file() else ""
            unchanged = before_brief == brief_path.read_bytes() and before_record == (breaking_bundle / "record.md").read_bytes()
            note(
                "WeChat local export needs no credentials or project mutation",
                p.returncode == 0 and unchanged and 'data-dasen-renderer="native-v1"' in rendered_local,
                p.stdout.splitlines()[-1] if p.stdout else p.stderr,
            )

            # Inject a no-network client into the native publisher. A missing receipt must not become delivered.
            sys.path.insert(0, str(NATIVE_PUBLISH.parent))
            spec = importlib.util.spec_from_file_location("dasen_native_publish", NATIVE_PUBLISH)
            native_publish = importlib.util.module_from_spec(spec)
            assert spec.loader
            spec.loader.exec_module(native_publish)
            native_publish.load_credentials = lambda *_args: types.SimpleNamespace(
                app_id="dummy-app", app_secret="dummy-secret", source="test"
            )

            class NoReceiptClient:
                def __init__(self, *_args):
                    pass

                def publish_article(self, *_args):
                    return ""

            native_publish.WechatClient = NoReceiptClient
            saved = yaml.safe_load(brief_path.read_text(encoding="utf-8")); saved["status"] = "drafted"
            brief_path.write_text(yaml.safe_dump(saved, allow_unicode=True, sort_keys=False), encoding="utf-8")
            try:
                native_publish.main([str(breaking_bundle)])
                no_receipt_blocked = False
            except RuntimeError:
                no_receipt_blocked = True
            status = yaml.safe_load(brief_path.read_text(encoding="utf-8"))["status"]
            note("delivery without Media ID blocked", no_receipt_blocked and status != "delivered")

            class ReceiptClient(NoReceiptClient):
                def publish_article(self, *_args):
                    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ_123456"

            native_publish.WechatClient = ReceiptClient
            native_publish.main([str(breaking_bundle)])
            status = yaml.safe_load(brief_path.read_text(encoding="utf-8"))["status"]
            record_text = (breaking_bundle / "record.md").read_text(encoding="utf-8")
            note("delivery with Media ID attested", status == "delivered" and "ABCDEFGHIJKLMNOPQRSTUVWXYZ_123456" in record_text)
        else:
            note("WeChat delivery checks optional", True, "SKIP: native dasen-wechat unavailable")

    failed = [name for name, ok, _ in CHECKS if not ok]
    print(f"\nSummary: {len(CHECKS)-len(failed)}/{len(CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
