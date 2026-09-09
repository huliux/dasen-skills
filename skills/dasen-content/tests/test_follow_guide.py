#!/usr/bin/env python3
"""Offline source-gate regressions; no CDN requests or draft delivery."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("content_examples", SKILL / "examples/verify_examples.py")
examples = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(examples)


def component(url: str, width: int = 52, height: int = 78) -> str:
    return (
        f'<section aria-label="关注指引" style="width:{width}px;height:{height}px;">'
        f'<img src="{url}" alt="" style="width:{width}px;height:{height}px;" /></section>\n'
        '<section><span>关注后查看后续内容</span></section>'
    )


class FollowGuideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="bitbook-follow-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        examples.project_files(self.root)
        self.project_path = self.root / "project.md"
        self.project = yaml.safe_load(self.project_path.read_text().split("---", 2)[1])
        self.url = "https://example.com/follow-v2.png"
        self.html = component(self.url)
        self.configure(self.url, self.html)
        brief = examples.base_brief("2026-09-06-follow-test", "material", "quick", "original")
        self.bundle = examples.make_bundle(
            self.root, "follow-test", brief, [examples.source(1), examples.source(2)],
            "记录已核验的操作步骤与结果。", single_source=False,
        )
        self.article = self.bundle / "article.md"
        self.meta = yaml.safe_load(self.article.read_text().split("---", 2)[1])
        self.write_article(self.html)

    def configure(self, url: str, html: str) -> None:
        self.project["hard_rules"].update({
            "body_h1_forbidden": True,
            "follow_guide": {
                "required": True, "url": url,
                # Metadata fixture only: draft checks do not fetch remote bytes.
                "sha256": hashlib.sha256(b"fixture-image").hexdigest(),
                "html_sha256": hashlib.sha256(html.encode()).hexdigest(),
                "marker": "关注指引", "text": "关注后查看后续内容",
            },
        })
        self.project_path.write_text(examples.dump_frontmatter(self.project, "# Project\n"))

    def write_article(self, html: str, *, prefix: str = "", suffix: str = "") -> None:
        body = prefix + html + "\n\n记录已核验的操作步骤与结果。\n" + suffix
        self.article.write_text(examples.dump_frontmatter(self.meta, body))

    def check(self, *errors: str, stage: str = "render") -> str:
        # Every invocation also proves project/brief/record/other fixture files stay untouched.
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = examples.run(
            sys.executable, str(examples.PREFLIGHT), "--bundle", str(self.bundle),
            "--stage", stage, cwd=self.root,
        )
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after, "read-only preflight changed fixture files")
        self.assertEqual(result.returncode, 1 if errors else 0, result.stdout + result.stderr)
        for error in errors:
            self.assertIn(error, result.stdout)
        return result.stdout

    def test_plain_writing_does_not_require_platform_component(self) -> None:
        self.write_article("")
        self.check(stage="draft")

    def test_current_png_passes(self) -> None:
        self.check()

    def test_old_gif_in_article_does_not_override_current_project(self) -> None:
        self.write_article(component("https://example.com/follow-v1.gif", 26, 32))
        self.check("HTML 与 project", "URL 必须恰好出现 1 次")

    def test_explicit_gif_rollback_requires_article_migration(self) -> None:
        gif_url = "https://example.com/follow-v1.gif"
        gif_html = component(gif_url, 26, 32)
        old_record = (self.bundle / "record.md").read_bytes()
        old_brief = (self.bundle / "brief.yaml").read_bytes()
        self.configure(gif_url, gif_html)
        self.check("HTML 与 project", "URL 必须恰好出现 1 次")
        self.write_article(gif_html)
        self.check()  # v1 is valid when explicitly selected; version number is not authority.
        self.assertEqual(old_record, (self.bundle / "record.md").read_bytes())
        self.assertEqual(old_brief, (self.bundle / "brief.yaml").read_bytes())

    def test_html_change_with_same_url_is_blocked(self) -> None:
        self.write_article(self.html.replace("width:52px", "width:26px"))
        self.check("HTML 与 project")

    def test_duplicate_component_is_blocked(self) -> None:
        self.write_article(self.html + "\n" + self.html)
        self.check("必须恰好出现 1 次，实际 2", "URL 必须恰好出现 1 次")

    def test_extra_url_outside_component_is_blocked(self) -> None:
        self.write_article(self.html, suffix=self.url)
        self.check("URL 必须恰好出现 1 次")

    def test_missing_component_is_blocked(self) -> None:
        self.write_article("")
        self.check("必须恰好出现 1 次，实际 0")

    def test_component_after_prose_is_blocked(self) -> None:
        self.write_article(self.html, prefix="这是正文首段。\n\n")
        self.check("必须位于正文最前方")

    def test_background_implementation_cannot_replace_approved_img(self) -> None:
        # The existing hash gate enforces the approved <img>, not a generic CSS validator.
        bad = (
            '<section aria-label="关注指引" '
            f'style="background-image:url({self.url});"></section>\n'
            '<section><span>关注后查看后续内容</span></section>'
        )
        self.write_article(bad)
        self.check("HTML 与 project")

    def test_valid_component_does_not_authorize_first_person(self) -> None:
        self.write_article(self.html, suffix="我曾在团队里负责过这项测试。")
        output = self.check("第一人称", "author_persona")
        self.assertNotIn("HTML 与 project", output)

    def test_valid_component_does_not_allow_body_h1(self) -> None:
        self.write_article(self.html, suffix="# 重复的正文标题\n")
        self.check("禁止正文重复 H1")

    def test_valid_component_does_not_override_byline(self) -> None:
        self.meta["author"] = "Wrong Author"
        self.write_article(self.html)
        self.check("channel.default_author")


if __name__ == "__main__":
    unittest.main(verbosity=2)
