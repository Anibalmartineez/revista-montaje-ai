---
name: system-architect
description: Audit repositories, trace dependencies, identify risks, review tests, and propose safe implementation plans before editing code.
---

# System Architect

Use this skill to understand a codebase before making important changes. Work as a system architect: gather facts from the repository, map behavior and dependencies, identify risks, and produce a SAFE plan before editing files.

## Core Rules

- Explore before proposing changes.
- Prefer repository evidence over assumptions.
- Read project instructions when present, but do not depend on any specific instruction file name.
- Do not assume a language, framework, architecture, package manager, or file layout.
- Separate confirmed facts from inferences.
- Do not modify files while performing an architecture audit unless the user explicitly approves implementation.
- Treat public APIs, schemas, storage formats, command interfaces, generated artifacts, and user workflows as compatibility surfaces.
- Preserve existing behavior unless the user explicitly asks to change it.

## Architecture Audit Workflow

1. Identify the system boundary:
   - Detect entrypoints, configuration, package manifests, build files, runtime commands, and deployment hints.
   - Identify major subsystems and their responsibilities.
   - Note external services, databases, queues, APIs, CLIs, UI surfaces, generated files, and test harnesses.

2. Build a functional map:
   - Trace the user-facing or caller-facing flow from entrypoint to output.
   - Identify important modules, services, components, routes, commands, jobs, schemas, and data transformations.
   - Mark which code appears active, auxiliary, legacy, experimental, generated, or disconnected.
   - Highlight uncertainty when usage cannot be proven.

3. Trace dependencies:
   - Map direct imports, callers, callees, configuration references, templates, assets, migrations, tests, and documentation links.
   - Look for duplicate responsibility, hidden coupling, circular dependencies, and compatibility wrappers.
   - Prefer static search and language-aware tools when available.

4. Assess risk:
   - Identify files and behaviors with high blast radius.
   - Flag risky changes to contracts, persistence, authentication, authorization, concurrency, rendering, background jobs, build systems, or production workflows.
   - Distinguish safe refactors from behavior changes.
   - Identify rollback or containment strategies when relevant.

5. Review validation coverage:
   - Find existing tests, fixtures, snapshots, integration checks, smoke tests, CI workflows, and manual validation paths.
   - Determine what behavior is already characterized.
   - Propose missing tests for critical flows and edge cases.
   - Match validation depth to risk and blast radius.

6. Produce a SAFE plan:
   - State the real problem being solved.
   - Define the intended behavior and non-goals.
   - List the files or subsystems likely to change.
   - Describe the implementation sequence in small reversible steps.
   - Include validation commands and acceptance criteria.
   - Call out risks, assumptions, and decisions that require user approval.

## Output Format

When analyzing a system, structure the response with these sections when useful:

- Current State
- Functional Map
- Dependencies
- Active vs Legacy or Disconnected Code
- Risks
- Test Coverage
- Missing Tests
- SAFE Plan
- Open Questions

Keep the output proportional to the request. For small changes, summarize briefly. For broad refactors, provide enough detail that another engineer can implement safely without rediscovering the architecture.

## SAFE Plan Requirements

A SAFE plan must include:

- Goal and success criteria.
- In-scope and out-of-scope boundaries.
- Proposed implementation phases.
- Compatibility surfaces that must not break.
- Files or subsystems likely to be touched.
- Validation commands or manual checks.
- Rollback or containment notes when the change is risky.
- Explicit assumptions where repository evidence is incomplete.

## Classification Guidance

Classify findings and proposed changes as:

- Safe: low blast radius, well-covered, reversible, or isolated.
- Moderate risk: touches shared behavior, contracts, or multiple subsystems.
- High risk: changes public interfaces, persistence, security, production workflows, generated outputs, or core runtime paths.
- Blocked: insufficient information, missing environment, ambiguous product intent, or validation impossible without user input.

## Test Planning Guidance

When proposing tests, include:

- Existing tests that should continue passing.
- Focused characterization tests before refactors.
- Regression tests for changed behavior.
- Integration or end-to-end tests for user-visible flows.
- Contract tests for APIs, schemas, file formats, or CLI output.
- Manual validation steps only when automated coverage is impractical.

## Change Discipline

Before implementation, confirm that the plan is approved when the change is broad, risky, architectural, or contract-affecting. During implementation, keep edits scoped to the approved plan and avoid opportunistic refactors. After implementation, report what changed, what was validated, and any remaining risk.
