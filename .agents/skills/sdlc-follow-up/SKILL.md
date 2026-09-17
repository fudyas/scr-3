---
name: sdlc-follow-up
description: Record real-hardware results, close a successful SCR requirement, or open and auto-run the next bug-fixing round. Use for `$sdlc-follow-up` or textual `/sdlc-follow-up` requests.
---

# Record hardware follow-up

Ask for the tested package versions, hardware/image identity, procedure, expected behavior, observed behavior, and relevant logs when the user's report does not establish them. Pass the report verbatim plus structured details to `./bin/lets sdlc follow-up`; do not edit the ledger document directly.

Explicit success closes the current round and requirement. A failure closes the current round as failed and opens the next numbered bug-fixing round; then run `./bin/lets sdlc resume <REQ>` so requirements analysis begins from the recorded symptoms and the workflow auto-progresses to its next human gate.
