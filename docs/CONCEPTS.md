# ActRun concepts

> **Status: design notes; partially superseded by the implementation.** The current Python prototype implements a key-value workspace, isolated branches, three-way conflict detection, resolver strategies, content-addressed snapshots, verified replay, leases, deadlock detection, and SQLite persistence. This document also describes a future document/path-oriented model that is **not** the current implementation. For shipped behavior, use the README status table and source code as the authority.

ActRun coordinates agents that share mutable state. This document fixes the vocabulary and the exact rules, so that code, tests and docs argue about the same thing.

## 1. Scope of v1

v1 answers one question, precisely:

> When several agents write to the same shared state, can we **detect** that their changes collide, **refuse to overwrite silently**, and **record** what happened?

In scope for v1: a versioned document workspace, branches, snapshots, conflict **detection** on merge, and an append-only event log.

Out of scope for v1: automatic content merging, binary files, networking or distributed operation, permission enforcement, leases and deadlock detection, performance tuning.

## 2. Glossary

| Term | Meaning |
| --- | --- |
| **Workspace** | A directory-backed store holding documents, snapshots, branches and the event log. |
| **Document** | UTF-8 text addressed by a path such as `spec/auth.md`. |
| **Snapshot** | An immutable mapping from paths to content hashes, plus the ids of its parent snapshots. |
| **Branch** | A named pointer to a snapshot. Writing on a branch creates a new snapshot and moves the pointer. |
| **Write** | Setting or deleting one document on a branch, by an identified agent, with optional intent. |
| **Merge** | Combining the heads of one or more branches into a target branch. |
| **Conflict** | Two or more branches changed the same path in incompatible ways. |
| **Event** | One record in the append-only log. |
| **Agent id** | A string naming who performed a write. Required on every write. |

## 3. State model (v1)

### Documents

- A workspace stores **documents addressed by path**.
- Paths are UTF-8 strings using `/` as separator, case-sensitive, with no empty segments and no `.` or `..` segments.
- Content is UTF-8 text. JSON is stored as text in v1. Structured merging of JSON is Planned.
- A document's identity is the **SHA-256 of its content**. Equal content means equal hash.

### Snapshots

- A snapshot maps every existing path to a content hash.
- Its id is derived from the mapping **and** its parent snapshot ids, so equal ids imply equal content and equal history.
- Snapshots are immutable. Nothing is ever edited in place.

### Branches

- A workspace starts with one branch, `main`.
- `branch(name)` creates a branch pointing at the current head of its source branch (the fork point).
- A write on a branch builds a new snapshot (copy-on-write) and moves that branch's head. Other branches are unaffected.
- **Writes on different branches never block or fail each other.** Collisions are handled at merge time, not at write time.

### Writes carry provenance

Every write records:

- `agent_id` (required),
- `path`,
- the new content hash, or a deletion marker,
- an optional free-text `intent` (why the agent made this change),
- a timestamp.

`intent` is metadata for humans, audits and arbiters. **In v1 it never influences how a merge is decided.**

## 4. Merge and conflict detection (v1)

`merge(branches, into="main")` combines the heads of `branches` into the target.

**Merge base.** The base is the most recent common ancestor of all heads involved, including the target's head. If there is no single such ancestor, v1 fails with an explicit `AmbiguousBase` error. It does not guess.

**Per-path rule.** Let `M` be the base content of a path, with "absent" meaning the path does not exist. A branch has *changed* the path if its content differs from `M`. Paths are decided independently:

| Base | Branch A | Branch B | Outcome |
| --- | --- | --- | --- |
| x | x | x | keep x |
| x | y | x | take y |
| x | y | y | take y (both agree) |
| x | y | z | **conflict** |
| x | deleted | x | take the deletion |
| x | deleted | deleted | take the deletion |
| x | deleted | y | **conflict** (delete vs modify) |
| absent | y | absent | take y |
| absent | y | y | take y |
| absent | y | z | **conflict** (divergent additions) |

The same rule extends to more than two branches: a path conflicts when two or more branches changed it to different outcomes.

**Granularity.** A document is the unit of conflict. Two agents editing different lines of the same file still conflict in v1. Line-level and structural merging are Planned and will arrive as merge strategies, not as a change to this rule.

**Atomicity.** A merge is all-or-nothing. If any path conflicts:

- no snapshot is committed and the target is unchanged,
- the result lists every conflict, with the base, each competing version, and each version's `agent_id` and `intent`,
- the result also exposes the cleanly merged paths for inspection.

*Open question:* whether a partial merge of the non-conflicting paths should ever be offered as an option.

**Invariant: ActRun never resolves a conflict silently.** Every conflict ends in an explicit resolution event or an abort event.

**Concurrent merges.** A merge commits with compare-and-swap on the target head. If the target moved since the merge started, the merge is retried against the new head or aborted. It never overwrites.

## 5. Resolution (implemented in the key-value prototype)

Resolution is how a detected conflict becomes a decision. It is pluggable.

A resolver receives a conflict (path, base, competing versions, agent ids, intents) and returns either a chosen content with a rationale, or "unresolved". Resolvers can be:

- **rule-based** (for example "prefer the branch with the later write"),
- **human** (a prompt or a review step),
- **an agent arbiter** (a model decides).

**Determinism rule.** An arbiter may be non-deterministic, but its *decision* must not be. The decision (chosen content hash, rationale, resolver identity) is recorded as a `merge.resolved` event. **Replay applies the recorded decision. It never calls the resolver again.** Non-determinism is confined to the instant the decision is made.

## 6. Events and the log

- Every state change appends events to an **append-only log**.
- The log is the **source of truth**. Workspace state is a projection derived from it.
- Events follow the existing versioned envelope: `schema_version`, `event_id`, `timestamp_unix_ms`, `run_id`, `type`, `payload`.

Draft event types for workspace behavior (the final contract lives in `EVENT_SCHEMA.md`):

| Event | Emitted when |
| --- | --- |
| `workspace.opened` | A workspace is created or opened |
| `branch.created` | A branch is forked |
| `document.written` | A document is set or deleted on a branch |
| `merge.started` | A merge begins |
| `merge.conflict_detected` | One or more conflicts are found |
| `merge.resolved` | A resolver decided a conflict (Planned) |
| `merge.completed` | A merge snapshot was committed |
| `merge.aborted` | A merge ended without committing |

These sit alongside the runtime events already in the prototype (`run.started`, `tool.completed`, and so on). Writes and merges carry `agent_id` so that runtime events and workspace events can be correlated.

*Open question:* whether adding event types requires a `schema_version` bump, or whether readers must ignore unknown types. To be settled in `EVENT_SCHEMA.md`.

## 7. Replay

**What replay guarantees.** Given the log and its content objects, replaying reconstructs every snapshot and branch head exactly. Because snapshot ids derive from content and history, a faithful replay produces **identical ids**, and that is how we test it.

**What replay does not do.** It replays *workspace state*, not agent behavior. ActRun does not re-run model calls and does not promise that re-running an agent produces the same writes.

**Content storage (proposed).** The workspace directory holds the log plus a content-addressed object store (`objects/<hash>`). Events reference content by hash.

## 8. Concurrency model

- v1 runs **in one process** with a single writer to the log, guarded by a lock.
- Isolation comes from branches. Agents do not contend on writes.
- Multi-process and multi-host operation is **Planned**, and is the main reason for the Rust core.

## 9. Leases and deadlocks (Planned)

Leases are advisory claims on a path or path prefix, held by an agent id for a bounded time. Their purpose is to avoid wasted work early. They do **not** replace conflict detection, which remains the safety net.

Deadlock detection will use a wait-for graph between agents and held leases. Exact semantics will be specified before implementation.

## 10. Prior art: why not just use X?

This section reflects the author's current understanding. Corrections are welcome and encouraged.

**Git branches and worktrees.** The closest existing answer, and the one to beat. If your agents only edit files in a repository, **a worktree per agent may be all you need**. ActRun is aimed at what Git does not model: agent identity and intent as first-class data on every write, a programmatic API at the granularity of agent actions, non-file state, leases and wait-for analysis between agents, and an event log designed to explain a multi-agent run. If ActRun cannot show value beyond Git for your case, use Git.

**Durable execution engines (Temporal and similar).** They make a single orchestrated workflow durable and replayable. They do not model shared mutable state among concurrent actors with merge semantics. The two are complementary, and ActRun's replay rule in section 5 follows the same principle of recording non-deterministic decisions.

**CRDTs.** They converge concurrent edits automatically without coordination, which is excellent for collaborative text. For agents, silent convergence can produce a result that is syntactically merged and semantically wrong. ActRun's stance is detect and escalate. A CRDT-based merge could later be offered as a resolution strategy.

**Databases with transactions or MVCC.** Excellent for structured data with a fixed schema. They do not capture intent and provenance per write, and they are a poor fit for document-shaped agent artifacts. A database could serve as a backing store later.

**Shared state in agent frameworks.** Some frameworks provide shared state with merge rules defined inside the framework. ActRun is framework-agnostic and aims to work underneath them.

## 11. Non-goals

- Not a security boundary and not a permission system.
- Not a replacement for Git where Git is enough.
- Not a guarantee that merged content is semantically correct, only that collisions are never hidden.

## 12. Open questions

1. Should the unit of conflict move from "document" to "JSON path" for structured data, and when?
2. Should a partial merge of non-conflicting paths be offered?
3. How should agents learn about conflicts: returned by `merge`, or pushed as events?
4. Do new event types bump `schema_version`?
5. What is the right locking strategy for multi-process access?
6. What is the minimal resolver interface that supports rule-based, human and agent arbiters?

## 13. What "Available" means for v1

The README may mark the workspace as **Available** only when automated tests prove all of the following:

1. Two branches writing **different content to the same path** produce a conflict on merge, and the target branch is unchanged.
2. Two branches writing **disjoint paths** merge cleanly, and the merged snapshot contains both.
3. Two branches writing **identical content** to the same path do not conflict.
4. A **delete versus modify** on the same path is reported as a conflict.
5. Every write, conflict and merge emits the corresponding event.
6. **Replaying the log** reconstructs snapshot ids identical to the original run.
7. A merge against a target that moved concurrently **never overwrites**.
