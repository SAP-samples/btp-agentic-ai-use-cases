"""Tests for the per-model circuit breaker and the breaker-aware fallback chain.

Two layers are covered:
  - ``TestCircuitBreaker`` exercises the breaker state machine in isolation
    (stdlib-only, no agent import) using an injected clock for determinism.
  - ``TestInvokeWithFallbackChain`` drives ``SampleAgent._invoke_with_fallback``
    with a fake graph to verify chain walking, skipping of open models, error
    propagation, and the all-open last-resort attempt.
"""
# pyright: reportMissingImports=false

import pytest

pytestmark = pytest.mark.structure


class _Clock:
    """Deterministic, manually-advanced replacement for time.monotonic."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class TestCircuitBreaker:
    async def test_unknown_model_is_allowed(self, add_agent_to_path):
        from circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker()
        assert await breaker.allows("m") is True

    async def test_opens_only_at_threshold(self, add_agent_to_path):
        from circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
        await breaker.record_failure("m")
        await breaker.record_failure("m")
        assert await breaker.allows("m") is True  # 2 < 3, still closed
        await breaker.record_failure("m")
        assert await breaker.allows("m") is False  # 3 >= 3, now open

    async def test_success_resets_failure_streak(self, add_agent_to_path):
        from circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
        await breaker.record_failure("m")
        await breaker.record_failure("m")
        await breaker.record_success("m")
        await breaker.record_failure("m")
        await breaker.record_failure("m")
        # Only 2 consecutive failures since the reset; breaker stays closed.
        assert await breaker.allows("m") is True

    async def test_cooldown_elapses_to_half_open_probe(self, add_agent_to_path):
        from circuit_breaker import CircuitBreaker

        clock = _Clock()
        breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30, time_fn=clock)
        await breaker.record_failure("m")
        assert await breaker.allows("m") is False  # open, within cooldown
        clock.advance(29)
        assert await breaker.allows("m") is False  # still cooling down
        clock.advance(1)
        assert await breaker.allows("m") is True  # cooldown elapsed -> probe allowed

    async def test_probe_success_closes_breaker(self, add_agent_to_path):
        from circuit_breaker import CircuitBreaker

        clock = _Clock()
        # threshold=2 so that after the probe succeeds a single failure is NOT
        # enough to re-open: this proves the success fully closed the breaker and
        # reset the streak, rather than merely masking a still-counting state.
        breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=30, time_fn=clock)
        await breaker.record_failure("m")
        await breaker.record_failure("m")  # 2 >= 2 -> open
        assert await breaker.allows("m") is False
        clock.advance(30)
        assert await breaker.allows("m") is True  # half-open probe allowed
        await breaker.record_success("m")
        # Fully closed with a fresh streak: one failure stays under threshold=2...
        await breaker.record_failure("m")
        assert await breaker.allows("m") is True
        # ...and it takes a second failure to open again.
        await breaker.record_failure("m")
        assert await breaker.allows("m") is False

    async def test_probe_failure_reopens_for_another_cooldown(self, add_agent_to_path):
        from circuit_breaker import CircuitBreaker

        clock = _Clock()
        # threshold=2 isolates the half-open path: a lone probe failure cannot
        # re-cross the threshold by itself, so re-opening here can only come from
        # the half-open branch, not ordinary failure counting.
        breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=30, time_fn=clock)
        await breaker.record_failure("m")
        await breaker.record_failure("m")  # 2 >= 2 -> open
        clock.advance(30)
        assert await breaker.allows("m") is True  # half-open probe allowed
        await breaker.record_failure("m")  # probe fails
        assert await breaker.allows("m") is False  # re-opened via the half-open path
        clock.advance(30)
        assert await breaker.allows("m") is True  # next cooldown elapses

    async def test_threshold_below_one_is_clamped(self, add_agent_to_path):
        from circuit_breaker import CircuitBreaker

        # A threshold of 0 must not open the breaker before any failure.
        breaker = CircuitBreaker(failure_threshold=0, cooldown_seconds=30)
        assert await breaker.allows("m") is True
        await breaker.record_failure("m")
        assert await breaker.allows("m") is False  # clamped to 1 -> opens after 1

    async def test_negative_cooldown_is_clamped(self, add_agent_to_path):
        from circuit_breaker import CircuitBreaker

        clock = _Clock()
        breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=-5, time_fn=clock)
        await breaker.record_failure("m")
        # cooldown clamped to 0 -> immediately eligible for a probe.
        assert await breaker.allows("m") is True

    async def test_models_are_independent(self, add_agent_to_path):
        from circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30)
        await breaker.record_failure("m1")
        assert await breaker.allows("m1") is False
        assert await breaker.allows("m2") is True


# ---------------------------------------------------------------------------
# Fallback-chain tests
# ---------------------------------------------------------------------------


class _Transient(Exception):
    """Stand-in transient error, patched into agent.RETRYABLE_ERRORS."""


class _Fatal(Exception):
    """Non-transient error that must propagate without triggering fallback."""


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeGraph:
    """Graph whose ainvoke replays a queue of outcomes.

    Each outcome is either a return value (str -> wrapped as a message) or an
    Exception instance to raise. Popping from the queue lets a single model
    behave differently across successive attempts (e.g. fail then a later probe).
    """

    def __init__(self, outcomes: list) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    async def ainvoke(self, messages, config):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return {"messages": [_FakeMessage(outcome)]}


def _make_agent(agent_mod, graphs_by_model: dict, breaker):
    """Build a SampleAgent without running __init__, wired to fake graphs."""
    inst = object.__new__(agent_mod.SampleAgent)
    chain = list(graphs_by_model.keys())
    inst._primary_model = chain[0]
    inst._breaker = breaker
    # Chain entries are (name, llm); here the "llm" is the name itself so the
    # stubbed _create_graph can map straight to the right fake graph.
    inst._model_chain = [(name, name) for name in chain]

    def _create_graph(llm, tools, system_prompt):
        return graphs_by_model[llm]

    inst._create_graph = _create_graph
    return inst


async def _invoke(inst):
    return await inst._invoke_with_fallback(
        tools=[], system_prompt="sys", query="hi", context_id="c1"
    )


@pytest.fixture
def agent_mod(add_agent_to_path, monkeypatch):
    """Import the agent module with a controlled transient-error taxonomy.

    RETRYABLE_ERRORS is patched to a local exception so the tests do not depend
    on litellm exception constructor signatures, and get_user_sub is stubbed so
    no auth context is required.
    """
    import agent as agent_mod

    monkeypatch.setattr(agent_mod, "RETRYABLE_ERRORS", (_Transient,))
    monkeypatch.setattr(agent_mod, "get_user_sub", lambda: "user-1")
    return agent_mod


class TestInvokeWithFallbackChain:
    async def test_primary_success_skips_fallbacks(self, agent_mod):
        from circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
        graphs = {"m0": _FakeGraph(["primary-ok"]), "m1": _FakeGraph(["unused"])}
        inst = _make_agent(agent_mod, graphs, breaker)

        result = await _invoke(inst)

        assert result["messages"][-1].content == "primary-ok"
        assert graphs["m1"].calls == 0  # fallback never touched
        assert await breaker.allows("m0") is True

    async def test_transient_failure_advances_to_fallback(self, agent_mod):
        from circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
        graphs = {"m0": _FakeGraph([_Transient()]), "m1": _FakeGraph(["fallback-ok"])}
        inst = _make_agent(agent_mod, graphs, breaker)

        result = await _invoke(inst)

        assert result["messages"][-1].content == "fallback-ok"
        assert graphs["m0"].calls == 1
        assert graphs["m1"].calls == 1

    async def test_non_transient_error_propagates_without_fallback(self, agent_mod):
        from circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
        graphs = {"m0": _FakeGraph([_Fatal()]), "m1": _FakeGraph(["unused"])}
        inst = _make_agent(agent_mod, graphs, breaker)

        with pytest.raises(_Fatal):
            await _invoke(inst)
        assert graphs["m1"].calls == 0  # no fallback for non-transient errors
        # A non-transient error is not an availability signal, so it must not
        # count toward opening the breaker.
        assert await breaker.allows("m0") is True

    async def test_all_transient_raises_last_error(self, agent_mod):
        from circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
        last = _Transient("m1 failed")
        graphs = {"m0": _FakeGraph([_Transient()]), "m1": _FakeGraph([last])}
        inst = _make_agent(agent_mod, graphs, breaker)

        with pytest.raises(_Transient) as excinfo:
            await _invoke(inst)
        assert excinfo.value is last

    async def test_open_model_is_skipped(self, agent_mod):
        from circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30)
        await breaker.record_failure("m0")  # open m0
        graphs = {"m0": _FakeGraph(["should-not-run"]), "m1": _FakeGraph(["fallback-ok"])}
        inst = _make_agent(agent_mod, graphs, breaker)

        result = await _invoke(inst)

        assert result["messages"][-1].content == "fallback-ok"
        assert graphs["m0"].calls == 0  # skipped while open

    async def test_all_open_forces_attempt_on_primary(self, agent_mod):
        from circuit_breaker import CircuitBreaker

        clock = _Clock()
        breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=100, time_fn=clock)
        await breaker.record_failure("m0")
        await breaker.record_failure("m1")  # both open, cooldown not elapsed
        graphs = {"m0": _FakeGraph(["primary-forced"]), "m1": _FakeGraph(["unused"])}
        inst = _make_agent(agent_mod, graphs, breaker)

        result = await _invoke(inst)

        assert result["messages"][-1].content == "primary-forced"
        assert graphs["m0"].calls == 1
        assert graphs["m1"].calls == 0
        # The forced attempt succeeded, so the primary's breaker is reset.
        assert await breaker.allows("m0") is True

    async def test_works_without_a_breaker(self, agent_mod):
        graphs = {"m0": _FakeGraph([_Transient()]), "m1": _FakeGraph(["fallback-ok"])}
        inst = _make_agent(agent_mod, graphs, breaker=None)

        result = await _invoke(inst)

        assert result["messages"][-1].content == "fallback-ok"
