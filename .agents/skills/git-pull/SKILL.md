---
name: git-pull
description: >-
  Use this skill to pull a git branch over SSH using the private key (admin/github) and SSH host config (admin/config) under the repo's admin/ folder. Pulls the currently checked-out branch by default, or a branch named as the argument — switching to that branch first. Pull-only and non-destructive: never pushes, forces, resets, stashes, or writes git config; a dirty tree or a diverged branch stops the skill with a report instead of a workaround. Do NOT auto-invoke; only run when explicitly called with $git-pull.
---

# Git Pull over SSH (`$git-pull`)

Pull a branch from `origin` over SSH, authenticating with the private key (`admin/github`) and resolving the `origin` host alias through the SSH host config (`admin/config`), both kept under the repo's `admin/` folder. By default pull the **currently checked-out** branch; if the user names a branch, switch to it first and pull that one. This skill is **pull-only**: it never pushes, forces, resets, stashes, or writes any git config.

## Arguments

Invocation arguments are optional. The branch to pull (e.g. `master`, `release/v0.2-otg-2`). If empty, the target is the current branch (`git rev-parse --abbrev-ref HEAD`).

## Core constraint

**Pull only. Change nothing you were not asked to.** Never run `git push`, `git reset`, `git stash`, `git rebase`, `git commit`, or any `--force`. Never persist SSH config with `git config core.sshCommand` — pass the key (`-i admin/github`) and the repo's SSH host config (`-F admin/config`, which maps the `origin` alias `fudya.github.com` onto `github.com`) through the `GIT_SSH_COMMAND` environment variable on the command itself. Never touch the private key's contents; the only permitted write to it is tightening its mode to `600` when it is too open (SSH refuses a group/world-readable key). If the pull cannot fast-forward or the working tree is dirty, **stop and report** — do not stash, reset, or force a resolution.

## Procedure

1. **Locate the key and check its mode.** Resolve from the repo root so the skill works from any subdirectory. SSH rejects an over-permissive key, so tighten to `600` only when needed — never loosen:
   ```bash
   repo="$(git rev-parse --show-toplevel)"
   key="$repo/admin/github"
   config="$repo/admin/config"
   [ -f "$key" ] || { echo "no SSH key at $key — cannot pull over SSH"; exit 1; }
   [ -f "$config" ] || { echo "no SSH host config at $config — cannot resolve the origin host alias"; exit 1; }
   perm="$(stat -c '%a' "$key")"
   case "$perm" in 600|400) ;; *) chmod 600 "$key"; echo "tightened key mode $perm -> 600" ;; esac
   ```

2. **Confirm the remote is SSH.** The key only helps an SSH remote. If `origin` is HTTPS, stop and tell the user — the key does not apply:
   ```bash
   git --no-pager remote -v | grep '^origin'
   ```

3. **Resolve the target branch** — the argument, or the current branch when no argument is given:
   ```bash
   current="$(git --no-pager rev-parse --abbrev-ref HEAD)"
   branch="<requested-branch-or-$current>" # substitute the branch supplied by the user
   echo "target=$branch  current=$current"
   ```

4. **Switch to the target branch if it is not the current one.** Fetch its ref first (over SSH) so a branch that exists only on the remote can be checked out, then switch. If the switch fails because the working tree is dirty, **stop and report** — never stash or discard:
   ```bash
   if [ "$branch" != "$current" ]; then
     GIT_SSH_COMMAND="ssh -F $config -i $key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
       git fetch origin "$branch"
     git switch "$branch" 2>/dev/null || git switch -c "$branch" --track "origin/$branch"
   fi
   ```

5. **Pull the branch over SSH.** Set the key inline via `GIT_SSH_COMMAND` (do not persist it). `accept-new` lets the first connection record `github.com` in `known_hosts` without a prompt; it will not silently accept a *changed* host key:
   ```bash
   GIT_SSH_COMMAND="ssh -i $key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
     git pull origin "$branch"
   ```

6. **Report the outcome** in plain words: already up to date, fast-forwarded (with the new short hash), or a real merge. If the pull failed — non-fast-forward divergence, merge conflicts, or a dirty tree blocking it — say exactly which, show git's message, and stop. Do not attempt to resolve it by resetting, stashing, or forcing.

## Rules

- Always use `--no-pager` for read commands.
- **Pull only.** Never push, reset, stash, rebase, commit, amend, or use any `--force`.
- Pass the key (`-i admin/github`) and the host config (`-F admin/config`) through **`GIT_SSH_COMMAND`** inline; never write `git config core.sshCommand` or any persistent config.
- Never read, copy, print, or modify the key's contents. The one allowed write is `chmod 600` when the mode is too open.
- Resolve the key and config from the **repo root** (`admin/github`, `admin/config`), not a relative guess.
- On any failure (dirty tree, divergence, conflict, missing branch, HTTPS remote), **stop and report** — never work around it destructively.
- Do not auto-invoke; run only on explicit `$git-pull`.

## Example output

```
Pulled release/v0.2-otg-2 over SSH using admin/github.

- Fast-forwarded 04850bc -> a1b2c3d (7 commits).
- Local uncommitted changes were left untouched.
```
