from pathlib import Path

from scripts.audit_privacy import scan_repository, scan_text


def test_privacy_scanner_detects_personal_data() -> None:
    findings = scan_text(
        Path("sample.md"),
        (
            "联系 dev@"
            "corp.example，文件位于 /Users/"
            "bob/private，电话 13800"
            "138000。"
        ),
    )
    assert {finding.kind for finding in findings} == {
        "email address",
        "personal home path",
        "phone number",
    }


def test_privacy_scanner_allows_documented_placeholders() -> None:
    assert not scan_text(
        Path("sample.md"),
        (
            "使用 alice@example.test 和 /Users/alice/private 作为教材占位值；"
            "SHA-256 7ba4eb6d10b32b2d11dce13821340351cdbbb30ba8ccc67841db2ffd86e79aca。"
        ),
    )


def test_repository_has_no_accidental_personal_data() -> None:
    assert scan_repository() == []
