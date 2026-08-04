from __future__ import annotations

import json
import py_compile
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "id": str,
    "name": str,
    "version": str,
    "language": str,
    "entrypoint": str,
    "requires_api_version": int,
    "dependencies": list,
    "capabilities": list,
    "description": str,
    "author": str,
    "homepage": str,
}

SUPPORTED_LANGUAGES = {"csharp", "python", "tcl"}
PLUGIN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest_paths = sorted(root.glob("*/plugin.json"))
    errors: list[str] = []

    if not manifest_paths:
        errors.append("No plugin.json manifests found in add-on directories.")

    seen_ids: dict[str, Path] = {}
    for manifest_path in manifest_paths:
        manifest = load_manifest(manifest_path, errors)
        if manifest is None:
            continue

        plugin_dir = manifest_path.parent
        validate_manifest_shape(manifest_path, manifest, errors)
        validate_manifest_values(manifest_path, plugin_dir, manifest, seen_ids, errors)
        validate_entrypoint(manifest_path, plugin_dir, manifest, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(manifest_paths)} add-on manifest(s).")
    return 0


def load_manifest(manifest_path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        with manifest_path.open("r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
    except json.JSONDecodeError as exc:
        errors.append(f"{manifest_path}: invalid JSON: {exc}")
        return None

    if not isinstance(manifest, dict):
        errors.append(f"{manifest_path}: manifest must be a JSON object.")
        return None

    return manifest


def validate_manifest_shape(
    manifest_path: Path, manifest: dict[str, Any], errors: list[str]
) -> None:
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in manifest:
            errors.append(f"{manifest_path}: missing required field '{field}'.")
            continue

        if not isinstance(manifest[field], expected_type):
            type_name = (
                expected_type.__name__
                if isinstance(expected_type, type)
                else " or ".join(item.__name__ for item in expected_type)
            )
            errors.append(f"{manifest_path}: field '{field}' must be {type_name}.")

    for field in (
        "id",
        "name",
        "version",
        "language",
        "entrypoint",
        "description",
        "author",
        "homepage",
    ):
        value = manifest.get(field)
        if isinstance(value, str) and not value.strip():
            errors.append(f"{manifest_path}: field '{field}' must not be empty.")

    for field in ("dependencies", "capabilities"):
        value = manifest.get(field)
        if isinstance(value, list) and not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            errors.append(
                f"{manifest_path}: field '{field}' must contain only non-empty strings."
            )


def validate_manifest_values(
    manifest_path: Path,
    plugin_dir: Path,
    manifest: dict[str, Any],
    seen_ids: dict[str, Path],
    errors: list[str],
) -> None:
    plugin_id = manifest.get("id")
    if isinstance(plugin_id, str):
        if not PLUGIN_ID_PATTERN.fullmatch(plugin_id):
            errors.append(
                f"{manifest_path}: id '{plugin_id}' must use lowercase letters, numbers, dots, or hyphens."
            )
        if plugin_dir.name != plugin_id:
            errors.append(
                f"{manifest_path}: add-on directory name must match id '{plugin_id}'."
            )
        if plugin_id in seen_ids:
            errors.append(
                f"{manifest_path}: duplicate id '{plugin_id}' also used by {seen_ids[plugin_id]}."
            )
        else:
            seen_ids[plugin_id] = manifest_path

    version = manifest.get("version")
    if isinstance(version, str) and not SEMVER_PATTERN.fullmatch(version):
        errors.append(
            f"{manifest_path}: version '{version}' must be semantic versioning, for example 1.0.0."
        )

    language = manifest.get("language")
    if isinstance(language, str) and language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        errors.append(
            f"{manifest_path}: language '{language}' is not supported; expected one of: {supported}."
        )

    requires_api_version = manifest.get("requires_api_version")
    if isinstance(requires_api_version, int) and requires_api_version < 1:
        errors.append(f"{manifest_path}: requires_api_version must be at least 1.")

    homepage = manifest.get("homepage")
    if isinstance(homepage, str) and not homepage.startswith(("https://", "http://")):
        errors.append(f"{manifest_path}: homepage must be an HTTP or HTTPS URL.")


def validate_entrypoint(
    manifest_path: Path, plugin_dir: Path, manifest: dict[str, Any], errors: list[str]
) -> None:
    language = manifest.get("language")
    entrypoint = manifest.get("entrypoint")
    if not isinstance(language, str) or not isinstance(entrypoint, str):
        return

    entrypoint_path = Path(entrypoint)
    if entrypoint_path.is_absolute() or ".." in entrypoint_path.parts:
        errors.append(
            f"{manifest_path}: entrypoint must be a relative path inside the add-on directory."
        )
        return

    if language == "python":
        source_path = plugin_dir / entrypoint_path
        if source_path.suffix != ".py":
            errors.append(f"{manifest_path}: Python entrypoint must be a .py file.")
        validate_source_file_exists(
            manifest_path, source_path, "Python entrypoint", errors
        )
        validate_python_syntax(source_path, errors)
        return

    if language == "tcl":
        source_path = plugin_dir / entrypoint_path
        if source_path.suffix != ".tcl":
            errors.append(f"{manifest_path}: Tcl entrypoint must be a .tcl file.")
        validate_source_file_exists(
            manifest_path, source_path, "Tcl entrypoint", errors
        )
        return

    if language == "csharp":
        if entrypoint_path.suffix != ".dll":
            errors.append(f"{manifest_path}: C# entrypoint must be a .dll file.")
        validate_csharp_project(manifest_path, plugin_dir, entrypoint_path.stem, errors)


def validate_source_file_exists(
    manifest_path: Path, source_path: Path, label: str, errors: list[str]
) -> None:
    if not source_path.is_file():
        errors.append(f"{manifest_path}: {label} '{source_path.name}' does not exist.")


def validate_python_syntax(source_path: Path, errors: list[str]) -> None:
    if not source_path.is_file():
        return

    try:
        py_compile.compile(str(source_path), doraise=True)
    except py_compile.PyCompileError as exc:
        errors.append(f"{source_path}: Python syntax error: {exc.msg}")


def validate_csharp_project(
    manifest_path: Path, plugin_dir: Path, entrypoint_name: str, errors: list[str]
) -> None:
    project_paths = sorted(plugin_dir.glob("*.csproj"))
    if not project_paths:
        errors.append(f"{manifest_path}: C# add-on must include a .csproj file.")
        return

    matching_projects = [
        project_path
        for project_path in project_paths
        if get_assembly_name(project_path) == entrypoint_name
    ]
    if not matching_projects:
        project_names = ", ".join(project_path.name for project_path in project_paths)
        errors.append(
            f"{manifest_path}: C# entrypoint '{entrypoint_name}.dll' must match a project AssemblyName or csproj name; found {project_names}."
        )


def get_assembly_name(project_path: Path) -> str:
    try:
        project = ET.parse(project_path).getroot()
    except ET.ParseError:
        return project_path.stem

    assembly_name = project.findtext(".//AssemblyName")
    return (
        assembly_name.strip()
        if assembly_name and assembly_name.strip()
        else project_path.stem
    )


if __name__ == "__main__":
    raise SystemExit(main())
