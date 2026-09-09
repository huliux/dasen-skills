from __future__ import annotations

import sys
from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from cover_receipts import finalize_cover_receipt, register_template_reference  # noqa: E402


def project() -> dict:
    return {
        "assets": {"root": "assets"},
        "visual": {"layout_library": "cover-templates"},
    }


def test_register_template_computes_project_reference_receipt(tmp_path: Path) -> None:
    reference = tmp_path / "assets" / "shared" / "reference.jpg"
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b"reference-image")
    template = tmp_path / "cover-templates" / "knowledge-card.md"
    template.parent.mkdir()
    template.write_text("---\nid: knowledge-card\nstatus: draft\n---\n\n# Prompt\n", encoding="utf-8")

    result = register_template_reference(
        project_config=project(), project_root=tmp_path, template_id="knowledge-card",
        reference_path="assets/shared/reference.jpg",
        reference_url="https://cdn.example.test/shared/reference.jpg", confirmed=True,
    )

    metadata = yaml.safe_load(template.read_text(encoding="utf-8").split("---", 2)[1])
    assert metadata["status"] == "verified"
    assert metadata["reference_sha256"] == result["reference_sha256"]
    assert len(metadata["reference_sha256"]) == 64


def test_finalize_cover_fills_hashes_and_appends_idempotent_record(tmp_path: Path) -> None:
    source = tmp_path / "assets" / "post" / "cover-source.png"
    final = tmp_path / "assets" / "post" / "cover.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"source")
    final.write_bytes(b"final")
    bundle = tmp_path / "writing" / "post"
    (bundle / "assets").mkdir(parents=True)
    manifest = bundle / "assets" / "cover.yaml"
    manifest.write_text(
        "source_path: assets/post/cover-source.png\nfinal_path: assets/post/cover.png\n",
        encoding="utf-8",
    )
    (bundle / "record.md").write_text("# Record\n", encoding="utf-8")

    first = finalize_cover_receipt(project(), tmp_path, bundle)
    second = finalize_cover_receipt(project(), tmp_path, bundle)

    saved = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    record = (bundle / "record.md").read_text(encoding="utf-8")
    assert saved["source_sha256"] == first["source_sha256"] == second["source_sha256"]
    assert saved["final_sha256"] == first["final_sha256"] == second["final_sha256"]
    assert record.count("## Cover Asset Receipt") == 1
