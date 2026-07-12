import json
from pathlib import Path

from ai_agent_book.diagram_pipeline import (
    extract_diagrams,
    replace_mermaid,
    write_manifest,
)


def test_diagram_ids_are_stable_and_markdown_is_replaced() -> None:
    source = "# Runtime\n\n```mermaid\nflowchart LR\nA --> B\n```\n"

    diagrams = extract_diagrams(Path("docs/runtime.md"), source)

    assert len(diagrams) == 1
    assert diagrams[0].diagram_id.startswith("runtime-")
    assert diagrams == extract_diagrams(Path("docs/runtime.md"), source)
    rendered = replace_mermaid(source, diagrams, Path("assets/diagrams"))
    assert "```mermaid" not in rendered
    assert '<source type="image/svg+xml"' in rendered
    assert ".png" in rendered
    assert "Runtime 图 1" in rendered
    assert 'alt="Runtime 图 1"' in rendered


def test_source_normalization_keeps_ids_stable() -> None:
    compact = "```mermaid\nflowchart LR\nA --> B\n```"
    padded = "```mermaid\r\nflowchart LR  \r\nA --> B\r\n\r\n```"

    assert extract_diagrams(Path("docs/runtime.md"), compact)[0].diagram_id == (
        extract_diagrams(Path("docs/runtime.md"), padded)[0].diagram_id
    )


def test_manifest_records_portable_assets(tmp_path: Path) -> None:
    diagrams = extract_diagrams(
        Path("docs/runtime.md"),
        "```mermaid\nflowchart LR\nA --> B\n```",
    )

    output = write_manifest(diagrams, tmp_path / "manifest.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload[0]["source_path"] == "docs/runtime.md"
    assert payload[0]["svg_path"].endswith(".svg")
    assert payload[0]["png_path"].endswith(".png")
