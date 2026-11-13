---
name: sdlc-chain-plan
description: >-
  Plan or revise SCR SDLC chains through an interactive conversation. Use
  session context and user rulings to define complete effort areas, consolidate
  existing scope, and mint items when authorized. Use for chain decomposition
  and cross-item scope changes, not a single item's implementation plan or chain
  execution.
---

# SDLC chain planning

One item closes one coherent functionality, data, or effort area within the agreed release scope.
Later items consume its result. They do not finish its completion claim.
Prefer the fewest complete items that remain practical to review and verify.

The user often develops the chain through an ongoing conversation.
Stay in that conversation. Do not require a new intake, a complete specification, or an existing chain ID.
Use `$sdlc-chain-plan` or `/sdlc-chain-plan`.

The [SDLC guide](../../../docs/SDLC-DEVELOPER-GUIDE.md) owns statuses, ledger operations, plans, approvals, and execution.
The [agent platform contract](../../../docs/SDLC-DEVELOPER-GUIDE.md#run-and-independent-roles) defines Codex roles and independent handoffs.

READ [Codex role dispatch](../../../docs/SDLC-DEVELOPER-GUIDE.md#codex-role-dispatch) before each worker launch.
This skill explicitly authorizes configured model and mapped effort overrides for fresh independent SDLC workers.
Use `fork_turns="none"` with overrides and a complete reconstructed handoff containing every contract field.
Full-history inheritance uses `fork_turns="all"` with neither `model` nor `reasoning_effort`.
Check current tool-supported models, efforts, custom roles, and concurrency before dispatch. Missing or unsupported mapping blocks dispatch with exact evidence.
Use available custom SDLC role, or `default` worker with complete role body. Count coordinator and all existing workers.
Configuration changes affect future launches. They do not switch an already-running coordinator.

READ [Managed stage artifacts](../../../docs/SDLC-DEVELOPER-GUIDE.md#managed-stage-artifacts).
Store planning, implementation, and QA deliverables under `.codex/sdlc/artifacts/`; keep product source and documentation on working branch.
Publish explicit INPUT or RESULT manifests through `./bin/lets sdlc artifacts publish`; retain immutable ledger bundles and original path/hash provenance.
Do not force-add ignored artifacts. Preserve original bytes until independent durable restore comparison passes.
Image runtime siblings remain protected. Never enumerate or clean them through artifact tooling. `.lets` state, drafts, leases, and telemetry retain current locations.
Review binds source tree and immutable INPUT digest. QA publishes separate RESULT for exact pair, without self-reference. Historical QA evidence can be INPUT.
Artifact-bearing review requires `--expected-artifacts DIGEST` on verified, approve, settle, prepare-promotion, and promote. Never downgrade missing artifact index to source-only.
This skill defines item boundaries and chain membership. It does not approve implementation plans or start execution.
Chat uses the session register. Item descriptions use `$caveman full` with exact technical substance.

## Conversation context

Maintain a short working brief in the conversation or an existing host-local draft:

1. The intended outcome, release, included areas, and explicit exclusions.
2. Accepted user rulings, their sources, and the proposals they replace.
3. Open questions and assumptions, separate from accepted decisions.
4. Existing item IDs, proposed boundaries, and current authorization for ledger changes.

User rulings can appear as corrections, examples, rejected alternatives, or direct instructions.
Preserve their conditions and scope. Do not turn an assistant suggestion into an accepted ruling.
The latest explicit ruling supersedes an earlier conflicting ruling.
Silence does not settle a product decision or authorize a ledger change.

5. READ the available session context before asking for missing information.
6. READ project design and image evidence and the relevant [SDLC context](../../../docs/SDLC-DEVELOPER-GUIDE.md#architecture-context).
7. READ the selected records, required dependencies, and relevant code.
8. SYNC the ledger with `./bin/lets sdlc sync`.
9. READ related chains and items, including DONE results, approved plans, reviews, and relevant obsolete history.
10. COMPARE the working brief with those records.
   10.1. ***if*** a conflict affects a boundary without an explicit ruling:
      10.1.1. ASK one focused question with a recommendation.
      10.1.2. CONTINUE work on unaffected areas.
11. ***for each*** new user ruling:
   11.1. UPDATE the working brief.
   11.2. REASSESS affected items, consumers, acceptance criteria, and dependencies across chain boundaries.
   11.3. SHOW the scope changes and their reasons.

Do not repeat settled questions or restart the whole decomposition after each answer.
Keep proposed items provisional during exploration. A request for options or criteria does not request minting.
Before a handoff, retain the working brief and unresolved questions with the proposed item table.
After resumption, refresh ledger state instead of inferring item status from the conversation.

## Item boundaries

| # | Criterion | Required result |
| --- | --- | --- |
| 1 | Completion | One concrete outcome and observable evidence establish completion within the declared scope. |
| 2 | Cohesion | Work that shares invariants, a data lifecycle, or repeated joint decisions stays together. |
| 3 | Ownership | Each required artifact and contract change has one owning item. Consumers reference that owner. |
| 4 | Coverage | Scope includes the required models, schemas, migrations, SQL, repositories, assets, interfaces, tests, and documentation. Only applicable parts belong. |
| 5 | Verification | After its prerequisites complete, the item can prove its own outcome without a later item. |
| 6 | Decisions | Decisions that determine behavior or data shape precede dependent implementation boundaries. Implementation choices remain in item planning. |
| 7 | Consumers | Shared changes include necessary updates to existing consumers and removal of replaced implementations. |
| 8 | Dependencies | Each dependency names a required result. Chain order, shared files, and preferred scheduling alone do not establish prerequisites. |

An exclusion cannot remove work required by the completion claim.
For data work, identify the complete model family and its required representations, constraints, indexes, views, and migration behavior.
Keep required corpus assets with the validation that requires their presence.
Apply image, package restoration, and real-hardware safety rules.
Separate acceptance work covers additional integration or release evidence. It cannot be the first proof of an earlier item's promised behavior.

A model library, schema, infrastructure component, or design contract can be a complete effort area.
It needs a useful deliverable, a stable consumer contract, and appropriate evidence of its own completion.
It does not need to deliver every future consumer.
Unsettled semantics and unused speculative abstractions do not establish a complete foundation.
Substantial design work can have its own item. Do not mint detailed downstream scope around unresolved product choices.

### Split exception

A split needs both a concrete size problem and a valid completion boundary.
Size problems include excessive review context, costly verification, difficult rollback, or too many independent decisions for reliable planning.
File count, task count, service count, and one-session duration alone do not justify a split.
Use tasks and blocks for internal decomposition under the SDLC contract.

Each proposed child must have its own completion claim, acceptance evidence, and stable contract with the other children.
Each intermediate promotion must leave a valid state within its declared scope.
Record why internal tasks cannot adequately manage the size problem and how the split reduces it.
Do not split solely by architecture layer, document section, or opportunities for parallel execution.
Choose complete item boundaries before grouping and scheduling chains.

## Existing scope

Derive effective scope from current rulings, review decisions, approved plans, and implementation evidence.
An item title or DONE status alone does not prove that its original description was delivered.
`REVIEW.md` overrides conflicting `PLAN.md` text under the SDLC contract.

| # | Disposition | Use |
| --- | --- | --- |
| 1 | Reuse | Existing work already supplies the required result. |
| 2 | Amend | An unstarted item still owns the outcome, but its scope or description needs correction. |
| 3 | Consolidate | Several items divide one complete effort. Keep one suitable owner and transfer every remaining obligation. |
| 4 | Obsolete | The premise disappeared, work already exists, or another item explicitly absorbs the remaining scope. |
| 5 | Mint | A required outcome has no suitable owner in the existing ledger. |

Preserve stable IDs when the same outcome remains. Do not rewrite DONE items to describe new work.
Active items retain their execution and review ownership. Route their changes through the applicable SDLC stage.
Amending a PLANNED description does not update its approved plan. Changed implementation scope requires the existing replanning workflow.
Consolidation preserves the destination, reason, and disposition of every acceptance obligation.
Each obligation remains covered, becomes explicitly postponed, or is removed by a user ruling.
Obsolete items cannot satisfy dependencies that require DONE.

## Reviewable proposal

Present one chain outcome and an item table with these columns:

| # | Candidate or existing ID | Outcome and owned scope | Completion evidence | Dependencies | Disposition |
| --- | --- | --- | --- | --- | --- |

Use provisional labels until the ledger assigns IDs.
Below the table, state exclusions, ruling sources, split reasons, unresolved questions, and proposed changes to other chains.
Identify the models, contracts, and existing code that determine each boundary through canonical links.
Keep implementation tasks and detailed solution design for `/sdlc-plan`.

Before proposing minting, verify coverage, unique ownership, valid intermediate states, and an acyclic dependency graph.
Internal prerequisites must precede their consumers. Unfinished external prerequisites make the chain not ready for execution.
Do not claim that separate chains can run independently while they share unresolved contracts or require changes from each other.

## Authorized ledger changes

The proposal must make the intended batch concrete before writes.
Existing user authorization for that batch remains valid. Do not ask again or seek separate approval for every item.
A request to mint the discussed chain can authorize its described additions.
It does not implicitly authorize unrelated retirement or replacement of active work.

1. ***if*** authorization for a proposed ledger change is missing:
   1.1. ASK one batch question that names the changes and explains the missing authorization.
2. ***if*** the user authorized the batch:
   2.1. SYNC the ledger again before writes.
   2.2. VERIFY affected items, statuses, scope, and membership against the proposal.
   2.3. ***if*** fresh state invalidates a proposed change:
      2.3.1. RECONCILE that change before its write.
   2.4. APPLY authorized changes through `./bin/lets sdlc` only.
   2.5. VERIFY the resulting item scope, dependencies, and chain membership through fresh reads.
   2.6. REPORT actual IDs, changed scope, unresolved blockers, and the next SDLC stage.

Use command `--help` for current arguments. Use files for multiline ideas and descriptions.
Preserve the raw user intent and relevant ruling sources in each item alongside its normalized scope.
Mint prerequisites before dependents. Repair active dependency references before obsoleting their former prerequisite.
`chains items` replaces the entire membership list. Preserve unaffected members and order.
Each item can belong to only one chain. A move must account for both affected chains.
Ledger writes are separate operations, not one atomic batch.
After a failed write, sync and inspect the result before any retry, especially a mint that can create a duplicate.
Report a partially applied batch and its remaining work. Do not continue dependent writes after an unresolved failure.
Never edit the ledger branch by hand or infer plan approval from chain agreement.

