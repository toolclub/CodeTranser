import pytest

from app.langgraph.events import (
    EventType,
    RunEvent,
    RunEventBus,
    detect_event_type,
)
from app.repositories.event_log_repo import SqlEventLogStore
from app.utils.clock import utcnow


def test_event_type_priority_prefers_finished_over_started() -> None:
    payload = {"run_started": True, "run_finished": True}
    assert detect_event_type(payload) is EventType.RUN_FINISHED


def test_event_type_from_explicit_type() -> None:
    assert detect_event_type({"type": "step_completed"}) is EventType.STEP_COMPLETED


def test_event_type_unknown_for_empty() -> None:
    assert detect_event_type({}) is EventType.UNKNOWN


@pytest.mark.asyncio
async def test_event_log_append_and_read(session_factory) -> None:
    store = SqlEventLogStore(session_factory)
    bus = RunEventBus(redis=None, event_store=store)
    for i in range(3):
        await bus.emit(
            RunEvent(
                type=EventType.STEP_COMPLETED,
                run_id="r_test",
                ts=utcnow().isoformat(),
                node_name=f"n{i}",
            )
        )
    rows = await store.list_since("r_test", after_id=0)
    assert len(rows) == 3
    assert [r["event_type"] for r in rows] == [EventType.STEP_COMPLETED.value] * 3
    # id 严格递增
    ids = [r["id"] for r in rows]
    assert ids == sorted(ids)


@pytest.mark.asyncio
async def test_event_log_resume_since_id(session_factory) -> None:
    store = SqlEventLogStore(session_factory)
    eid_a = await store.append(run_id="r", event_type="run_started", event_data={})
    eid_b = await store.append(run_id="r", event_type="step_started", event_data={})
    eid_c = await store.append(run_id="r", event_type="step_completed", event_data={})
    rows = await store.list_since("r", after_id=eid_a)
    assert [r["id"] for r in rows] == [eid_b, eid_c]


@pytest.mark.asyncio
async def test_event_log_filter_by_message_id(session_factory) -> None:
    store = SqlEventLogStore(session_factory)
    await store.append(run_id="r", event_type="x", event_data={}, message_id="m1")
    await store.append(run_id="r", event_type="x", event_data={}, message_id="m2")
    rows = await store.list_since("r", after_id=0, message_id="m2")
    assert len(rows) == 1
    assert rows[0]["message_id"] == "m2"
