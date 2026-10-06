"""Quote integrity is semantic for set fields, but strict for ordered action data."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_action_consequence import action
from test_cost_quotes import quote_fixture

from infra_joint.control.contracts import (
    ExecutionRequirements,
    LogicalModelAction,
    LogicalOutput,
)
from infra_joint.control.quote import QuoteProtocolError, action_sha256


@pytest.mark.parametrize("seed", ["0", "3", "33"])
def test_unmodified_quote_deepcopy_can_authorize_and_execute_across_hash_seeds(seed: str) -> None:
    code = """
import asyncio
import json
import sys
sys.path.insert(0, "tests")
from test_cost_quotes import quote_fixture
from test_action_consequence import action
from infra_joint.control.contracts import ExecutionRequirements
from infra_joint.control.quote import action_sha256, QuoteLedgerGateway

async def check():
    quotes, execution, _ = quote_fixture()
    logical = action(requirements=ExecutionRequirements(modalities=frozenset({'text', 'image'})))
    copied = logical.model_copy(deep=True)
    assert logical == copied
    assert action_sha256(logical) == action_sha256(copied)
    quote = await quotes.propose(logical, payload_json='{}', operator='invoke_model')
    pending = await quotes.authorize(quote.quote_id, owner='manager')
    outcomes = await QuoteLedgerGateway(quotes.gateway, quotes).execute_batch(
        (pending.action,), expose_profile=False)
    assert outcomes[0].observation.succeeded
    assert len(execution.actions) == 1
    print(json.dumps({'hash': action_sha256(logical), 'states': quotes.summary()['quote_states']}))

asyncio.run(check())
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONHASHSEED": seed},
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["states"] == {"consumed": 1}


def test_quote_hash_preserves_ordered_inputs_dependencies_and_output_contract() -> None:
    logical = LogicalModelAction(
        action_id="reason", owner_agent_id="manager", prompt="Answer.",
        inputs=("first", "second"), depends_on=("one", "two"),
        outputs=(LogicalOutput(artifact_id="note", semantic_type="evidence_note",
                               media_type="text/plain"),),
    )
    mutations = (
        {"prompt": "A different prompt."}, {"inputs": ("second", "first")},
        {"depends_on": ("two", "one")}, {"owner_agent_id": "specialist"},
        {"action_id": "other"}, {"outputs": ()},
        {"requirements": ExecutionRequirements(reserved_output_tokens=2)},
        {"requirements": ExecutionRequirements(modalities=frozenset({"text", "image"}))},
        {"requirements": ExecutionRequirements(
            required_capabilities=frozenset({"model", "vision"}))},
    )
    original_hash = action_sha256(logical)
    for changes in mutations:
        assert action_sha256(logical.model_copy(update=changes)) != original_hash


def test_quote_hash_is_stable_across_process_hash_seeds() -> None:
    code = """
from infra_joint.control.contracts import ExecutionRequirements, LogicalModelAction
from infra_joint.control.quote import action_sha256
a = LogicalModelAction(action_id='a', owner_agent_id='manager', prompt='Answer.',
    requirements=ExecutionRequirements(modalities=frozenset({'text','image'}),
        required_capabilities=frozenset({'model','vision','json'})))
print(action_sha256(a))
"""
    hashes = set()
    for seed in ("0", "3", "33"):
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True, text=True, check=True,
        )
        hashes.add(completed.stdout.strip())
    assert len(hashes) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["prompt", "requirements"])
async def test_actual_stored_quote_mutation_still_fails_closed(change: str) -> None:
    quotes, execution, _ = quote_fixture()
    quote = await quotes.propose(action(), payload_json="{}", operator="invoke_model")
    pending = quotes._quotes[quote.quote_id]
    if change == "prompt":
        pending.action = pending.action.model_copy(update={"prompt": "Different."})
    else:
        pending.action = pending.action.model_copy(update={
            "requirements": ExecutionRequirements(reserved_output_tokens=2)})
    with pytest.raises(QuoteProtocolError, match="quoted_action_mutated"):
        await quotes.authorize(quote.quote_id, owner="manager")
    assert not execution.actions
    assert quotes.summary()["quote_states"] == {"rejected": 1}
