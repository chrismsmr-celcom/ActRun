# Contributing to cerbere cohort

Thanks for your interest in cerbere cohort. This is an early-stage project, so contributions of every size matter, and so does honest feedback.

## The most useful contribution right now

**Evidence.** cerbere cohort is a bet that agents sharing mutable state need real coordination primitives. We want to know whether that is true for you.

If you run several agents against shared state, please open a [multi-agent failure report](https://github.com/chrismsmr-celcom/cerbere-cohort/issues/new?template=multi_agent_failure.yml). A concrete story ("two agents rewrote the same file", "a run deadlocked", "I could not tell who changed what") is worth more than a pull request at this stage.

## Ways to contribute

- **Report failures** you have hit with multi-agent systems.
- **Challenge the design.** If part of [`docs/CONCEPTS.md`](docs/CONCEPTS.md) looks wrong, open an issue and say so.
- **Fix bugs and add tests.** The prototype is small. A failing test that reproduces a bug is a great contribution on its own.
- **Improve the docs.** Anything unclear, outdated, or overclaiming is a good first contribution.
- **Build features** from the [roadmap](README.md#roadmap), after discussing them first (see below).

Issues labeled `good first issue` are meant for newcomers.

## Before you write code

For anything larger than a small fix, **open an issue first**. This applies in particular to:

- a new public API or a change to an existing one,
- any change to the event schema,
- any change to merge or conflict semantics (these must match `docs/CONCEPTS.md`, or change it in the same pull request),
- a new dependency,
- a new component or language boundary (Python vs Rust).

This avoids wasted work on a direction the project cannot accept.

## Development setup

Requirements: Python 3.10+, Git, and the Rust toolchain (stable) for the trace analyzer.

```bash
git clone https://github.com/chrismsmr-celcom/cerbere-cohort.git
cd cerbere-cohort

# Python
cd python
python -m pip install -e ".[dev]"
pytest

# Rust (from the repository root)
cd ..
cargo test
```

## Project layout

```
cerbere-cohort/
├── python/
│   ├── src/cerbere-cohort/          Library: workspace, merge, leases, deadlock, persistence, events
│   └── tests/               pytest suite
├── crates/cerbere-cohort-trace/     Rust trace analyzer (reads JSONL events)
├── schemas/                 Event schema (draft)
├── docs/CONCEPTS.md         Semantics and acceptance criteria (the reference)
├── examples/                Runnable scenarios
├── integrations/mcp-server/ MCP server (draft)
├── example-trace.jsonl      Sample event log used by the Rust analyzer
└── README.md, CONTRIBUTING.md, SECURITY.md
```

## Checks

CI runs the same commands. Please run them locally before opening a pull request.

```bash
# Python (from python/)
pytest

# Rust (from the repository root)
cargo fmt --check
cargo clippy --all-targets
cargo test
cargo run -p cerbere-cohort-trace -- example-trace.jsonl
```

Run `cargo fmt` to fix formatting automatically.

## Coding guidelines

**General**

- Keep the core small. A new dependency needs a justification in the pull request.
- Every behavior change comes with a test. Every bug fix comes with a regression test.
- `docs/CONCEPTS.md` is the reference for semantics. Code and docs must not disagree: if you change one, change the other.
- Keep the core provider-neutral: no model-vendor-specific code.

**Python**

- Python 3.10+ compatible.
- Type hints on all public functions and classes.
- Tests are real tests: they assert behavior. No scripts that only print.
- Concurrency tests must use timeouts and never rely on long sleeps.
- Never mutate a snapshot's data in place. State changes go through branches and commits.

**Rust**

- Stable toolchain. Code must pass `cargo fmt` and should be free of `clippy` warnings.
- Avoid `unsafe`. If you need it, explain why in a comment and in the pull request.

## Event schema changes

Events are written to JSONL and read by the Rust analyzer, so the event format is a contract. A change to it must:

1. update `schemas/event.v1.schema.json`,
2. update `example-trace.jsonl`,
3. update the Python event emitters and the Rust analyzer, with tests,
4. bump `schema_version` once that field exists (it is planned for milestone M1),
5. be described in the pull request, including whether old logs remain readable.

## Documentation must not overclaim

The README separates what exists from what is planned. Keep it that way. Do not describe a planned feature as implemented, and mark design sketches as sketches. Contributions that blur this line will be asked to change.

## Commits and pull requests

- One logical change per pull request. Small pull requests are reviewed faster.
- Write commit messages in the imperative mood ("Add lease timeout"), and reference the related issue.
- Fill in the pull request template.
- This is a small project: reviews may take a few days.

## Security and data

- Never commit secrets, credentials, or real user data. This includes event logs and test fixtures.
- Report security vulnerabilities as described in [SECURITY.md](SECURITY.md), not in public issues.

## License

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE).

## Code of conduct

Participation in this project is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
