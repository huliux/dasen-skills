from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

import pytest


SKILL = Path(__file__).resolve().parents[1]
CONTENT_SCRIPTS = SKILL.parent / "dasen-content" / "scripts"
sys.path.insert(0, str(CONTENT_SCRIPTS))
sys.path.insert(0, str(SKILL / "scripts"))
from visual_styles import available_styles  # noqa: E402
from render_adapters import compile_render_plan, resolve_render_plan  # noqa: E402


def brief(style_id: str, *, provider: str = "none", model: str | None = None) -> dict:
    style = deepcopy(available_styles({}, SKILL)[style_id])
    style["selected_from"] = "fallback"
    role = style["role"]
    return {
        "visual": {
            role: {"style_id": style_id, "style": style, "render_method": "auto", "reference": None},
            "generation": {"required": False, "provider": provider, "model": model},
        }
    }


def body_plan(
    data: dict, direction: dict | None, *, adapter: str = "html-css",
    schema_version: int = 3, layout: str = "feedback-loop", shot_id: str = "body-01",
) -> dict:
    style = data["visual"]["body"]["style"]
    shot = {
        "id": shot_id,
        "placement": "核心解释段后",
        "purpose": "解释研究、写作与反馈之间的闭环",
        "acquisition": {"mode": "create"},
        "asset_type": "infographic",
        "layout": layout,
        "render_target": {"width_px": 750, "height_px": 1250, "display_width_px": 375},
        "content_slots": {
            "input": ["文章材料", "读者问题"],
            "steps": ["研究", "写作", "验证"],
            "output": "可核验结论",
        },
        "source_ids": ["S1"],
        "required": True,
    }
    if direction is not None:
        shot["direction"] = direction
    return {
        "schema_version": schema_version,
        "content_id": "example",
        "body": {
            "style_id": style["id"],
            "style_revision": style["revision"],
            "adapter": adapter,
            "shots": [shot],
        },
    }


def cover_plan(data: dict, direction: dict, *, adapter: str = "image-model") -> dict:
    style = data["visual"]["cover"]["style"]
    return {
        "schema_version": 3,
        "content_id": "example",
        "cover": {
            "required": True,
            "style_id": style["id"],
            "style_revision": style["revision"],
            "adapter": adapter,
            "brief": {
                "purpose": "让读者立即理解文章的核心承诺",
                "acquisition": {"mode": "create"},
                "layout": "single-hero",
                "render_target": {"width_px": 2000, "height_px": 850, "display_width_px": 375},
                "content_slots": {"headline": "核心承诺", "support": "读者收益"},
                "direction": direction,
                "text_layers": ["主题标签", "主标题"],
                "reference": None,
            },
        },
    }


def test_html_css_is_zero_configuration_body_adapter() -> None:
    plan = resolve_render_plan(brief("body-clean-editorial"), "body")
    assert plan["status"] == "ready"
    assert plan["adapter"] == "html-css"
    assert "provider" not in plan


def test_image_model_adapter_keeps_provider_out_of_style_identity() -> None:
    data = brief("cover-cinematic-system", provider="example-provider", model="image-v2")
    plan = resolve_render_plan(data, "cover")
    assert plan["adapter"] == "image-model"
    assert plan["provider"] == "example-provider"
    assert plan["style_id"] == "cover-cinematic-system"


def test_optional_unavailable_image_model_becomes_nonblocking_handoff() -> None:
    data = brief("cover-clean-editorial")
    data["visual"]["cover"]["render_method"] = "image-model"
    plan = resolve_render_plan(data, "cover")
    assert plan["status"] == "handoff"
    assert plan["blocking"] is False


def test_human_cover_without_image_capability_uses_manual_handoff() -> None:
    plan = resolve_render_plan(brief("cover-human-editorial"), "cover")
    assert plan["adapter"] == "manual"
    assert plan["status"] == "handoff"
    assert plan["blocking"] is False


def test_same_style_accepts_distinct_asset_directions_without_new_identity() -> None:
    data = brief("body-clean-editorial")
    plan = body_plan(
        data,
        {
            "focus": "output",
            "density": "sparse",
            "include": ["output-panel"],
            "omit": ["metric-strip"],
        },
        layout="flow",
    )
    plan["body"]["shots"].append({
        "id": "body-02",
        "placement": "复盘段后",
        "purpose": "解释反馈如何重新进入研究与写作",
        "asset_type": "infographic",
        "layout": "feedback-loop",
        "render_target": {"width_px": 750, "height_px": 1250, "display_width_px": 375},
        "content_slots": {
            "nodes": ["研究", "写作", "验证", "反馈"],
            "loop": "反馈回到下一轮研究",
        },
        "direction": {
            "focus": "loop",
            "density": "dense",
            "include": ["feedback-loop", "metric-strip"],
            "omit": [],
        },
        "source_ids": ["S1"],
        "required": True,
    })
    sparse = compile_render_plan(
        data,
        plan,
        "body",
        asset_id="body-01",
    )
    dense = compile_render_plan(
        data,
        plan,
        "body",
        asset_id="body-02",
    )
    assert sparse["style_id"] == dense["style_id"] == "body-clean-editorial"
    assert sparse["style_revision"] == dense["style_revision"] == 1
    assert sparse["layout"] == "flow"
    assert dense["layout"] == "feedback-loop"
    assert sparse["content_slots"] != dense["content_slots"]
    assert sparse["prompt"] != dense["prompt"]
    assert sparse["compilation_fingerprint"] != dense["compilation_fingerprint"]
    assert len(sparse["compilation_fingerprint"]) == 64
    assert sparse["enforcement"] == {
        "tokens": "exact", "geometry": "exact", "typography": "native-text-layer",
    }
    assert sparse["target_status"] == "ready"
    assert sparse["derived_constraints"]["min_source_text_px"] == 36


def test_missing_direction_uses_bounded_compatibility_default() -> None:
    data = brief("body-clean-editorial")
    compiled = compile_render_plan(data, body_plan(data, None, schema_version=1), "body")
    assert compiled["direction"] == {
        "focus": "legacy-focus",
        "density": "balanced",
        "include": [],
        "omit": [],
    }
    assert compiled["content_slots"]["legacy-focus"] == "解释研究、写作与反馈之间的闭环"


def test_existing_schema_v3_without_acquisition_keeps_create_compatibility() -> None:
    data = brief("body-clean-editorial")
    plan = body_plan(
        data, {"focus": "steps", "density": "balanced", "include": [], "omit": []}
    )
    plan["body"]["shots"][0].pop("acquisition")
    compiled = compile_render_plan(data, plan, "body")
    assert compiled["acquisition_mode"] == "create"


@pytest.mark.parametrize("mode", ["official", "web", "capture", "user"])
def test_acquired_assets_bypass_render_adapter(mode: str) -> None:
    data = brief("body-clean-editorial")
    plan = body_plan(
        data, {"focus": "steps", "density": "balanced", "include": [], "omit": []}
    )
    plan["body"]["shots"][0]["acquisition"] = {"mode": mode}
    with pytest.raises(ValueError, match="不经过 Render Adapter"):
        compile_render_plan(data, plan, "body")


def test_unknown_acquisition_mode_is_rejected() -> None:
    data = brief("body-clean-editorial")
    plan = body_plan(
        data, {"focus": "steps", "density": "balanced", "include": [], "omit": []}
    )
    plan["body"]["shots"][0]["acquisition"] = {"mode": "stable-cdn"}
    with pytest.raises(ValueError, match="asset.acquisition.mode"):
        compile_render_plan(data, plan, "body")


@pytest.mark.parametrize(
    "direction, message",
    [
        ({"focus": "steps", "density": "balanced", "include": ["feedback-loop"], "omit": ["feedback-loop"]}, "不能重叠"),
        ({"focus": "steps", "density": "balanced", "include": [], "omit": [], "palette": "blue"}, "不允许覆盖字段"),
        ({"focus": "steps", "density": "packed", "include": [], "omit": []}, "density"),
        ({"focus": "steps", "density": False, "include": [], "omit": []}, "density"),
    ],
)
def test_direction_rejects_overlap_style_override_and_unknown_density(direction: dict, message: str) -> None:
    data = brief("body-clean-editorial")
    with pytest.raises(ValueError, match=message):
        compile_render_plan(data, body_plan(data, direction), "body")


@pytest.mark.parametrize(
    "direction, message",
    [
        (
            {
                "focus": "以 ACME Logo 为唯一视觉焦点，采用亮粉色，用 provider-x/model-y 生成",
                "density": "balanced", "include": [], "omit": [],
            },
            "小写 slug",
        ),
        ({"focus": "steps", "density": "balanced", "include": ["brand-logo"], "omit": []}, "不安全模块"),
        ({"focus": "steps", "density": "balanced", "include": [], "omit": ["safe-area"]}, "必备组件"),
        ({"focus": "steps", "density": "balanced", "include": [], "omit": ["brand-mark"]}, "未知模块"),
        ({"focus": "missing-slot", "density": "balanced", "include": [], "omit": []}, "不存在的 content slot"),
    ],
)
def test_direction_rejects_controls_unsafe_modules_and_protected_omissions(direction: dict, message: str) -> None:
    data = brief("body-clean-editorial")
    with pytest.raises(ValueError, match=message):
        compile_render_plan(data, body_plan(data, direction), "body")


def test_schema_v2_requires_direction_and_content_slots() -> None:
    data = brief("body-clean-editorial")
    missing_direction = body_plan(data, None, schema_version=2)
    with pytest.raises(ValueError, match="显式填写 direction"):
        compile_render_plan(data, missing_direction, "body")

    missing_content = body_plan(
        data, {"focus": "steps", "density": "balanced", "include": [], "omit": []},
        schema_version=2,
    )
    missing_content["body"]["shots"][0].pop("content_slots")
    with pytest.raises(ValueError, match="显式填写 content_slots"):
        compile_render_plan(data, missing_content, "body")


@pytest.mark.parametrize("slot", ["provider", "provider-name", "brand-logo", "color-scheme", "safety-mode"])
def test_content_slots_reject_render_control_keys(slot: str) -> None:
    data = brief("body-clean-editorial")
    plan = body_plan(data, {"focus": "steps", "density": "balanced", "include": [], "omit": []})
    plan["body"]["shots"][0]["content_slots"] = {slot: "provider-x", "steps": "合法内容"}
    with pytest.raises(ValueError, match="渲染控制键"):
        compile_render_plan(data, plan, "body")


def test_content_values_may_legitimately_discuss_rules_and_models() -> None:
    data = brief("body-clean-editorial")
    plan = body_plan(data, {"focus": "comparison", "density": "balanced", "include": [], "omit": []})
    plan["body"]["shots"][0]["content_slots"] = {
        "comparison": "比较“禁用规则”和“启用规则”两种配置的结果",
        "subject": "不同模型供应商的能力边界",
    }
    compiled = compile_render_plan(data, plan, "body")
    assert compiled["direction"]["focus"] == "comparison"
    assert "禁用规则" in compiled["prompt"]


def test_image_model_compilation_is_guided_and_keeps_critical_text_for_post_layout() -> None:
    data = brief("cover-cinematic-system", provider="example-provider", model="image-v2")
    compiled = compile_render_plan(
        data,
        cover_plan(data, {
            "focus": "headline",
            "density": "sparse",
            "include": ["signal-path"],
            "omit": ["metric-strip"],
        }),
        "cover",
    )
    assert compiled["status"] == "ready"
    assert compiled["enforcement"] == {
        "tokens": "guided", "geometry": "guided", "typography": "post-layout",
    }
    assert compiled["text_layers"] == ["主题标签", "主标题"]
    assert "直接烘焙进生成像素" in compiled["negative_prompt"]
    assert compiled["derived_constraints"]["safe_inset_px"] == {"x": 120, "y": 51}


def test_provider_selection_does_not_change_compiled_prompt() -> None:
    first = brief("cover-cinematic-system", provider="provider-a", model="model-a")
    second = brief("cover-cinematic-system", provider="provider-b", model="model-b")
    direction = {"focus": "headline", "density": "sparse", "include": [], "omit": []}
    first_compiled = compile_render_plan(first, cover_plan(first, direction), "cover")
    second_compiled = compile_render_plan(second, cover_plan(second, direction), "cover")
    assert first_compiled["provider"] != second_compiled["provider"]
    assert first_compiled["prompt"] == second_compiled["prompt"]
    assert first_compiled["negative_prompt"] == second_compiled["negative_prompt"]
    assert first_compiled["compilation_fingerprint"] == second_compiled["compilation_fingerprint"]


def test_schema_v3_requires_render_target_but_v2_reports_missing_target() -> None:
    data = brief("body-clean-editorial")
    current = body_plan(
        data, {"focus": "steps", "density": "balanced", "include": [], "omit": []}
    )
    current["body"]["shots"][0].pop("render_target")
    with pytest.raises(ValueError, match="render_target"):
        compile_render_plan(data, current, "body")

    current["schema_version"] = 2
    compiled = compile_render_plan(data, current, "body")
    assert compiled["target_status"] == "missing"
    assert compiled["render_target"] is None
    assert "不得声称" in compiled["qa"][-1]


@pytest.mark.parametrize(
    "target, message",
    [
        ({"width_px": 750, "height_px": 1250}, "缺字段"),
        ({"width_px": 750, "height_px": 1250, "display_width_px": 0}, "正整数"),
        ({"width_px": 375, "height_px": 625, "display_width_px": 750}, "不得大于"),
        ({"width_px": True, "height_px": 625, "display_width_px": 375}, "正整数"),
        ({"width_px": 750, "height_px": 1250, "display_width_px": 375, "dpi": 144}, "未知字段"),
    ],
)
def test_render_target_rejects_incomplete_or_ambiguous_scale(target: dict, message: str) -> None:
    data = brief("body-clean-editorial")
    plan = body_plan(
        data, {"focus": "steps", "density": "balanced", "include": [], "omit": []}
    )
    plan["body"]["shots"][0]["render_target"] = target
    with pytest.raises(ValueError, match=message):
        compile_render_plan(data, plan, "body")


def test_compile_rejects_visual_plan_that_drifts_from_frozen_style() -> None:
    data = brief("body-clean-editorial")
    plan = body_plan(data, {"focus": "steps", "density": "balanced", "include": [], "omit": []})
    plan["body"]["style_revision"] = 99
    with pytest.raises(ValueError, match="style_revision"):
        compile_render_plan(data, plan, "body")


def test_compile_rejects_unrecorded_adapter_override() -> None:
    data = brief("body-clean-editorial")
    plan = body_plan(data, {"focus": "steps", "density": "balanced", "include": [], "omit": []})
    with pytest.raises(ValueError, match="不能覆盖"):
        compile_render_plan(data, plan, "body", requested_method="manual")
