"""可重复构建独立 MFP 和交付包，明确排除生产状态。"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

EXCLUDED = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "data",
    "logs",
    "config",
    ".test-run",
    ".test-work",
}


def write_entry(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    """固定元数据使同一源码的包可重复比对。"""
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 21, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, payload)


def build() -> dict[str, str]:
    """只打包本插件文件，不读取或导出其他仓库差异。"""
    root = Path(__file__).resolve().parents[1]
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    archive_path = dist / f"snowluma_plus-{manifest['version']}.mfp"
    entries = []
    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if (
                not path.is_file()
                or EXCLUDED.intersection(relative.parts)
                or path.suffix in {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log"}
            ):
                continue
            if (
                path.suffix not in {".py", ".md", ".json", ".toml", ".txt"}
                and path.name != "LICENSE"
            ):
                continue
            write_entry(archive, relative.as_posix(), path.read_bytes())
            entries.append(relative.as_posix())
    bundle = dist / f"snowluma_plus-{manifest['version']}-delivery.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        for path in (archive_path, root / "README.md", root / "docs/VALIDATION.md"):
            write_entry(archive, path.name, path.read_bytes())
    report = {
        "mfp": archive_path.name,
        "mfp_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "bundle": bundle.name,
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "entry_count": len(entries),
        "entries": entries,
    }
    (dist / "build_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {key: str(value) for key, value in report.items() if key != "entries"}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
