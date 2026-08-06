from structured_extractor.domain import Extractor
from structured_extractor.providers import DeterministicIncidentProvider, ScriptedProvider


def test_valid_incident_is_extracted_to_typed_result() -> None:
    result = Extractor(DeterministicIncidentProvider()).extract(
        "支付服务发生严重超时，标题：支付超时"
    )

    assert result.title == "支付超时"
    assert result.severity == "high"
    assert result.affected_service == "payment"


def test_one_invalid_response_can_be_repaired_within_bound() -> None:
    provider = ScriptedProvider(
        responses=(
            {"title": "timeout", "severity": "urgent"},
            {"title": "timeout", "severity": "high", "affected_service": "api"},
        )
    )

    result = Extractor(provider, max_repairs=1).extract("API timeout")

    assert result.affected_service == "api"
    assert provider.calls == 2
