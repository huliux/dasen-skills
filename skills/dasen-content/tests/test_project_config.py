from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
INIT_PROJECT = SCRIPTS / "init_project.py"
INIT_CONTENT = SCRIPTS / "init_content.py"
PREFLIGHT = SCRIPTS / "preflight.py"
sys.path.insert(0, str(SCRIPTS))
from project_config import default_project_config, split_frontmatter  # noqa: E402


def run(script: Path, *args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args], cwd=cwd, env=env,
        capture_output=True, text=True, check=False,
    )


def project_args(*extra: str) -> list[str]:
    return ["--project", "northstar-news", "--platform", "wechat", *extra]


def content_args(*extra: str) -> list[str]:
    return [
        "--id", "2026-09-07-config-test", "--journey", "material",
        "--length", "quick", "--method", "original", "--platform", "wechat",
        "--objective", "验证配置", "--audience", "读者", "--deliverable", "文章",
        *extra,
    ]


def test_optional_project_and_custom_brand_are_compiled(tmp_path: Path) -> None:
    created = run(INIT_PROJECT, *project_args("--brand-name", "Northstar"), cwd=tmp_path)
    assert created.returncode == 0, created.stderr
    repeated = run(INIT_PROJECT, *project_args("--brand-name", "Other"), cwd=tmp_path)
    assert repeated.returncode != 0 and "拒绝覆盖" in repeated.stderr

    result = run(INIT_CONTENT, *content_args(), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert brief["schema_version"] == 3
    assert brief["configuration"] == "project"
    assert brief["project_file"] == "project.md"
    assert brief["brand"] == {"name": "Northstar", "aliases": []}
    assert brief["assets"]["root"] == "assets"
    assert brief["visual"]["body"]["style_id"] == "body-clean-editorial"
    assert brief["visual"]["cover"]["style_id"] == "cover-clean-editorial"
    assert brief["word_count"] == {"min": 1, "max": 1000}
    assert brief["source_policy"]["minimum"] == 2


def test_unset_content_brand_stays_unset(tmp_path: Path) -> None:
    assert run(INIT_PROJECT, *project_args(), cwd=tmp_path).returncode == 0
    project_path = tmp_path / "project.md"
    source = project_path.read_text(encoding="utf-8")
    config = yaml.safe_load(source.split("---", 2)[1])
    assert config["brand"]["name"] is None
    result = run(INIT_CONTENT, *content_args(), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert brief["brand"]["name"] is None


def test_zero_config_creates_standalone_bundle(tmp_path: Path) -> None:
    result = run(INIT_CONTENT, *content_args(), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert brief["configuration"] == "standalone"
    assert brief["project"] is None and brief["project_file"] is None
    assert brief["brand"] == {"name": None, "aliases": []}
    assert brief["image_policy"] == "local"


def test_standalone_preflight_rejects_injected_content_brand(tmp_path: Path) -> None:
    result = run(INIT_CONTENT, *content_args(), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    bundle = tmp_path / "writing/2026-09-07/config-test"
    brief_path = bundle / "brief.yaml"
    brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    brief["brand"] = {"name": "Injected", "aliases": []}
    brief_path.write_text(yaml.safe_dump(brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
    checked = run(PREFLIGHT, "--bundle", str(bundle), cwd=tmp_path)
    assert checked.returncode != 0
    assert "standalone brief 的内容品牌必须保持未设置" in checked.stdout


def test_content_output_root_cannot_escape_project(tmp_path: Path) -> None:
    assert run(INIT_PROJECT, *project_args(), cwd=tmp_path).returncode == 0
    for unsafe_root in ("../outside", str((tmp_path / "absolute").resolve())):
        result = run(INIT_CONTENT, *content_args("--root", unsafe_root), cwd=tmp_path)
        assert result.returncode != 0
    assert not (tmp_path.parent / "outside").exists()
    assert not (tmp_path / "absolute").exists()


def test_series_control_file_cannot_escape_project(tmp_path: Path) -> None:
    assert run(INIT_PROJECT, *project_args(), cwd=tmp_path).returncode == 0
    outside = tmp_path.parent / "outside-series.md"
    outside.write_text("---\nseries: outside\nproject: northstar-news\n---\n", encoding="utf-8")
    result = run(
        INIT_CONTENT,
        *content_args("--series-file", "../outside-series.md"),
        cwd=tmp_path,
    )
    assert result.returncode != 0
    assert "必须位于项目根目录内" in result.stderr
    assert not (tmp_path / "writing").exists()


def test_global_and_absolute_project_references_are_rejected(tmp_path: Path) -> None:
    assert run(INIT_PROJECT, *project_args(), cwd=tmp_path).returncode == 0
    for reference in ("@global", str((tmp_path / "project.md").resolve())):
        result = run(INIT_CONTENT, *content_args("--project-file", reference), cwd=tmp_path)
        assert result.returncode == 2
        assert "相对路径" in result.stderr or "@global" in result.stderr
    assert not (tmp_path / "writing").exists()


def test_project_can_start_without_brand_or_channels_and_platform_ids_are_open(tmp_path: Path) -> None:
    created = run(INIT_PROJECT, "--project", "northstar-news", cwd=tmp_path)
    assert created.returncode == 0, created.stderr
    project = yaml.safe_load((tmp_path / "project.md").read_text().split("---", 2)[1])
    assert project["channels"] == {}
    result = run(INIT_CONTENT, *content_args("--platform", "reddit"), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert brief["platform"] == "reddit"
    assert brief["channel"] == {}
    assert brief["image_policy"] == "local"


def test_multiple_channels_compile_only_the_selected_platform(tmp_path: Path) -> None:
    created = run(
        INIT_PROJECT,
        "--project", "northstar-news", "--platform", "wechat", "--platform", "reddit",
        cwd=tmp_path,
    )
    assert created.returncode == 0, created.stderr
    project = yaml.safe_load((tmp_path / "project.md").read_text().split("---", 2)[1])
    assert set(project["channels"]) == {"wechat", "reddit"}
    assert project["channels"]["wechat"]["image_policy"] == "local"
    assert project["channels"]["reddit"]["image_policy"] == "local"
    result = run(INIT_CONTENT, *content_args("--platform", "reddit"), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert brief["channel"] == project["channels"]["reddit"]
    assert "wechat" not in brief["channel"]


def test_channel_credential_locator_stays_in_project_and_not_brief(tmp_path: Path) -> None:
    created = run(INIT_PROJECT, *project_args("--platform", "wechat"), cwd=tmp_path)
    assert created.returncode == 0, created.stderr
    project_path = tmp_path / "project.md"
    text = project_path.read_text(encoding="utf-8")
    config = yaml.safe_load(text.split("---", 2)[1])
    config["channels"]["wechat"]["credentials"] = {
        "app_id_env": "PROJECT_WECHAT_APP_ID",
        "app_secret_env": "PROJECT_WECHAT_APP_SECRET",
        "keychain_service": "example.wechat",
        "app_id_account": "app-id",
        "app_secret_account": "app-secret",
    }
    project_path.write_text(
        "---\n" + yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
        + "---" + text.split("---", 2)[2],
        encoding="utf-8",
    )

    result = run(INIT_CONTENT, *content_args("--platform", "wechat"), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert "credentials" not in brief["channel"]
    assert "credentials:" in project_path.read_text(encoding="utf-8")


def test_project_template_matches_canonical_default_factory() -> None:
    template = split_frontmatter((SKILL / "templates/project-template.md").read_text(encoding="utf-8"))
    assert template == default_project_config("example-project")


def test_project_rejects_dangling_default_author_profile(tmp_path: Path) -> None:
    assert run(INIT_PROJECT, *project_args(), cwd=tmp_path).returncode == 0
    project_path = tmp_path / "project.md"
    text = project_path.read_text(encoding="utf-8")
    config = yaml.safe_load(text.split("---", 2)[1])
    config["authors"]["default"] = "missing"
    project_path.write_text(
        "---\n" + yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
        + "---" + text.split("---", 2)[2],
        encoding="utf-8",
    )
    result = run(INIT_CONTENT, *content_args(), cwd=tmp_path)
    assert result.returncode != 0
    assert "authors.default" in result.stderr


def test_series_requires_both_project_and_series_control_documents(tmp_path: Path) -> None:
    (tmp_path / "series.md").write_text(
        "---\nseries: example-series\nproject: northstar-news\n---\n", encoding="utf-8"
    )
    without_project = run(
        INIT_CONTENT,
        *content_args(
            "--journey", "series", "--series", "example-series", "--series-file", "series.md"
        ),
        cwd=tmp_path,
    )
    assert without_project.returncode == 2
    assert "project.md" in without_project.stderr
    assert not (tmp_path / "writing").exists()

    assert run(INIT_PROJECT, *project_args(), cwd=tmp_path).returncode == 0
    without_series = run(
        INIT_CONTENT,
        *content_args("--journey", "series", "--series", "example-series"),
        cwd=tmp_path,
    )
    assert without_series.returncode == 2
    assert "series" in without_series.stderr
    assert not (tmp_path / "writing").exists()


def test_generic_product_and_persona_arguments_have_no_fixed_identity(tmp_path: Path) -> None:
    created = run(
        INIT_PROJECT,
        *project_args(
            "--brand-name", "Northstar", "--default-author", "Lin",
            "--persona-id", "lin", "--persona-name", "Lin", "--persona-contact", "lin@example.test",
        ),
        cwd=tmp_path,
    )
    assert created.returncode == 0, created.stderr
    result = run(
        INIT_CONTENT,
        *content_args(
            "--product-placement", "--product-name", "Orbit", "--product-fact", "verified fact",
            "--author-persona", "byline,contact",
        ),
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert brief["product_placement"]["product_name"] == "Orbit"
    assert brief["author_persona"]["name"] == "Lin"
    assert brief["author_persona"]["profile_id"] == "lin"
    assert brief["author_persona"]["contacts"] == ["lin@example.test"]
    article = (tmp_path / "writing/2026-09-07/config-test/article.md").read_text()
    assert "author: Lin" in article


def test_product_placement_never_falls_back_to_content_or_distribution_brand(tmp_path: Path) -> None:
    assert run(INIT_PROJECT, *project_args("--brand-name", "Northstar"), cwd=tmp_path).returncode == 0
    result = run(INIT_CONTENT, *content_args("--product-placement"), cwd=tmp_path)
    assert result.returncode == 2
    assert "--product-name" in result.stderr
    assert not (tmp_path / "writing").exists()


def test_editorial_policy_compiles_project_series_then_cli_override(tmp_path: Path) -> None:
    created = run(INIT_PROJECT, *project_args("--brand-name", "Northstar"), cwd=tmp_path)
    assert created.returncode == 0, created.stderr
    project_path = tmp_path / "project.md"
    project_text = project_path.read_text(encoding="utf-8")
    project_config = yaml.safe_load(project_text.split("---", 2)[1])
    project_config["editorial"]["word_count"]["quick"] = {"min": 10, "max": 900}
    project_config["editorial"]["sources"]["default"] = {"minimum": 3, "primary_required": False}
    project_path.write_text(
        "---\n" + yaml.safe_dump(project_config, allow_unicode=True, sort_keys=False)
        + "---" + project_text.split("---", 2)[2],
        encoding="utf-8",
    )
    (tmp_path / "series.md").write_text(
        """---
series: policy-test
project: northstar-news
editorial:
  word_count:
    quick: {min: 20, max: 800}
  sources:
    default: {minimum: 4, primary_required: true}
  title:
    wechat: {min: 12, max: 30, forbidden_characters: ['?']}
---
""",
        encoding="utf-8",
    )

    result = run(
        INIT_CONTENT,
        *content_args(
            "--series-file", "series.md",
            "--word-min", "30", "--word-max", "700",
            "--source-minimum", "5", "--no-primary-required",
            "--title-min", "10", "--title-max", "32", "--title-forbid", ":",
        ),
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert brief["word_count"] == {"min": 30, "max": 700}
    assert brief["source_policy"]["minimum"] == 5
    assert brief["source_policy"]["primary_required"] is False
    assert brief["title_policy"] == {
        "min": 10,
        "max": 32,
        "forbidden_characters": [":"],
    }


def test_optional_tos_setup_stores_only_secret_locators(tmp_path: Path) -> None:
    created = run(
        INIT_PROJECT,
        *project_args(
            "--remote-provider", "tos",
            "--remote-endpoint", "https://bucket.tos.example.test",
            "--remote-region", "example-region",
            "--remote-bucket", "example-bucket",
            "--remote-public-base-url", "https://assets.example.test",
            "--remote-access-key-env", "EXAMPLE_TOS_ACCESS",
            "--remote-secret-key-env", "EXAMPLE_TOS_SECRET",
        ),
        cwd=tmp_path,
    )
    assert created.returncode == 0, created.stderr
    config = yaml.safe_load((tmp_path / "project.md").read_text().split("---", 2)[1])
    remote = config["assets"]["remote"]
    assert remote["provider"] == "tos"
    assert remote["access_key_env"] == "EXAMPLE_TOS_ACCESS"
    assert remote["secret_key_env"] == "EXAMPLE_TOS_SECRET"
    assert "access_key" not in remote and "secret_key" not in remote


def test_optional_tos_setup_rejects_incomplete_metadata(tmp_path: Path) -> None:
    result = run(
        INIT_PROJECT,
        *project_args("--remote-provider", "tos", "--remote-region", "example-region"),
        cwd=tmp_path,
    )
    assert result.returncode != 0
    assert not (tmp_path / "project.md").exists()


def test_remote_provider_id_is_not_tos_specific(tmp_path: Path) -> None:
    result = run(
        INIT_PROJECT,
        *project_args(
            "--remote-provider", "oss",
            "--remote-endpoint", "https://oss.example.test",
            "--remote-region", "example-region",
            "--remote-bucket", "example-bucket",
            "--remote-public-base-url", "https://assets.example.test",
            "--remote-access-key-env", "EXAMPLE_OSS_ACCESS",
            "--remote-secret-key-env", "EXAMPLE_OSS_SECRET",
        ),
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    config = yaml.safe_load((tmp_path / "project.md").read_text().split("---", 2)[1])
    assert config["assets"]["remote"]["provider"] == "oss"


def test_visual_provider_configuration_stores_locator_not_secret(tmp_path: Path) -> None:
    created = run(
        INIT_PROJECT,
        *project_args(
            "--visual-provider", "example-image-api",
            "--visual-model", "example-v2",
            "--visual-endpoint", "https://images.example.test/v1",
            "--visual-api-key-env", "EXAMPLE_IMAGE_API_KEY",
        ),
        cwd=tmp_path,
    )
    assert created.returncode == 0, created.stderr
    config = yaml.safe_load((tmp_path / "project.md").read_text().split("---", 2)[1])
    generation = config["visual"]["generation"]
    assert generation["provider"] == "example-image-api"
    assert generation["api_key_env"] == "EXAMPLE_IMAGE_API_KEY"
    assert "api_key" not in generation

    result = run(INIT_CONTENT, *content_args(), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert "api_key_env" not in brief["visual"]["generation"]
    assert "credential_profile" not in brief["visual"]["generation"]


def test_legacy_visual_preset_and_template_are_narrow_compatibility_aliases(tmp_path: Path) -> None:
    created = run(
        INIT_PROJECT,
        *project_args("--visual-preset", "bitbook-editorial", "--template-library", "cover-layouts"),
        cwd=tmp_path,
    )
    assert created.returncode == 0, created.stderr
    project = yaml.safe_load((tmp_path / "project.md").read_text().split("---", 2)[1])
    assert project["visual"]["defaults"] == {
        "body_style": "body-whiteboard-clarity",
        "cover_style": "cover-clean-editorial",
    }
    assert project["visual"]["layout_library"] == "cover-layouts"
    assert "preset" not in project["visual"] and "template_library" not in project["visual"]


def test_existing_schema_v3_visual_aliases_compile_without_becoming_style_identity(tmp_path: Path) -> None:
    config = default_project_config("northstar-news")
    config["visual"] = {
        "preset": "bitbook-editorial",
        "template_library": "cover-layouts",
        "generation": {"required": False, "provider": "none"},
    }
    (tmp_path / "project.md").write_text(
        "---\n" + yaml.safe_dump(config, allow_unicode=True, sort_keys=False) + "---\n",
        encoding="utf-8",
    )
    result = run(INIT_CONTENT, *content_args(), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    brief = yaml.safe_load((tmp_path / "writing/2026-09-07/config-test/brief.yaml").read_text())
    assert brief["visual"]["body"]["style_id"] == "body-whiteboard-clarity"
    assert brief["visual"]["cover"]["style_id"] == "cover-clean-editorial"
    assert brief["visual"]["layout_library"] == "cover-layouts"
    assert brief["visual"]["compatibility"] == {
        "preset": "bitbook-editorial", "template_library": "cover-layouts"
    }
