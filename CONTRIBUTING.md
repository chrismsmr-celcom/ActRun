# Contributing to ActRun

Thank you for considering a contribution to ActRun.

ActRun is an early-stage project. Contributions that improve correctness, clarity, tests, documentation, and the reliability of the existing implementation are especially valuable.

This document explains how to contribute.

## Project status

ActRun is experimental software. Its public APIs, internal architecture, and event schema may change.

Before starting substantial work, open an issue or discussion to explain the proposed change. This helps avoid duplicated effort and design decisions that conflict with the project's direction.

## Ways to contribute

You can contribute by:

- Reporting reproducible bugs.
- Improving tests.
- Fixing implementation issues.
- Improving documentation and examples.
- Reviewing API design.
- Improving the JSONL event contract.
- Improving Rust trace processing.
- Proposing model-provider integrations.
- Identifying security and reliability weaknesses.

Small, focused contributions are preferred.

## Development setup

### Requirements

- Python 3.10 or newer.
- `pip`.
- Rust and Cargo for Rust development.
- Git.

### Clone the repository

```bash
git clone https://github.com/OWNER/ActRun.git
cd ActRun
```

### Set up Python

```bash
cd python
python -m pip install -e ".[dev]"
```

Run the Python tests:

```bash
pytest
```

Run Ruff:

```bash
ruff check .
```

### Set up Rust

From the repository root:

```bash
cd rust/trace-engine
cargo test
```

Run the trace engine against the example log:

```bash
cargo run -- ../../example-trace.jsonl
```

## Contribution guidelines

### 1. Keep changes focused

A pull request should solve one clearly described problem.

Avoid combining unrelated refactors, formatting changes, new features, and documentation rewrites in one pull request.

### 2. Add or update tests

Changes to runtime behavior should include tests.

Changes to event processing should include tests for valid input and relevant failure cases.

Do not claim that a behavior is tested unless a test actually covers it.

### 3. Preserve the architecture

The current architectural separation is intentional:

- Python owns model interaction, agent execution, and basic evaluation.
- Rust processes recorded execution traces.
- JSONL is the current exchange format between runtime output and trace processing.

Do not introduce a second agent runtime in Rust without first discussing the architectural trade-offs.

### 4. Document limitations

If a feature has limitations, document them.

In particular, do not describe the current runtime as a sandbox or claim that tool arguments are schema-validated by the runtime.

### 5. Avoid unnecessary dependencies

New dependencies should have a clear technical justification.

Prefer the standard library when it is sufficient. Explain the maintenance, security, and performance implications of new dependencies.

## Pull request process

Before opening a pull request:

1. Make sure the change has a clear purpose.
2. Add or update relevant tests.
3. Run the Python tests if Python code changed.
4. Run Ruff if Python code changed.
5. Run Rust tests if Rust code changed.
6. Update documentation where necessary.
7. Review the diff for unrelated changes or accidentally committed secrets.

A pull request should include:

- A short description of the problem.
- What changed.
- Why the change is needed.
- Tests performed.
- Known limitations or follow-up work.

## Commit messages

Use concise, descriptive commit messages.

Examples:

```text
fix(runtime): handle unknown tool calls
test(runtime): cover tool timeout behavior
docs: clarify evaluation limitations
feat(trace): report tool denial counts
```

These prefixes are conventions, not a requirement for every contribution.

## Reporting bugs

When reporting a bug, include:

- Python or Rust version, as applicable.
- Operating system.
- Steps to reproduce.
- Expected behavior.
- Actual behavior.
- Relevant error messages.
- A minimal example when possible.

Remove API keys, tokens, personal data, and confidential application information before sharing logs.

## Security issues

Do not report exploitable vulnerabilities in public issues.

Follow the private reporting guidance in [SECURITY.md](SECURITY.md).

## Code of conduct

Be respectful, constructive, and specific.

Technical disagreement is welcome. Personal attacks, harassment, discriminatory behavior, and deliberate disruption are not.

## License

By submitting a contribution, you agree that your contribution will be distributed under the project's MIT License.

