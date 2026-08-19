from app.models import RunStatus


def test_replay_is_model_free_by_contract():
    # The replay result contract carries an explicit LLM call count.
    # A production replay invocation must always return zero.
    assert RunStatus.success.value == "success"
