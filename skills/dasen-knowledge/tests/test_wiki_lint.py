from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "wiki_lint.py"
FIXTURE = ROOT / "tests" / "fixtures" / "valid-clone"
sys.path.insert(0, str(ROOT / "scripts"))
from wiki_lint import lint  # noqa: E402


class WikiLintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        shutil.copytree(FIXTURE / "wiki", Path(self.temp.name) / "wiki")
        self.wiki = Path(self.temp.name) / "wiki"

    def tearDown(self): self.temp.cleanup()

    def codes(self, **kwargs):
        return {d["code"] for d in lint(self.wiki, **kwargs)["diagnostics"]}

    def add_second_source(self):
        first = self.wiki / "pages/sources/source-a.md"
        second = self.wiki / "pages/sources/source-b.md"
        second.write_text(first.read_text().replace("Source A", "Source B").replace("source.md", "source-b.md"))
        index = self.wiki / "index.md"
        index.write_text(index.read_text().replace("- [[source-a]] — fixture source", "- [[source-a]] — fixture source\n- [[source-b]] — second fixture source"))

    def add_synthesis(self, sources, body="Synthesis cites [[source-a]] and [[source-b]]. It compares two sources. It records a bounded conclusion."):
        source_lines = "\n".join(f'  - "{source}"' for source in sources)
        page = self.wiki / "pages/synthesis/synthesis-a.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            "---\n"
            "title: Synthesis A\n"
            "type: synthesis\n"
            "tags: [fixture]\n"
            f"sources:\n{source_lines}\n"
            'related: ["[[topic-a]]"]\n'
            "source_mode: multi\n"
            "confidence: high\n"
            "created: 2026-01-01\n"
            "updated: 2026-01-01\n"
            "---\n# Synthesis A\n\n" + body + "\n"
        )
        index = self.wiki / "index.md"
        index.write_text(index.read_text().replace("## Synthesis（综述）", "## Synthesis（综述）\n- [[synthesis-a]] — fixture synthesis"))

    def test_valid_clone_succeeds_with_raw_absent(self):
        report = lint(self.wiki)
        self.assertTrue(report["ok"])
        self.assertIn("SKIP_RAW_ABSENT", {d["code"] for d in report["diagnostics"]})

    def test_invalid_yaml_and_duplicate_key(self):
        page = self.wiki / "pages/topics/topic-a.md"
        page.write_text(page.read_text().replace("title: Topic A", "title: bad: scalar"))
        self.assertIn("INVALID_YAML", self.codes())
        page.write_text(page.read_text().replace("title: bad: scalar", "title: Topic A\ntitle: Again"))
        self.assertIn("INVALID_YAML", self.codes())

    def test_duplicate_slug_and_ambiguous_link(self):
        original = self.wiki / "pages/topics/topic-a.md"
        duplicate = self.wiki / "pages/entities/topic-a.md"
        duplicate.parent.mkdir(parents=True, exist_ok=True)
        duplicate.write_text(original.read_text().replace("type: topic", "type: entity"))
        codes = self.codes()
        self.assertIn("DUPLICATE_SLUG", codes)
        self.assertIn("AMBIGUOUS_LINK", codes)

    def test_missing_and_broken_link(self):
        page = self.wiki / "pages/topics/topic-a.md"
        page.write_text(page.read_text().replace('sources: ["[[source-a]]"]', "sources: []").replace('related: ["[[source-a]]"]', 'related: ["[[missing]]"]'))
        codes = self.codes()
        self.assertIn("EMPTY_LIST", codes)
        self.assertIn("BROKEN_LINK", codes)

    def test_index_coverage(self):
        index = self.wiki / "index.md"
        index.write_text(index.read_text().replace("- [[topic-a]] — fixture topic\n", ""))
        self.assertIn("INDEX_MISSING_PAGE", self.codes())

    def test_invalid_provenance(self):
        page = self.wiki / "pages/sources/source-a.md"
        page.write_text(page.read_text().replace("raw/articles/source.md", "../secret.md"))
        self.assertIn("INVALID_RAW_LOCATOR", self.codes())

    def test_raw_required_fails_when_absent(self):
        report = lint(self.wiki, require_raw=True)
        self.assertFalse(report["ok"])
        self.assertIn("RAW_REQUIRED", {d["code"] for d in report["diagnostics"]})

    def test_strict_local_vault_with_sealed_raw_passes(self):
        raw = self.wiki / "raw/articles/source.md"
        raw.parent.mkdir(parents=True)
        raw.write_text("line one\nline two\n")
        state = subprocess.run(
            [sys.executable, str(ROOT / "scripts/wiki_state.py"), "bootstrap", "--wiki", str(self.wiki), "--json"],
            text=True, capture_output=True,
        )
        self.assertEqual(0, state.returncode)
        self.assertTrue(lint(self.wiki, require_raw=True)["ok"])

    def test_synthesis_requires_distinct_source_summaries(self):
        self.add_synthesis(["[[source-a]]", "[[source-a]]"], body="Synthesis cites [[source-a]]. It repeats one source. It lacks independent evidence.")
        codes = self.codes()
        self.assertIn("DUPLICATE_PROVENANCE", codes)
        self.assertIn("MULTI_SOURCE_REQUIRED", codes)

    def test_synthesis_rejects_direct_or_uncited_provenance(self):
        self.add_second_source()
        self.add_synthesis(["[[source-a]]", "[[source-b]]", "raw/articles/source.md"], body="Synthesis cites [[source-a]]. It omits the second source. It has mixed provenance.")
        codes = self.codes()
        self.assertIn("SYNTHESIS_DIRECT_PROVENANCE", codes)
        self.assertIn("PROVENANCE_NOT_CITED", codes)

    def test_misplaced_page_and_traversal_link(self):
        nested = self.wiki / "pages/topics/nested/page.md"
        nested.parent.mkdir()
        nested.write_text("# misplaced\n")
        topic = self.wiki / "pages/topics/topic-a.md"
        topic.write_text(topic.read_text().replace('related: ["[[source-a]]"]', 'related: ["[[pages/../../schema]]"]'))
        codes = self.codes()
        self.assertIn("MISPLACED_PAGE", codes)
        self.assertIn("BROKEN_LINK", codes)

    def test_malformed_ipv6_is_content_error(self):
        page = self.wiki / "pages/sources/source-a.md"
        page.write_text(page.read_text().replace("sources: [raw/articles/source.md#L1-L2]", 'sources: ["https://[broken"]\nchecked_at: 2026-01-01'))
        report = lint(self.wiki)
        self.assertFalse(report["ok"])
        self.assertIn("INVALID_SOURCE_URL", {item["code"] for item in report["diagnostics"]})

    def test_source_summary_requires_materialized_raw(self):
        page = self.wiki / "pages/sources/source-a.md"
        page.write_text(page.read_text().replace("sources: [raw/articles/source.md#L1-L2]", 'sources: ["https://example.com/live"]'))
        self.assertIn("SOURCE_SUMMARY_NOT_MATERIALIZED", self.codes())

    def test_direct_url_provenance_requires_checked_at(self):
        page = self.wiki / "pages/topics/topic-a.md"
        page.write_text(page.read_text().replace('sources: ["[[source-a]]"]', 'sources: ["https://example.com/evidence"]'))
        self.assertIn("CHECKED_AT_REQUIRED", self.codes())
        page.write_text(page.read_text().replace("updated: 2026-01-01", "updated: 2026-01-01\nchecked_at: 2026-01-01"))
        self.assertNotIn("CHECKED_AT_REQUIRED", self.codes())

    def test_cli_json_and_exit_behavior(self):
        good = subprocess.run([sys.executable, str(SCRIPT), "--wiki", str(self.wiki), "--json"], text=True, capture_output=True)
        self.assertEqual(0, good.returncode)
        self.assertTrue(json.loads(good.stdout)["ok"])
        page = self.wiki / "pages/topics/topic-a.md"
        page.write_text("---\ntitle: bad: yaml\n---\n")
        bad = subprocess.run([sys.executable, str(SCRIPT), "--wiki", str(self.wiki), "--json"], text=True, capture_output=True)
        self.assertEqual(1, bad.returncode)
        self.assertFalse(json.loads(bad.stdout)["ok"])

    def test_strict_warning_json_is_not_ok(self):
        source = self.wiki / "pages/sources/source-a.md"
        renamed = source.with_name("来源.md")
        source.rename(renamed)
        for path in [self.wiki / "pages/topics/topic-a.md", self.wiki / "index.md"]:
            path.write_text(path.read_text().replace("source-a", "来源"))
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--wiki", str(self.wiki), "--json", "--strict-warnings"],
            text=True,
            capture_output=True,
        )
        report = json.loads(proc.stdout)
        self.assertEqual(1, proc.returncode)
        self.assertFalse(report["ok"])
        self.assertTrue(report["strict_warnings"])


if __name__ == "__main__": unittest.main()
