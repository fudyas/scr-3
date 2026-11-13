#!/usr/bin/env bash
# PreToolUse hook: protect the project's shared database data from being dropped
# or deleted without explicit user consent.
#
# If the project runs a persistent datastore (e.g. a PostgreSQL cluster bind-mounted
# under var/), that data must NEVER be dropped or deleted without the user agreeing to
# it first. When a Bash command would wipe it, this hook returns permissionDecision
# "ask" so Claude Code pauses and hands the decision to the user (await user
# instructions) instead of running it. Everything non-destructive passes straight
# through.
#
# Deliberately NOT matched (these preserve the data): plain `dc dn` /
# `docker compose down` without a volume flag (a var/ bind mount survives),
# `dc up` / `--rebuild`, and `alembic upgrade` — the routine QA window is untouched.
# A destructive schema-dropping *migration* applied via `alembic upgrade` cannot be
# seen from the command line; that vector is covered by the SWE/QA prompt guardrails,
# not this hook.

set -uo pipefail
payload="$(cat)"

# Only Bash commands can carry these shapes; every other tool passes through.
tool="$(printf '%s' "${payload}" | jq -r '.tool_name // empty' 2>/dev/null)"
[ "${tool}" = "Bash" ] || exit 0

cmd="$(printf '%s' "${payload}" | jq -r '.tool_input.command // empty' 2>/dev/null)"
[ -n "${cmd}" ] || exit 0
low="$(printf '%s' "${cmd}" | tr '[:upper:]' '[:lower:]')"

reason=""

# 1. A stack teardown that also removes volumes — a RAW `docker compose down` with a
#    volume flag. The LETS `dc dn` wrapper is safe by construction (it hard-codes
#    `down --remove-orphans` and rejects unknown args, so it can never pass a volume
#    flag), so it is intentionally NOT matched here. The volume flag must sit in the
#    SAME command clause as the `down` keyword (up to the next ; | & separator), so an
#    incidental `grep -v` filtering log noise elsewhere on the line is not mistaken for
#    `docker compose down -v`.
teardown_clause="$(printf '%s' "${low}" | grep -oE 'docker[- ]?compose[^&|;]*down[^&|;]*')"
if [ -n "${teardown_clause}" ] \
	&& printf '%s' "${teardown_clause}" | grep -qE '(--volumes?\b|(^| )-v( |$))'; then
	reason="a stack teardown with volume removal would wipe stack volumes"
fi

# 2. Explicit docker volume deletion.
if printf '%s' "${low}" | grep -qE 'docker[[:space:]]+volume[[:space:]]+(rm|prune)'; then
	reason="'docker volume rm/prune' would delete stack data volumes"
fi

# 3. Deleting a database cluster bind mount under var/ (a *-pg / *-db data directory).
if printf '%s' "${low}" | grep -qE '\brm\b[^&|;]*var/[a-z0-9_-]*(pg|db)\b'; then
	reason="removing the var/ database bind mount would delete the project's data"
fi

# 4. Destructive SQL against the shared cluster. `truncate <ident>` is SQL; the
#    `truncate -s` coreutil (a `-` after the space) is not matched.
if printf '%s' "${low}" | grep -qE 'drop[[:space:]]+(database|schema)\b|truncate[[:space:]]+(table\b|only\b|"|[a-z])'; then
	reason="a DROP DATABASE/SCHEMA or TRUNCATE would destroy project data"
fi

# 5. Alembic rollback — a downgrade / re-baseline can drop schemas.
if printf '%s' "${low}" | grep -qE 'alembic[[:space:]][^&|;]*downgrade'; then
	reason="'alembic downgrade' can drop schemas on the shared cluster"
fi

[ -n "${reason}" ] || exit 0

jq -nc --arg r "PAUSED for consent: ${reason}. The project's shared database must never be dropped or deleted without explicit user consent — confirm with the user before running this, or take a non-destructive path." \
	'{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: $r}}'
