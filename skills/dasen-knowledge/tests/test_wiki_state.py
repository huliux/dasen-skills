from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "wiki_state.py"
FIXTURE = ROOT / "tests" / "fixtures" / "valid-clone"


class WikiStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        shutil.copytree(FIXTURE / "wiki", Path(self.temp.name) / "wiki")
        self.wiki = Path(self.temp.name) / "wiki"

    def tearDown(self): self.temp.cleanup()

    def cli(self, *args):
        proc = subprocess.run([sys.executable, str(SCRIPT), *args, "--wiki", str(self.wiki), "--json"], text=True, capture_output=True)
        return proc, json.loads(proc.stdout)

    def add_raw(self, text="immutable source\nsecond line\n"):
        path = self.wiki / "raw/articles/source.md"
        path.parent.mkdir(parents=True)
        path.write_text(text)
        return path

    def test_clone_check_and_bootstrap_do_not_create_state(self):
        for command in ("check", "bootstrap"):
            proc, report = self.cli(command)
            self.assertEqual(0, proc.returncode)
            self.assertEqual("clone-raw-absent", report["mode"])
            self.assertFalse((self.wiki / ".kb").exists())

    def test_bootstrap_mark_check_and_list(self):
        raw = self.add_raw(); before = raw.read_bytes()
        proc, report = self.cli("bootstrap")
        self.assertEqual(0, proc.returncode)
        self.assertEqual(1, report["raw_inputs"])
        state = json.loads((self.wiki / ".kb/state.json").read_text())
        item = state["raw_inputs"]["wiki/raw/articles/source.md"]
        self.assertEqual("compiled", item["status"])
        self.assertEqual(["pages/sources/source-a.md"], item["outputs"])
        proc, report = self.cli("mark", "--path", "raw/articles/source.md", "--status", "compiled", "--page", "pages/sources/source-a.md")
        self.assertEqual(0, proc.returncode)
        proc, report = self.cli("check")
        self.assertEqual(0, proc.returncode)
        proc, report = self.cli("list", "--status", "compiled")
        self.assertEqual(1, len(report["items"]))
        self.assertEqual(before, raw.read_bytes())

    def test_hash_drift_and_cli_exit(self):
        raw = self.add_raw()
        self.assertEqual(0, self.cli("bootstrap")[0].returncode)
        raw.write_text("mutated\n")
        proc, report = self.cli("check")
        self.assertEqual(1, proc.returncode)
        self.assertIn("RAW_HASH_DRIFT", {d["code"] for d in report["diagnostics"]})
        proc, report = self.cli("mark", "--path", "raw/articles/source.md", "--status", "compiled", "--page", "pages/sources/source-a.md")
        self.assertEqual(1, proc.returncode)

    def test_unrecorded_raw_is_detected_then_sealed_without_rehashing_old(self):
        self.add_raw(); self.cli("bootstrap")
        before = json.loads((self.wiki / ".kb/state.json").read_text())["raw_inputs"]["wiki/raw/articles/source.md"]["sha256"]
        (self.wiki / "raw/articles/new.md").write_text("new\n")
        proc, report = self.cli("check")
        self.assertEqual(1, proc.returncode)
        self.assertIn("RAW_UNRECORDED", {d["code"] for d in report["diagnostics"]})
        proc, report = self.cli("seal")
        self.assertEqual(0, proc.returncode)
        self.assertEqual(1, report["added"])
        after = json.loads((self.wiki / ".kb/state.json").read_text())["raw_inputs"]["wiki/raw/articles/source.md"]["sha256"]
        self.assertEqual(before, after)
        self.assertEqual(0, self.cli("check")[0].returncode)

    def test_mark_rejects_unrelated_and_traversal_outputs(self):
        self.add_raw()
        self.assertEqual(0, self.cli("bootstrap")[0].returncode)
        proc, report = self.cli(
            "mark", "--path", "raw/articles/source.md", "--status", "compiled", "--page", "pages/topics/topic-a.md"
        )
        self.assertEqual(1, proc.returncode)
        self.assertIn("OUTPUT_PROVENANCE_MISMATCH", {item["code"] for item in report["diagnostics"]})
        proc, report = self.cli(
            "mark", "--path", "raw/articles/source.md", "--status", "compiled", "--page", "pages/../../wiki/schema.md"
        )
        self.assertEqual(2, proc.returncode)
        self.assertEqual("tool-error", report["mode"])

    def test_check_revalidates_compiled_outputs(self):
        self.add_raw()
        self.assertEqual(0, self.cli("bootstrap")[0].returncode)
        (self.wiki / "pages/sources/source-a.md").unlink()
        proc, report = self.cli("check")
        self.assertEqual(1, proc.returncode)
        self.assertIn("OUTPUT_MISSING", {item["code"] for item in report["diagnostics"]})

    def test_scalar_state_item_is_tool_error(self):
        self.add_raw()
        self.assertEqual(0, self.cli("bootstrap")[0].returncode)
        path = self.wiki / ".kb/state.json"
        state = json.loads(path.read_text())
        state["raw_inputs"]["wiki/raw/articles/source.md"] = 7
        path.write_text(json.dumps(state))
        proc, report = self.cli("check")
        self.assertEqual(2, proc.returncode)
        self.assertEqual("tool-error", report["mode"])

    def test_record_lint_reflect_and_unseen_reject_stale_report(self):
        self.add_raw()
        self.assertEqual(0, self.cli("bootstrap")[0].returncode)
        lint_script = ROOT / "scripts/wiki_lint.py"
        lint_proc = subprocess.run(
            [sys.executable, str(lint_script), "--wiki", str(self.wiki), "--json", "--require-raw"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, lint_proc.returncode)
        report_path = Path(self.temp.name) / "lint.json"
        report_path.write_text(lint_proc.stdout)
        self.assertEqual(0, self.cli("record-lint", "--report", str(report_path))[0].returncode)
        proc, report = self.cli("unseen")
        self.assertEqual(0, proc.returncode)
        self.assertEqual(2, len(report["changed"]))
        self.assertEqual(0, self.cli("record-reflect", "--report", str(report_path))[0].returncode)
        self.assertEqual([], self.cli("unseen")[1]["changed"])
        index = self.wiki / "index.md"
        index_before = index.read_text()
        index.write_text(index_before + "\n")
        proc, report = self.cli("record-lint", "--report", str(report_path))
        self.assertEqual(2, proc.returncode)
        self.assertEqual("tool-error", report["mode"])
        index.write_text(index_before)
        topic = self.wiki / "pages/topics/topic-a.md"
        topic.write_text(topic.read_text() + "\nChanged after reflect.\n")
        self.assertEqual(["pages/topics/topic-a.md"], self.cli("unseen")[1]["changed"])
        proc, report = self.cli("record-reflect", "--report", str(report_path))
        self.assertEqual(2, proc.returncode)
        self.assertEqual("tool-error", report["mode"])


if __name__ == "__main__": unittest.main()
