from __future__ import annotations

import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
INIT_CONTENT = SCRIPTS / "init_content.py"
sys.path.insert(0, str(SCRIPTS))
from visual_styles import (  # noqa: E402
    available_styles,
    load_catalog,
    resolve_visual_style,
    save_project_style,
)


BODY_IDS = {"body-clean-editorial", "body-technical-dark", "body-whiteboard-clarity"}
COVER_IDS = {
    "cover-clean-editorial", "cover-human-editorial",
    "cover-cinematic-system", "cover-knowledge-glow",
}


def dump_catalog(path: Path, styles: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "styles": styles}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def project_style(style_id: str, role: str = "body") -> dict:
    builtin_id = "body-clean-editorial" if role == "body" else "cover-clean-editorial"
    raw = deepcopy(available_styles({}, SKILL)[builtin_id])
    for field in ("id", "origin", "selected_from"):
        raw.pop(field, None)
    raw["label"] = style_id
    raw["source"] = {
        "kind": "project-authored", "samples": [], "conflicts": [], "captured_at": "2026-09-08"
    }
    return raw


def test_builtin_catalog_has_exactly_three_body_and_four_cover_styles(tmp_path: Path) -> None:
    styles = available_styles({}, tmp_path)
    assert {key for key, value in styles.items() if value["role"] == "body"} == BODY_IDS
    assert {key for key, value in styles.items() if value["role"] == "cover"} == COVER_IDS
    assert all(item["source"]["kind"] == "dasen-original" for item in styles.values())


def test_visual_resolution_is_brief_series_project_fallback(tmp_path: Path) -> None:
    dump_catalog(tmp_path / "visual-styles.yaml", {
        "project-body": project_style("project-body"),
        "series-cover": project_style("series-cover", "cover"),
    })
    project = {
        "visual": {
            "style_library": "visual-styles.yaml",
            "defaults": {"body_style": "project-body", "cover_style": "cover-clean-editorial"},
        }
    }
    series = {"visual": {"cover_style": "series-cover"}}
    body = resolve_visual_style(
        role="body", requested=None, project_config=project,
        series_config=series, project_root=tmp_path,
    )
    cover = resolve_visual_style(
        role="cover", requested="cover-knowledge-glow", project_config=project,
        series_config=series, project_root=tmp_path,
    )
    assert body["id"] == "project-body" and body["selected_from"] == "project"
    assert cover["id"] == "cover-knowledge-glow" and cover["selected_from"] == "brief"


def test_project_visual_style_cannot_override_builtin_or_escape(tmp_path: Path) -> None:
    dump_catalog(tmp_path / "collision.yaml", {"body-clean-editorial": project_style("collision")})
    with pytest.raises(ValueError, match="不得覆盖"):
        available_styles({"visual": {"style_library": "collision.yaml"}}, tmp_path)
    with pytest.raises(ValueError, match="相对路径"):
        available_styles({"visual": {"style_library": "../outside.yaml"}}, tmp_path)


def test_sample_derived_project_style_writes_hash_receipts_after_confirmation(tmp_path: Path) -> None:
    for name in ("one.png", "two.png", "three.png"):
        (tmp_path / name).write_bytes(name.encode())
    definition = project_style("private-body")
    definition["id"] = "private-body"
    definition["source"] = {
        "kind": "sample-derived",
        "samples": ["one.png", "two.png", "three.png"],
        "conflicts": ["样本标题密度不同"],
        "captured_at": "2026-09-08",
    }
    project = {"visual": {"style_library": "private/visual-styles.yaml"}}
    with pytest.raises(ValueError, match="用户确认"):
        save_project_style(
            project_config=project, project_root=tmp_path,
            definition=definition, confirmed=False,
        )
    saved = save_project_style(
        project_config=project, project_root=tmp_path,
        definition=definition, confirmed=True,
    )
    assert saved["origin"] == "project:private/visual-styles.yaml"
    assert len(saved["source"]["samples"]) == 3
    assert all(len(item["sha256"]) == 64 for item in saved["source"]["samples"])
    assert all(item["role"] == "body" for item in saved["source"]["samples"])


def test_init_content_freezes_dual_default_visual_snapshots(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, str(INIT_CONTENT),
            "--id", "2026-09-08-visual-defaults", "--journey", "material",
            "--length", "quick", "--method", "original",
            "--objective", "test", "--audience", "reader", "--deliverable", "article",
        ],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-08/visual-defaults/brief.yaml").read_text())
    assert brief["visual"]["selection"] == {"mode": "default", "reason": None}
    assert brief["visual"]["body"]["style_id"] == "body-clean-editorial"
    assert brief["visual"]["cover"]["style_id"] == "cover-clean-editorial"
    assert brief["visual"]["body"]["style"]["selected_from"] == "fallback"
    assert brief["visual"]["cover"]["style"]["selected_from"] == "fallback"


def test_goal_mode_requires_and_records_agent_selection_reason(tmp_path: Path) -> None:
    base = [
        sys.executable, str(INIT_CONTENT),
        "--id", "2026-09-08-agent-visual", "--journey", "material",
        "--length", "quick", "--method", "original",
        "--objective", "explain a system", "--audience", "reader", "--deliverable", "article",
        "--body-style", "body-technical-dark", "--cover-style", "cover-cinematic-system",
        "--visual-selection-mode", "agent",
    ]
    refused = subprocess.run(base, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert refused.returncode == 2
    assert "--visual-selection-reason" in refused.stderr
    created = subprocess.run(
        [*base, "--visual-selection-reason", "系统机制和调用链是文章的核心立意"],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert created.returncode == 0, created.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-08/agent-visual/brief.yaml").read_text())
    assert brief["visual"]["selection"]["mode"] == "agent"
    assert brief["visual"]["selection"]["reason"] == "系统机制和调用链是文章的核心立意"


def test_goal_mode_cannot_label_untouched_fallbacks_as_agent_choices(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, str(INIT_CONTENT),
            "--id", "2026-09-08-agent-fallback", "--journey", "material",
            "--length", "quick", "--method", "original",
            "--objective", "explain a system", "--audience", "reader", "--deliverable", "article",
            "--visual-selection-mode", "agent",
            "--visual-selection-reason", "系统机制和调用链是文章的核心立意",
        ],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "--body-style 与 --cover-style" in result.stderr
    assert not (tmp_path / "writing").exists()


def test_default_mode_cannot_mislabel_explicit_style_choice(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, str(INIT_CONTENT),
            "--id", "2026-09-08-default-explicit", "--journey", "material",
            "--length", "quick", "--method", "original",
            "--objective", "test", "--audience", "reader", "--deliverable", "article",
            "--body-style", "body-technical-dark", "--visual-selection-mode", "default",
        ],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "default 选择模式" in result.stderr
    assert not (tmp_path / "writing").exists()


def test_catalog_rejects_broken_token_reference(tmp_path: Path) -> None:
    broken = project_style("broken")
    broken["components"]["canvas"]["fill"] = "{tokens.colors.missing}"
    dump_catalog(tmp_path / "broken.yaml", {"broken": broken})
    with pytest.raises(ValueError, match="不存在的 token"):
        load_catalog(tmp_path / "broken.yaml", origin="project:broken.yaml")
