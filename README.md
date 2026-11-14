# ActRun

**A lightweight, open-source runtime and evaluation foundation for AI agents.**

ActRun is a Python and Rust project for running tool-using AI agents, recording their execution as structured events, and inspecting those execution traces.

The goal is to make agent execution easier to understand, test, and evaluate — without tying the project to a specific model provider.

> **Project status: Early development**
>
> ActRun is an experimental prototype. Its APIs and event format may change. It is not yet intended for production workloads or untrusted tool execution.

## Why ActRun?

AI agents do more than generate text. They can call tools, interact with external systems, and perform multi-step tasks.

Building reliable agents requires more than connecting a model to a set of tools. Developers also need a way to:

- Control the execution loop.
- Restrict which tools an agent can invoke.
- Set basic execution limits.
- Record what happened during a run.
- Inspect execution traces.
- Evaluate whether an agent produced an expected result.

ActRun is being built as a small, understandable foundation for these tasks.

## What ActRun does today

| Component | Current capability |
|---|---|
| Python runtime | Runs an asynchronous model/tool-calling loop |
| Tool registry | Exposes registered tools to the model |
| Tool restrictions | Rejects calls to tools that are not registered |
| Execution limits | Supports a maximum number of model steps and per-tool timeouts |
| Event recording | Writes structured execution events to JSONL |
| Basic evaluation | Compares actual output with an expected output |
| Rust trace engine | Reads JSONL events and aggregates basic execution metrics |

These capabilities are intentionally limited. The project will grow through tested, incremental additions.

## What ActRun is not

ActRun does not currently provide:

- A production-grade security sandbox.
- Container or process isolation for tools.
- Credential isolation or network egress enforcement.
- Built-in integrations with OpenAI, Anthropic, or other model providers.
- A complete benchmark or dataset management system.
- Deterministic trace replay.
- A graphical dashboard.
- Distributed execution or persistent run storage.
- A guarantee that an agent's output is correct or safe.

These are not implemented features and should not be assumed to exist.

## Architecture

ActRun uses Python for agent execution and Rust for trace processing.

```text
                    Application
                         |
                         v
                 Python AgentRuntime
                         |
                +--------+--------+
                |                 |
                v                 v
             Model API        Tool Registry
                |                 |
                +--------+--------+
                         |
                         v
                  Runtime Events
                         |
                         v
                   JSONL Event Log
                         |
                         v
                  Rust Trace Engine
                         |
                         v
                 Aggregated Metrics
```

The two languages have separate responsibilities:

### Python — Runtime and evaluation

The Python package currently contains:

- `models.py`: model protocol and response data structures.
- `runtime.py`: asynchronous execution loop and tool invocation.
- `events.py`: JSONL event recording.
- `evaluation.py`: basic exact-match evaluation.

Python owns agent execution. Rust does not run a second agent runtime.

### Rust — Trace processing

The Rust component reads the JSONL event log and calculates basic metrics, including:

- Total number of events.
- Number of distinct runs.
- Event counts by type.
- Tool failures.
- Tool denials.
- Completed runs.
- Failed runs.

The Rust component currently operates as a standalone command-line program.

## Getting started

### Requirements

- Python 3.10 or newer.
- Rust toolchain and Cargo, if you want to use the trace engine.
- Git.

### Clone the repository

```bash
git clone https://github.com/OWNER/ActRun.git
cd ActRun
```

Replace `OWNER` with the GitHub account or organization hosting the repository.

### Install the Python package

```bash
cd python
python -m pip install -e ".[dev]"
```

### Run the tests

```bash
pytest
```

## Python example

ActRun currently defines a provider-neutral `Model` protocol. You must implement that protocol for your chosen model provider.

The following example uses a small fake model. It demonstrates the current runtime API without requiring an API key or an external model provider.

```python
import asyncio

from agent_harness import AgentRuntime, ModelResponse, Tool, ToolCall
from agent_harness.events import JsonlEventSink


class ExampleModel:
    def __init__(self):
        self.calls = 0

    async def complete(self, messages, tool_specs):
        self.calls += 1

        if self.calls == 1:
            return ModelResponse(
                tool_calls=[
                    ToolCall(
                        name="add",
                        arguments={"a": 2, "b": 3},
                    )
                ]
            )

        return ModelResponse(content="The result is 5.")


def add(a: int, b: int) -> int:
    return a + b


async def main():
    model = ExampleModel()

    runtime = AgentRuntime(
        model=model,
        tools=[
            Tool(
                name="add",
                description="Add two numbers.",
                function=add,
            )
        ],
        event_sink=JsonlEventSink("runs.jsonl"),
        max_steps=5,
    )

    result = await runtime.run("What is 2 + 3?")

    print("Status:", result.status)
    print("Output:", result.output)
    print("Run ID:", result.run_id)


if __name__ == "__main__":
    asyncio.run(main())
```

The example demonstrates:

1. Implementing the `Model` protocol.
2. Registering a tool.
3. Running an agent task.
4. Recording runtime events.
5. Reading the final `RunResult`.

The example model is a test implementation, not a production model adapter.

## Tool registration

Tools are registered when the runtime is created.

```python
from agent_harness import AgentRuntime, Tool

runtime = AgentRuntime(
    model=my_model,
    tools=[
        Tool(
            name="search",
            description="Search a data source.",
            function=search_function,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"],
            },
            timeout_seconds=5,
        )
    ],
    max_steps=8,
)
```

The `parameters` field is passed to the model implementation as part of the tool specification. The current runtime does not independently validate arguments against this schema.

Only registered tool names can be invoked. Calls to unknown tools are denied and recorded as `tool.denied` events.

## Execution events

ActRun records events in JSON Lines format.

Each event currently contains:

```json
{
  "schema_version": "1",
  "event_id": "unique-event-id",
  "timestamp_unix_ms": 1730000000000,
  "run_id": "unique-run-id",
  "type": "run.started",
  "payload": {
    "task": "Example task"
  }
}
```

Current event types include:

- `run.started`
- `run.completed`
- `run.failed`
- `run.stopped`
- `tool.started`
- `tool.completed`
- `tool.failed`
- `tool.denied`

The event format is an early versioned contract. It may evolve as the project develops.

**Data handling:** event payloads may contain task text, tool arguments, or other application data. Do not write secrets, credentials, personal data, or sensitive production information to event logs unless you have implemented appropriate redaction and access controls.

## Basic evaluation

ActRun currently provides an exact-match evaluator.

```python
from agent_harness.evaluation import EvalCase, evaluate_exact_match

cases = [
    EvalCase(
        case_id="addition-001",
        task="What is 2 + 3?",
        expected_output="5",
    )
]

results = await evaluate_exact_match(runtime, cases)

for result in results:
    print(result.case_id, result.passed, result.status)
```

The evaluator runs each case through the runtime and compares the returned output with the expected output.

By default, comparison uses `str.strip()` to remove leading and trailing whitespace.

This is a basic correctness check, not a comprehensive evaluation framework. It does not currently support semantic grading, LLM-as-a-judge, benchmark reporting, statistical analysis, or dataset versioning.

## Rust trace engine

The Rust component processes an existing JSONL event file.

From the repository root:

```bash
cd rust/trace-engine
cargo test
cargo run -- ../../example-trace.jsonl
```

The command prints aggregated metrics as JSON.

The current trace engine validates that events can be deserialized and that `schema_version` is supported. It does not yet perform full semantic validation of event sequences.

## Project structure

```text
ActRun/
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── SECURITY.md
├── example-trace.jsonl
│
├── python/
│   ├── pyproject.toml
│   ├── src/
│   │   └── agent_harness/
│   │       ├── __init__.py
│   │       ├── models.py
│   │       ├── runtime.py
│   │       ├── events.py
│   │       └── evaluation.py
│   └── tests/
│       └── test_runtime.py
│
└── rust/
    └── trace-engine/
        ├── Cargo.toml
        └── src/
            └── main.rs
```

The current Python distribution is named `open-agent-harness`, and its import namespace is `agent_harness`. The project branding is ActRun; package and import names have not yet been migrated.

## Design principles

ActRun is being developed around a few principles:

- **Provider neutrality:** the runtime should not depend on one model vendor.
- **Clear responsibilities:** Python executes agents; Rust processes traces.
- **Observable execution:** important runtime events should be recordable.
- **Small core:** prefer understandable components over unnecessary abstraction.
- **Incremental reliability:** add capabilities with tests and documented limitations.
- **Honest evaluation:** distinguish measured results from assumptions.

## Roadmap

The following items are planned, not currently implemented.

- [ ] Stabilize the Python public API.
- [ ] Define and document the JSONL event schema.
- [ ] Add model-provider adapters.
- [ ] Improve tool argument validation.
- [ ] Add structured evaluation reports.
- [ ] Add benchmark dataset support.
- [ ] Add trace replay.
- [ ] Improve error handling and cancellation behavior.
- [ ] Add stronger runtime and security tests.
- [ ] Evaluate Python/Rust integration based on measured performance.
- [ ] Add CI workflows and release automation.

Roadmap items may change based on testing and community feedback.

## Security

ActRun is experimental software and is not a security boundary.

The current runtime does not isolate tool execution from the host process. A registered Python function executes with the permissions of the process running ActRun.

Do not use the current prototype to execute untrusted code or expose sensitive production systems.

Please read [SECURITY.md](SECURITY.md) before reporting a vulnerability or using ActRun in a sensitive environment.

## Contributing

Contributions, bug reports, tests, and design discussions are welcome.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

ActRun is distributed under the MIT License. See [LICENSE](LICENSE).

