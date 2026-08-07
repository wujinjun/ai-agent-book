from pathlib import Path

import pytest
from pydantic import ValidationError

from framework_comparison.domain import BenchmarkSpec
from framework_comparison.fixture import PolicyDenied, ResearchTools
from framework_comparison.io import load_evidence, load_spec, verify_evidence_sources
from framework_comparison.scoring import compare_candidates


def test_weights_must_sum_to_one() -> None:
    payload = load_spec().model_dump()
    payload["criteria"][0]["weight"] = 0.99
    with pytest.raises(ValidationError, match="weights must sum"):
        BenchmarkSpec.model_validate(payload)


def test_missing_candidate_is_rejected() -> None:
    with pytest.raises(ValueError, match="exactly the three"):
        compare_candidates(load_spec(), load_evidence()[:2])


def test_evidence_records_real_source_hashes() -> None:
    root = Path(__file__).parents[1] / "src" / "framework_comparison" / "candidates"
    for item in load_evidence():
        source = root / item.implementation_path
        assert source.is_file()
        import hashlib

        assert hashlib.sha256(source.read_bytes()).hexdigest() == item.implementation_sha256
    verify_evidence_sources(load_evidence())


def test_fixture_denies_cross_tenant_document() -> None:
    import asyncio

    with pytest.raises(PolicyDenied, match="outside"):
        asyncio.run(ResearchTools().read_doc("D-secret"))
