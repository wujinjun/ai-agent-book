#!/usr/bin/env python3
"""Preflight publication assets, fonts, remote resources, and license metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import tomllib
import zipfile
from collections import Counter
from datetime import date
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree

import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "output/pdf/ai-agent-book-2026.pdf"
DEFAULT_EPUB = ROOT / "output/epub/ai-agent-book-2026.epub"
DEFAULT_PPTX = ROOT / "training/slides/ai-agent-engineering-training.pptx"
DEFAULT_PROVENANCE = ROOT / "notes/asset-provenance.yml"
DEFAULT_REPORT = ROOT / "notes/distribution-asset-audit.json"
PRINT_CSS = ROOT / "templates/pandoc/print.css"
REMOTE_SCHEMES = {"http", "https"}
FONT_FILE_KEYS = {"/FontFile", "/FontFile2", "/FontFile3"}
RESOURCE_ATTRIBUTES = {
    "audio": ("src",),
    "embed": ("src",),
    "iframe": ("src",),
    "img": ("src",),
    "link": ("href",),
    "object": ("data",),
    "script": ("src",),
    "source": ("src", "srcset"),
    "video": ("src", "poster"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def report_path(path: Path) -> str:
    """Return a repository-relative label when possible, otherwise an absolute path."""

    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _object_id(reference: Any, value: Any) -> int:
    return int(getattr(reference, "idnum", 0) or id(value))


def _font_embedded(font: Any) -> bool:
    subtype = str(font.get("/Subtype", ""))
    if subtype == "/Type3":
        return True
    descriptors: list[Any] = []
    if subtype == "/Type0":
        for descendant in font.get("/DescendantFonts", []):
            descriptor = descendant.get_object().get("/FontDescriptor")
            if descriptor is not None:
                descriptors.append(descriptor.get_object())
    else:
        descriptor = font.get("/FontDescriptor")
        if descriptor is not None:
            descriptors.append(descriptor.get_object())
    return any(any(key in descriptor for key in FONT_FILE_KEYS) for descriptor in descriptors)


def _walk_pdf_resources(
    resources: Any,
    *,
    fonts: dict[int, Any],
    images: set[int],
    visited_xobjects: set[int],
) -> None:
    resources = resources.get_object()
    font_dictionary = resources.get("/Font")
    if font_dictionary is not None:
        for reference in font_dictionary.get_object().values():
            font = reference.get_object()
            fonts[_object_id(reference, font)] = font
    xobjects = resources.get("/XObject")
    if xobjects is None:
        return
    for reference in xobjects.get_object().values():
        value = reference.get_object()
        identifier = _object_id(reference, value)
        if identifier in visited_xobjects:
            continue
        visited_xobjects.add(identifier)
        if str(value.get("/Subtype", "")) == "/Image":
            images.add(identifier)
        nested = value.get("/Resources")
        if nested is not None:
            _walk_pdf_resources(
                nested,
                fonts=fonts,
                images=images,
                visited_xobjects=visited_xobjects,
            )


def audit_pdf(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    reader = PdfReader(path)
    fonts: dict[int, Any] = {}
    images: set[int] = set()
    visited_xobjects: set[int] = set()
    sizes: Counter[str] = Counter()
    box_differences = 0
    for page in reader.pages:
        width = round(float(page.mediabox.width), 2)
        height = round(float(page.mediabox.height), 2)
        sizes[f"{width}x{height}"] += 1
        if page.cropbox != page.mediabox:
            box_differences += 1
        _walk_pdf_resources(
            page["/Resources"],
            fonts=fonts,
            images=images,
            visited_xobjects=visited_xobjects,
        )

    font_types: Counter[str] = Counter()
    font_names: Counter[str] = Counter()
    non_embedded: list[str] = []
    for font in fonts.values():
        subtype = str(font.get("/Subtype", "unknown"))
        base_name = str(font.get("/BaseFont", "type3-outline"))
        font_types[subtype] += 1
        font_names[base_name] += 1
        if not _font_embedded(font):
            non_embedded.append(base_name)

    hard_issues: list[str] = []
    if set(sizes) != {"594.96x841.92"}:
        hard_issues.append(f"PDF contains non-A4 media boxes: {dict(sizes)}")
    if non_embedded:
        hard_issues.append(f"PDF contains non-embedded fonts: {sorted(set(non_embedded))}")
    forbidden_system_fonts = sorted(
        name
        for name in font_names
        if re.search(r"Menlo|Monaco|PingFang|Hiragino|HelveticaNeue", name, flags=re.I)
    )
    if forbidden_system_fonts:
        hard_issues.append(
            f"PDF contains unapproved system font resources: {forbidden_system_fonts}"
        )
    manual = [
        (
            "Confirm that bundled SIL-OFL-1.1 font notices satisfy the final storefront, "
            "printer and commercial distribution terms."
        ),
        (
            "Confirm printer trim, binding margin and bleed requirements; the current "
            "text-only PDF uses A4 media/crop boxes without a dedicated bleed workflow."
        ),
    ]
    return (
        {
            "path": report_path(path),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "pages": len(reader.pages),
            "media_boxes": dict(sorted(sizes.items())),
            "cropbox_differs_from_mediabox_pages": box_differences,
            "font_resources": len(fonts),
            "font_types": dict(sorted(font_types.items())),
            "named_font_subsets": dict(sorted(font_names.items())),
            "non_embedded_fonts": sorted(set(non_embedded)),
            "unapproved_system_fonts": forbidden_system_fonts,
            "raster_image_xobjects": len(images),
        },
        hard_issues,
        manual,
    )


def _remote(reference: str) -> bool:
    return urlsplit(reference.strip()).scheme.lower() in REMOTE_SCHEMES


def audit_epub(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    embedded_fonts: list[str] = []
    external_resources: list[str] = []
    external_hyperlinks = 0
    font_families: set[str] = set()
    counts: Counter[str] = Counter()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name in names:
            suffix = Path(name).suffix.lower()
            counts[suffix or "no_suffix"] += 1
            if suffix in {".ttf", ".otf", ".woff", ".woff2"}:
                embedded_fonts.append(name)
            if suffix == ".css":
                css = archive.read(name).decode("utf-8", "replace")
                for family in re.findall(r"font-family\s*:\s*([^;}]+)", css, flags=re.I):
                    font_families.add(" ".join(family.split()))
                for reference in re.findall(r"url\(([^)]+)\)", css, flags=re.I):
                    if _remote(reference.strip("\"' ")):
                        external_resources.append(f"{name}: {reference}")
            if suffix not in {".xhtml", ".html"}:
                continue
            root = ElementTree.fromstring(archive.read(name))
            for element in root.iter():
                local_name = element.tag.rsplit("}", 1)[-1]
                if local_name == "a" and _remote(element.attrib.get("href", "")):
                    external_hyperlinks += 1
                for attribute in RESOURCE_ATTRIBUTES.get(local_name, ()):
                    raw_reference = element.attrib.get(attribute, "").strip()
                    if not raw_reference:
                        continue
                    reference = raw_reference.split()[0]
                    if _remote(reference):
                        external_resources.append(f"{name}: {local_name}.{attribute}={reference}")

    hard_issues = [f"EPUB has external runtime resources: {item}" for item in external_resources]
    manual = [
        (
            "EPUB embeds no font files and relies on reader system fonts; test final "
            "typography on the target storefronts and physical devices."
        ),
    ]
    return (
        {
            "path": report_path(path),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "archive_entries_by_suffix": dict(sorted(counts.items())),
            "embedded_fonts": sorted(embedded_fonts),
            "css_font_families": sorted(font_families),
            "external_runtime_resources": external_resources,
            "external_hyperlinks": external_hyperlinks,
        },
        hard_issues,
        manual,
    )


def audit_pptx(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    typefaces: set[str] = set()
    embedded_fonts: list[str] = []
    external_hyperlinks = 0
    external_resources: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        slide_count = len(
            [name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
        )
        for name in names:
            suffix = Path(name).suffix.lower()
            if suffix in {".ttf", ".otf", ".odttf"} or "embeddedfont" in name.lower():
                embedded_fonts.append(name)
            if suffix == ".xml":
                root = ElementTree.fromstring(archive.read(name))
                for element in root.iter():
                    typeface = next(
                        (
                            value
                            for key, value in element.attrib.items()
                            if key.endswith("typeface")
                        ),
                        "",
                    )
                    if typeface:
                        typefaces.add(typeface)
            if not name.endswith(".rels"):
                continue
            root = ElementTree.fromstring(archive.read(name))
            for relation in root:
                if relation.attrib.get("TargetMode") != "External":
                    continue
                relation_type = relation.attrib.get("Type", "").rsplit("/", 1)[-1]
                target = relation.attrib.get("Target", "")
                if relation_type == "hyperlink":
                    external_hyperlinks += 1
                else:
                    external_resources.append(f"{name}: {relation_type}={target}")

    hard_issues = [f"PPTX has external runtime resources: {item}" for item in external_resources]
    manual = [
        (
            "PPTX embeds no font files; confirm Calibri, Calibri Light and Helvetica Neue "
            "substitution on delivery computers or replace them with approved fonts."
        ),
    ]
    return (
        {
            "path": report_path(path),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "slides": slide_count,
            "typefaces": sorted(typefaces),
            "embedded_fonts": sorted(embedded_fonts),
            "external_runtime_resources": external_resources,
            "external_hyperlinks": external_hyperlinks,
        },
        hard_issues,
        manual,
    )


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a PNG file: {path}")
    return struct.unpack(">II", header[16:24])


def audit_source_assets(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = document.get("assets", [])
    registered = {str(entry["path"]): entry for entry in entries}
    referenced: set[str] = set()
    image_pattern = re.compile(r"!\[[^]]*]\(([^)\s]+)(?:\s+[^)]*)?\)")
    markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for markdown in markdown_files:
        for reference in image_pattern.findall(markdown.read_text(encoding="utf-8")):
            if _remote(reference):
                continue
            resolved = (markdown.parent / reference).resolve()
            try:
                relative = resolved.relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if relative.startswith("assets/diagrams/"):
                continue
            referenced.add(relative)

    required = referenced | {"training/slides/ai-agent-engineering-training.pptx"}
    hard_issues = [
        f"asset has no provenance record: {item}" for item in sorted(required - set(registered))
    ]
    inventory: list[dict[str, Any]] = []
    font_inventory: list[dict[str, Any]] = []
    print_css = PRINT_CSS.read_text(encoding="utf-8")
    for relative in sorted(registered):
        asset_path = ROOT / relative
        if not asset_path.is_file():
            hard_issues.append(f"registered asset is missing: {relative}")
            continue
        computed_sha256 = sha256(asset_path)
        declared_sha256 = registered[relative].get("sha256")
        item: dict[str, Any] = {
            **registered[relative],
            "computed_sha256": computed_sha256,
            "bytes": asset_path.stat().st_size,
        }
        if declared_sha256 is not None and declared_sha256 != computed_sha256:
            hard_issues.append(f"asset checksum mismatch: {relative}")
        if item.get("kind") == "distribution_font":
            license_file = item.get("license_file")
            if not isinstance(license_file, str) or not (ROOT / license_file).is_file():
                hard_issues.append(f"distribution font has no bundled license file: {relative}")
            if relative not in print_css:
                hard_issues.append(f"distribution font is not referenced by print CSS: {relative}")
            font_inventory.append(item)
        if asset_path.suffix.lower() == ".png":
            width, height = _png_dimensions(asset_path)
            item["pixels"] = {"width": width, "height": height}
            if width < 1200:
                hard_issues.append(f"source raster width below 1200px: {relative} ({width}px)")
        inventory.append(item)
    return (
        {
            "registry": path.relative_to(ROOT).as_posix(),
            "referenced_non_diagram_assets": sorted(referenced),
            "assets": inventory,
            "distribution_fonts": font_inventory,
        },
        hard_issues,
        [
            "A professional reviewer must confirm the rights_basis entries against "
            "private source records."
        ],
    )


def audit_dependencies(pyproject: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    document = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = document["project"]
    requirements = list(project.get("dependencies", []))
    for values in project.get("optional-dependencies", {}).values():
        requirements.extend(values)
    names: set[str] = set()
    for requirement in requirements:
        match = re.match(r"[A-Za-z0-9_.-]+", requirement)
        if match is None:
            raise ValueError(f"invalid dependency declaration: {requirement}")
        names.add(match.group(0))
    records: list[dict[str, Any]] = []
    hard_issues: list[str] = []
    manual: list[str] = []
    for name in sorted(names):
        try:
            package = distribution(name)
        except PackageNotFoundError:
            hard_issues.append(
                f"declared dependency is not installed for license inventory: {name}"
            )
            continue
        metadata = package.metadata
        classifiers = [
            value.split("License ::", 1)[1].strip()
            for value in metadata.get_all("Classifier", [])
            if "License ::" in value
        ]
        license_files: list[dict[str, str]] = []
        for file in package.files or []:
            if "license" not in str(file).lower() and "copying" not in str(file).lower():
                continue
            located = Path(str(package.locate_file(file)))
            if located.is_file():
                license_files.append({"path": str(file), "sha256": sha256(located)})
        license_value = metadata.get("License")
        records.append(
            {
                "name": metadata.get("Name", name),
                "version": package.version,
                "license_metadata": license_value,
                "license_classifiers": classifiers,
                "license_files": license_files,
            }
        )
        signal = " ".join([license_value or "", *classifiers]).lower()
        if not signal:
            manual.append(f"Dependency {name} has no concise license signal in package metadata.")
        if "affero" in signal or "agpl" in signal:
            manual.append(
                f"Dependency {name} reports AGPL terms; confirm build-tool use and "
                "distribution obligations."
            )
    manual.append(
        "Installed metadata is an inventory aid, not a legal compatibility opinion; "
        "review direct and transitive dependency terms for the commercial distribution model."
    )
    return records, hard_issues, manual


def build_report(
    *,
    pdf: Path = DEFAULT_PDF,
    epub: Path = DEFAULT_EPUB,
    pptx: Path = DEFAULT_PPTX,
    provenance: Path = DEFAULT_PROVENANCE,
) -> dict[str, Any]:
    sections: dict[str, Any] = {}
    hard_issues: list[str] = []
    manual: list[str] = []
    for key, function, path in (
        ("pdf", audit_pdf, pdf),
        ("epub", audit_epub, epub),
        ("pptx", audit_pptx, pptx),
        ("source_assets", audit_source_assets, provenance),
    ):
        section, section_issues, section_manual = function(path)
        sections[key] = section
        hard_issues.extend(section_issues)
        manual.extend(section_manual)
    dependencies, dependency_issues, dependency_manual = audit_dependencies(ROOT / "pyproject.toml")
    hard_issues.extend(dependency_issues)
    manual.extend(dependency_manual)
    return {
        "schema_version": 1,
        "checked_at": date.today().isoformat(),
        "status": "failed" if hard_issues else "passed_with_manual_review_required",
        **sections,
        "direct_dependency_license_inventory": dependencies,
        "hard_issues": sorted(set(hard_issues)),
        "manual_review_required": sorted(set(manual)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if not args.no_write:
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"Distribution preflight status={report['status']}, "
        f"hard_issues={len(report['hard_issues'])}, "
        f"manual_review={len(report['manual_review_required'])}"
    )
    for issue in report["hard_issues"]:
        print(f"- {issue}")
    return 1 if report["hard_issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
