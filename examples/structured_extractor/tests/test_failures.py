from typing import Any

import pytest

from structured_extractor.domain import ExtractionFailed, Extractor, SensitiveInputRejected
from structured_extractor.providers import ScriptedProvider


@pytest.mark.parametrize(
    "response",
    [
        {"title": "timeout", "severity": "high"},
        {"title": "timeout", "severity": 7, "affected_service": "api"},
        {"title": "", "severity": "high", "affected_service": "api"},
    ],
)
def test_missing_wrong_and_partial_outputs_fail_with_stable_public_error(
    response: dict[str, Any],
) -> None:
    extractor = Extractor(ScriptedProvider(responses=(response,)), max_repairs=0)

    with pytest.raises(ExtractionFailed) as captured:
        extractor.extract("partial incident")

    assert str(captured.value) == "结构化抽取失败；请检查输入或稍后重试"
    assert "validation" not in str(captured.value).lower()


def test_repairs_are_bounded() -> None:
    provider = ScriptedProvider(
        responses=({"severity": "bad"}, {"severity": "bad"}, {"severity": "bad"})
    )

    with pytest.raises(ExtractionFailed) as captured:
        Extractor(provider, max_repairs=1).extract("incident")

    assert captured.value.attempts == 2
    assert provider.calls == 2


def test_sensitive_input_is_rejected_before_provider_call() -> None:
    provider = ScriptedProvider(
        responses=({"title": "x", "severity": "low", "affected_service": "api"},)
    )

    with pytest.raises(SensitiveInputRejected):
        Extractor(provider).extract("password=super-secret-value")

    assert provider.calls == 0
