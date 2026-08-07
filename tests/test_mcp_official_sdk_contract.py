from pathlib import Path

ROOT = Path(__file__).parents[1]
SDK = ROOT / "projects/03-mcp-local-agent/official_sdk"


def test_official_mcp_sdk_slice_is_pinned_and_documented() -> None:
    required = (
        SDK / "README.md",
        SDK / "pyproject.toml",
        SDK / ".env.example",
        SDK / "src/mcp_local_official/server.py",
        SDK / "src/mcp_local_official/main.py",
        SDK / "tests/test_server.py",
    )
    assert all(path.is_file() for path in required)

    project = (SDK / "pyproject.toml").read_text(encoding="utf-8")
    readme = (SDK / "README.md").read_text(encoding="utf-8")
    tests = (SDK / "tests/test_server.py").read_text(encoding="utf-8")
    assert '"mcp==2.0.0"' in project
    assert "--transport stdio" in readme
    assert "--transport streamable-http" in readme
    assert "stdio_client" in tests
    assert "Client(" in tests and "http://127.0.0.1" in tests


def test_mcp_chapters_link_to_the_official_sdk_slice() -> None:
    for chapter in (
        ROOT / "docs/part-03-rag-and-memory/ch11-mcp.md",
        ROOT / "docs/part-03-rag-and-memory/ch12-mcp-server.md",
    ):
        source = chapter.read_text(encoding="utf-8")
        assert "projects/03-mcp-local-agent/official_sdk/" in source
        assert "mcp==2.0.0" in source

