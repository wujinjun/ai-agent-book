import pytest

from sampling_lab.domain import SamplingConfig, probability_distribution


@pytest.mark.parametrize("temperature", [0.0, -0.1])
def test_temperature_must_be_positive(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature"):
        probability_distribution((1.0, 0.0), temperature=temperature)


@pytest.mark.parametrize("top_p", [0.0, -0.1, 1.1])
def test_top_p_must_be_in_valid_range(top_p: float) -> None:
    with pytest.raises(ValueError, match="top_p"):
        probability_distribution((1.0, 0.0), top_p=top_p)


def test_top_k_and_max_tokens_must_be_positive() -> None:
    with pytest.raises(ValueError, match="top_k"):
        probability_distribution((1.0, 0.0), top_k=0)
    with pytest.raises(ValueError, match="max_tokens"):
        SamplingConfig(max_tokens=0)


def test_empty_or_non_finite_logits_are_rejected() -> None:
    with pytest.raises(ValueError, match="logits"):
        probability_distribution(())
    with pytest.raises(ValueError, match="有限"):
        probability_distribution((1.0, float("nan")))
