# {{ITEM_ID}} — Plan

## Goal

{{One paragraph: the result this item delivers and why.}}

## Context

{{Customer wording, relevant design, stable requirement IDs, source/image evidence, prior packages, dependencies, and existing code. Use architecture maps only when present.}}

## Deliverables

| # | Deliverable | Source requirement | Observable result, owned changes, and supported conditions |
| --- | --- | --- | --- |
| 1 | D1 | {{Customer requirement or accepted decision}} | {{Bounded result, owned artifacts/interfaces, and supported conditions. Add rows only for distinct deliverables.}} |

## Dependencies

1. {{Existing dependency, consumed interface, required assumption, and evidence needed for integration. State internals outside item ownership. Use none when absent.}}

## Design

1. **Fit:** {{How the change slots into the current code design.}}
2. **Patterns:** {{The CLEAN layers and existing building blocks it reuses.}}
3. **Context:** {{The architecture records and constraints it honors.}}
4. **Necessity:** {{Concrete deliverable failures that require added mechanisms. Prefer existing interfaces and simplest sufficient design.}}

## Out of scope

1. {{Work this item does not do.}}

## Safety

{{For image work: hardware-required item, device/image identity, package ownership, backups, maintainer scripts, upgrades, conflicts, rollback, full image-lock test window, restoration evidence, and developer hardware confirmation. For other work: applicable risks and evidence.}}

## Verification

{{Apply docs/SDLC-DEVELOPER-GUIDE.md#scope-and-verification. Keep item tests separate from mandatory gates. Map relevant failures and regressions without qualifying unchanged dependency internals.}}

| # | Deliverable criterion | Test and expected result | Defect detected or affected regression | Acceptance stage |
| --- | --- | --- | --- | --- |
| 1 | {{D1 and observable acceptance criterion}} | {{Focused check and expected result}} | {{Concrete defect in delivered behavior; for regressions, changed code and affected behavior}} | {{Assigned task or final item QA}} |

### Mandatory gates

1. {{Required repository or safety gate, source rule, applicability, and stage. Retain applicable package/image restoration checks.}}

### Post-task item acceptance

1. {{Assembled-item acceptance, independent QA/RESULT, exact-revision SHOW, and promotion obligations. These do not belong in task Done when.}}
2. {{For image work: separately authorized exact-package hardware procedure and developer confirmation before DONE. Otherwise state hardware not required.}}

## BLK-0001 — {{Block title}}

### TSK-0001 — {{UPPERCASE IMPERATIVE PHRASE}}

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | default |

**To do**

1. {{One change per step: deliverable reference, file, symbol, and canonical record link. Include affected consumers when required by this change.}}

**Done when**

1. {{Deliverable criterion and evidence achievable at this task's validation stage. Reference relevant tests and applicable task gates. Keep later item/hardware acceptance in header. Never invent absent tooling.}}
