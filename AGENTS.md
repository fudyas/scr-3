# Repository agent instructions

The Agentic SDLC workflow is operated exclusively through `./bin/lets sdlc ...`. Do not invoke its Python modules directly or edit the `sdlc` ledger by hand.

Use `$caveman full` for every instruction sent to an SDLC subagent and every authored section written into a `REQ-*` document. Preserve exact commands, paths, symbols, errors, hashes, and customer source text. Compress prose only; never remove technical substance, evidence, acceptance criteria, safety rules, or traceability.

Treat textual `/sdlc-*` requests as aliases for the matching repository skill:

| Text alias | Skill |
| --- | --- |
| `/sdlc-new` | `$sdlc-new` |
| `/sdlc-resume` | `$sdlc-resume` |
| `/sdlc-status` | `$sdlc-status` |
| `/sdlc-approve` | `$sdlc-approve` |
| `/sdlc-implement` | `$sdlc-implement` |
| `/sdlc-validate` | `$sdlc-validate` |
| `/sdlc-follow-up` | `$sdlc-follow-up` |
| `/sdlc-list` | `$sdlc-list` |
| `/sdlc-show` | `$sdlc-show` |
| `/sdlc-abandon` | `$sdlc-abandon` |

SDLC commands auto-progress through every stage that does not need developer input. Stop only at an explicit human gate, a safety failure, or a tooling-reported blocker. Every image change must be delivered as a reversible Debian package. Image mutation and package testing must hold the SDLC image lock across mount, install, test, uninstall, restoration verification, and unlock. A cleanup or restoration failure quarantines the image; never unlock or continue using it until the tooling reports recovery.
