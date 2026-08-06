from sampling_lab.domain import SamplingConfig, generate, probability_distribution
from sampling_lab.providers import FixedLogitModel


def test_top_k_and_top_p_filter_the_same_normalized_distribution() -> None:
    probabilities = probability_distribution(
        (4.0, 3.0, 2.0, 1.0),
        temperature=1.0,
        top_k=3,
        top_p=0.8,
    )

    assert round(sum(probabilities), 12) == 1.0
    assert probabilities[0] > probabilities[1] > 0.0
    assert probabilities[2:] == (0.0, 0.0)


def test_seeded_generation_is_reproducible() -> None:
    model = FixedLogitModel()
    config = SamplingConfig(temperature=0.8, top_k=3, top_p=0.95, max_tokens=5)

    first = generate(model, config=config, seed=2026)
    second = generate(model, config=config, seed=2026)

    assert first == second
    assert first.finish_reason == "max_tokens"
    assert len(first.tokens) == 5


def test_stop_token_terminates_before_maximum() -> None:
    model = FixedLogitModel(scripted_logits=((0.0, 0.0, 20.0, -20.0),))

    result = generate(
        model,
        config=SamplingConfig(max_tokens=8, stop_tokens=("<STOP>",)),
        seed=7,
    )

    assert result.tokens == ("<STOP>",)
    assert result.finish_reason == "stop"
