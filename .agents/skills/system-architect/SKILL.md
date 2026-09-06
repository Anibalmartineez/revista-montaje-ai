---
name: system-architect
description: Audit unfamiliar or high-risk codebases, trace runtime flows and compatibility surfaces, align documentation, review branches, and produce approval-ready SAFE plans before broad or risky changes. Use for architecture audits, impact analysis, major refactors, production workflows, or pre-merge reviews; not for ordinary isolated edits.
---

# System Architect

Understand a system before changing it. Build an evidence-backed map of behavior, contracts, dependencies and risk, then propose the smallest safe path forward.

This skill defines the audit method. Project instructions define repository-specific files, priorities, commands and invariants; do not duplicate or override them here.

## Start protocol

Before substantive work:

1. Read applicable project instructions.
2. Determine the user's requested outcome and current authorization boundary.
3. Select the smallest operating mode that satisfies the request and state it.
4. Define the system boundary, version, branch or subsystem in scope.
5. Inspect repository and documentation state without modifying files.

Record whether the user authorized:

- file edits;
- documentation edits;
- tests or build commands;
- starting services;
- browser or interactive validation;
- external mutations;
- commits, merge or push.

Approval for analysis does not authorize implementation. Approval for implementation does not automatically authorize unrelated tests, external changes or Git publication.

## Operating modes

### Architecture audit

Use to reconstruct an unfamiliar or broad system.

- Start read-only.
- Trace entrypoint to observable output.
- Classify active, auxiliary, legacy, experimental, generated and disconnected surfaces.
- Do not modify files or execute unapproved runtime checks.

### Impact analysis

Use for a proposed change.

- Identify callers, callees, contracts, storage, UI workflows and tests.
- Estimate blast radius and shared dependencies.
- Separate necessary work from attractive but out-of-scope refactors.
- Produce an approval gate before broad, risky or contract-affecting edits.

### Documentation alignment

Use to compare documentation and implementation.

- Read project instructions and the documented source hierarchy first.
- Verify behavioral claims against executable code, persistence, runtime or tests.
- Classify documents as contractual, operational, historical, proposal or pending.
- Report aligned, outdated, ambiguous, conflicting and missing material separately.
- Preserve historical evidence; do not silently rewrite it as current state.

### Branch review

Use before integration.

- Identify current branch, target branch, working-tree state and merge-base.
- Include committed, staged, unstaged and untracked files in the review.
- Classify behavioral, contractual, test, documentation and out-of-scope changes.
- Distinguish a focused green suite from repository-wide health.
- Do not call failures pre-existing without an equivalent baseline on the target revision.
- Recommend merge, correction or additional validation with explicit residual risk.

## Source and evidence rules

Use the strongest evidence available for each claim:

1. persisted or generated artifact inspected directly;
2. authorized runtime observation;
3. automated test that exercises the behavior;
4. executable code, schema and configuration;
5. current contractual or operational documentation;
6. historical documentation or probable inference.

The order is contextual, not mechanical. A schema may be the authority for accepted data while runtime evidence proves what the application actually does.

For each important conclusion label it as appropriate:

- confirmed by artifact or persistence;
- confirmed by runtime;
- confirmed by automated test;
- confirmed by code or schema;
- documented intent;
- probable inference;
- pending verification.

Do not:

- present intent as implemented behavior;
- declare a feature operational because code, CSS or controls exist;
- treat HTTP success as proof of correct rendered or productive output;
- let a historical roadmap override current code;
- resolve conflicting evidence silently.

When sources conflict, identify the exact conflict and what evidence would resolve it.

## Audit workflow

### 1. Establish the boundary

- Detect entrypoints, runtime flags, manifests, routes, commands and deployment hints.
- Identify the exact product version and exclusions.
- Check Git state when branch or change context matters.
- Note external services, files, databases, queues, APIs, browsers and generated artifacts.

### 2. Build the functional map

- Trace the user or caller flow from entrypoint to output.
- Identify owners of state, mutation, validation, persistence and rendering.
- Distinguish persisted state from derived, cached and temporary state.
- Identify error, retry, conflict and recovery paths.

### 3. Trace dependencies and contracts

- Map imports, callers, callees, configuration, templates, selectors, schemas, fixtures and storage paths.
- Find shared engines, adapters, compatibility wrappers and legacy bridges.
- Treat APIs, schemas, storage formats, command interfaces, generated artifacts and operator workflows as compatibility surfaces.
- Flag duplicate responsibility, hidden coupling and cross-version contamination.

### 4. Assess risk

Pay special attention to:

- persistence and migrations;
- concurrency and atomicity;
- authentication, authorization and file security;
- geometry, units and coordinate systems;
- rendering and generated output;
- destructive or irreversible workflows;
- shared production engines;
- user-visible recovery behavior.

Classify findings:

- **Safe:** isolated, reversible and covered.
- **Moderate:** spans components or shared behavior.
- **High:** affects contracts, persistence, security, production output or core runtime paths.
- **Pending:** evidence is incomplete but useful work can continue.
- **Blocked:** safe checks are exhausted and a user decision or unavailable external condition is essential.

### 5. Review validation coverage

- Locate unit, contract, integration, end-to-end, snapshot and manual checks.
- Identify fixtures and whether they are synthetic, historical or production-derived.
- Match validation depth to risk.
- Record what was not executed and why.
- Prefer characterization before refactoring behavior that is not already covered.

For visual or interactive work, plan checks for rendered state, console errors, focus, keyboard, responsive behavior and persistence. For generated documents or production output, inspect the artifact itself and verify relevant dimensions, structure and visual or metric parity.

### 6. Produce the SAFE plan

Include:

- real problem and success criteria;
- in-scope and out-of-scope boundaries;
- confirmed behavior and open decisions;
- compatibility surfaces that must not break;
- files or subsystems likely to change;
- small reversible implementation phases;
- tests, fixtures and manual evidence required;
- rollback or containment strategy;
- assumptions and approval gates.

Do not begin a later phase merely because it is described in the same plan.

## Subagents

Use subagents only when the user explicitly requests delegation, the environment permits it, and the audit has genuinely independent areas.

When authorized:

- give each agent a bounded read-only scope unless implementation is separately approved;
- avoid overlapping file ownership;
- require concrete paths, symbols and evidence;
- wait for all relevant results before consolidating conclusions;
- keep responsibility for contradictions and the final SAFE plan with the primary agent.

## Change discipline

During approved implementation:

- preserve existing behavior unless the user approved a change;
- keep edits inside the approved phase;
- avoid opportunistic cleanup;
- protect unrelated and user-owned worktree changes;
- stop when new evidence materially expands the blast radius or requires a product decision.

After implementation, report:

- what changed and what did not;
- validation performed and omitted;
- residual risks and limitations;
- documentation or contracts updated;
- rollback path;
- whether the branch is ready for focused review.

Do not commit, merge, push, delete branches or perform external mutations unless the user explicitly authorizes them.

## Output shape

Keep the response proportional. For broad work, use the sections that help another engineer continue without rediscovery:

- Scope and Current State
- Functional Map
- Evidence
- Dependencies and Contracts
- Active vs Legacy or Disconnected Code
- Risks and Blast Radius
- Existing and Missing Coverage
- Open Decisions
- SAFE Plan and Rollback
- Acceptance Criteria
- Do Not Touch Yet

For small impact analyses, a compact summary is enough. Always separate confirmed facts from inference and make required user decisions visible.
