---
name: structured-english
description: Write algorithms in Structured English — readable, precise pseudo-code for non-programmers. Auto-invoke whenever a plan, response, or document presents, explains, or specifies an algorithm or step-by-step procedure. Renders as Markdown numbered nested lists with UPPERCASE action verbs and ***lowercase bold-italic*** logic keywords (***if***/***while***/***for each***); scope is shown by list nesting, never by block closers.
---

# Structured English

Apply whenever you express an **algorithm** — any ordered procedure with logic, branching, or repetition — in a plan, a chat response, or a written document (`docs/*`, design notes, specs). This is the house style for describing *how* something works to a reader who may not program.

## When to apply

- **Auto-invoke** when a plan or response lays out algorithmic steps, or a document section describes a procedure, flow, or algorithm.
- Use it for the **description** of logic. Real source code still goes in fenced code blocks in its own language — Structured English explains or specifies it, it does not replace it.
- Skip it for prose that has no algorithm (narrative, rationale, prose summaries).

## Core principles

- **Readability** — a non-programmer can follow it without technical training.
- **Clarity** — no ambiguous, poetic, or vague language. One action per step.
- **Precision** — the steps reflect the exact sequence of logic, in order.

## Structural rules

- **Numbered nested lists — never a code fence.** Write the algorithm as a Markdown numbered list. Fences are reserved for real source code; Structured English is prose-grade Markdown so it renders inline in any document.
- **Action verbs first, UPPERCASE.** Begin each step with an imperative verb: `GET`, `SET`, `CALCULATE`, `ADD`, `STORE`, `DISPLAY`, `RETURN`, `SEND`, `INITIALIZE`.
- **Logic keywords lowercase and bold-italic.** Write every control word as `***keyword***`: `***if***`, `***then***`, `***else***`, `***else if***`, `***while***`, `***for each***`, `***in***`, `***repeat***`, `***until***`, `***case***`, `***of***`, `***default***`, `***and***`, `***or***`, `***not***`.
- **Scope by nesting — no block closers.** A construct's body is a nested numbered sub-list one level under it; the indentation ends the block. Never write `ENDIF`, `ENDWHILE`, `ENDFOR`, or `ENDCASE`. An `***else***` sits back at the parent level, aligned under its `***if***`.
- **Exact names.** Refer to data and operations by the precise terms from the system's data dictionary — not paraphrases or synonyms.
- **JavaScript-style variables.** Hold results from earlier steps in named variables (`camelCase`, meaningful words) and refer back to them by name, shown in `backticks`: `userData`, `eligibleOrders`, `runningTotal` — never `x`, `tmp`, or `rc`.
- **One action per step.** Do not chain multiple operations into one list item.

## Keyword vocabulary

- **Actions (UPPERCASE):** `GET`, `READ`, `SET`, `INITIALIZE`, `CALCULATE`, `COMPUTE`, `ADD`, `APPEND`, `REMOVE`, `STORE`, `SAVE`, `DISPLAY`, `SEND`, `RETURN`.
- **Selection:** `***if*** … ***then***`, `***else***`, `***else if***`, `***case*** … ***of***`, `***default***`.
- **Iteration:** `***while***`, `***for each*** … ***in***`, `***repeat*** … ***until***`.
- **Logical operators:** `***and***`, `***or***`, `***not***`.

## Logic construct templates

### Sequence

1. GET the input data into `userData`
2. CALCULATE `resultValue` from `userData`
3. STORE `resultValue` on disk

### Selection

1. ***if*** condition is true ***then***
   1. EXECUTE action A
2. ***else***
   1. EXECUTE action B

Multi-way selection:

1. ***case*** `orderStatus` ***of***
   1. "pending": SEND a reminder to the customer
   2. "shipped": DISPLAY the tracking number
   3. "closed": ARCHIVE the order
   4. ***default***: LOG the unknown status

### Iteration

While:

1. ***while*** condition is true
   1. EXECUTE the repeated action

For each:

1. ***for each*** item ***in*** `collection`
   1. EXECUTE the repeated action

Repeat:

1. ***repeat***
   1. EXECUTE the repeated action
2. ***until*** condition is true

## Worked example

1. GET all of today's orders into `todaysOrders`
2. INITIALIZE `flaggedOrders` as an empty list
3. ***for each*** order ***in*** `todaysOrders`
   1. CALCULATE `orderTotal` from the order line items
   2. ***if*** `orderTotal` is greater than 1000 ***and*** the order is unverified ***then***
      1. ADD the order to `flaggedOrders`
4. ***if*** `flaggedOrders` is not empty ***then***
   1. SEND `flaggedOrders` to the review queue
   2. DISPLAY the count of `flaggedOrders` to the operator
5. ***else***
   1. DISPLAY "no orders need review"

## Do and don't

- **Do** write the algorithm as a Markdown numbered list, never inside a code fence.
- **Do** start every step with an UPPERCASE imperative verb.
- **Do** write logic keywords as lowercase `***bold-italic***`, and show every block's scope by nesting it as a sub-list.
- **Do** name intermediate results as variables and reuse those exact names downstream.
- **Don't** add block closers (`ENDIF`, `ENDWHILE`, `ENDFOR`, `ENDCASE`) — the indentation ends the block.
- **Don't** use programming-language syntax — no braces, semicolons, or operators like `&&`, `==`, `++`.
- **Don't** write vague or poetic steps ("handle the data gracefully"). State the exact operation.
- **Don't** pack two actions into one step.
