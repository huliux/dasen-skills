"""Check the interpreter against every applicable locked runtime requirement."""
from __future__ import annotations

import importlib
from importlib import metadata
from pathlib import Path
import re
import sys

IMPORTS = {
    "packaging": "packaging", "pyyaml": "yaml", "markdown-it-py": "markdown_it",
    "mdurl": "mdurl", "pygments": "pygments", "pillow": "PIL", "tzdata": "tzdata",
}
REQUIRED = {"packaging", "pyyaml", "markdown-it-py", "pygments", "pillow"}


def locked_requirements(path: Path, environment: dict | None = None) -> list:
    from packaging.requirements import Requirement

    text = path.read_text(encoding="utf-8").replace("\\\n", " ")
    requirements = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        declaration, *hashes = line.split("--hash=")
        if not hashes or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", h.strip()) for h in hashes):
            raise ValueError("every runtime requirement must carry SHA-256 hashes")
        requirement = Requirement(declaration.strip())
        pins = list(requirement.specifier)
        if (requirement.url or requirement.extras or len(pins) != 1
                or pins[0].operator != "==" or "*" in pins[0].version):
            raise ValueError(f"runtime requirement must be exactly pinned: {requirement.name}")
        if requirement.marker is None or requirement.marker.evaluate(environment):
            requirements.append(requirement)
    names = {r.name.lower().replace("_", "-") for r in requirements}
    required = REQUIRED | ({"tzdata"} if (environment or {}).get("sys_platform", sys.platform) == "win32" else set())
    if not required <= names or len(names) != len(requirements):
        raise ValueError("runtime lock has missing or duplicate applicable core requirements")
    return requirements


def inspect_dependencies(path: Path) -> dict:
    result = {"status": "blocked", "python": sys.version.split()[0],
              "interpreter": sys.executable, "packages": {}, "errors": []}
    if sys.version_info < (3, 10):
        result["errors"].append("Python 3.10 or newer is required")
        return result
    try:
        requirements = locked_requirements(path)
    except ImportError:
        result["errors"].append("packaging is missing; install the complete hashed requirements.txt")
        return result
    except (OSError, ValueError) as exc:
        result["errors"].append(str(exc))
        return result
    for requirement in requirements:
        name = requirement.name.lower().replace("_", "-")
        item = {"status": "blocked", "required": str(requirement.specifier), "installed": None}
        try:
            installed = metadata.version(requirement.name)
            item["installed"] = installed
            if not requirement.specifier.contains(installed):
                raise ValueError(f"expected {requirement.specifier}, found {installed}")
            if name in IMPORTS:
                importlib.import_module(IMPORTS[name])
            item["status"] = "ready"
        except (metadata.PackageNotFoundError, ImportError, OSError, ValueError, SystemExit) as exc:
            item["error"] = str(exc)
            result["errors"].append(f"{requirement.name}: {exc}")
        result["packages"][requirement.name] = item
    result["status"] = "blocked" if result["errors"] else "ready"
    return result
