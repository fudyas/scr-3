---
name: git-push
description: >-
  Use this skill to push a git branch to origin over SSH using the private key (admin/github) and SSH host config (admin/config) under the repo's admin/ folder. Pushes the currently checked-out branch by default, or a branch named as the argument. ALWAYS asks the user for explicit consent before pushing — it previews the outgoing commits and pushes only after the user approves. Non-destructive: never force-pushes, never pushes tags or other remotes, and a rejected non-fast-forward push stops with a report instead of forcing. Do NOT auto-invoke; only run when explicitly called with $git-push.
---

# Git Push over SSH, with consent (`$git-push`)

Push a branch to `origin` over SSH, authenticating with the private key (`admin/github`) and resolving the `origin` host alias through the SSH host config (`admin/config`), both kept under the repo's `admin/` folder. By default push the **currently checked-out** branch; if the user names a branch, push that local branch. This skill **never pushes without explicit consent** and is **non-destructive**: it never force-pushes, never pushes tags, and never touches a remote other than `origin`.

## Arguments

Invocation arguments are optional. The branch to push (e.g. `master`, `release/v0.2-otg-2`). If empty, the target is the current branch (`git rev-parse --abbrev-ref HEAD`).

## Core constraint

**Get consent, then push — nothing more.** The push happens **only after** the user explicitly approves it through the `AskUserQuestion` gate in step 6; never push before that approval. Never run any `--force`, `--force-with-lease`, `git push --tags`, `--mirror`, `--delete`, or a push to any remote but `origin`. Never persist SSH config with `git config core.sshCommand` — pass the key (`-i admin/github`) and the repo's SSH host config (`-F admin/config`, which maps the `origin` alias `fudya.github.com` onto `github.com`) through the `GIT_SSH_COMMAND` environment variable on the command itself. Never read, print, or modify the private key's contents; the only permitted write to it is tightening its mode to `600` when it is too open (SSH refuses a group/world-readable key). If the push is rejected as non-fast-forward, **stop and report** — do not force it.

## Procedure

1. **Locate the key and check its mode.** Resolve from the repo root so the skill works from any subdirectory. SSH rejects an over-permissive key, so tighten to `600` only when needed — never loosen:
   ```bash
   repo="$(git rev-parse --show-toplevel)"
   key="$repo/admin/github"
   config="$repo/admin/config"
   [ -f "$key" ] || { echo "no SSH key at $key — cannot push over SSH"; exit 1; }
   [ -f "$config" ] || { echo "no SSH host config at $config — cannot resolve the origin host alias"; exit 1; }
   perm="$(stat -c '%a' "$key")"
   case "$perm" in 600|400) ;; *) chmod 600 "$key"; echo "tightened key mode $perm -> 600" ;; esac
   ```

2. **Confirm the remote is SSH.** The key only helps an SSH remote. If `origin` is HTTPS, stop and tell the user — the key does not apply:
   ```bash
   git --no-pager remote -v | grep '^origin'
   ```

3. **Resolve the target branch** — the argument, or the current branch when no argument is given — and confirm it exists locally:
   ```bash
   current="$(git --no-pager rev-parse --abbrev-ref HEAD)"
   branch="<requested-branch-or-$current>" # substitute the branch supplied by the user
   git --no-pager rev-parse --verify --quiet "refs/heads/$branch" >/dev/null \
     || { echo "no local branch '$branch' to push"; exit 1; }
   echo "target=$branch  current=$current"
   ```

4. **Refresh the remote's view of that branch** (read-only, over SSH) so the outgoing preview and the fast-forward check are accurate:
   ```bash
   GIT_SSH_COMMAND="ssh -F $config -i $key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
     git fetch origin "$branch"
   ```

5. **Compute what would be pushed and guard the edge cases.** Compare the local branch against the just-fetched remote ref:
   ```bash
   remote_ref="refs/remotes/origin/$branch"
   if git --no-pager rev-parse --verify --quiet "$remote_ref" >/dev/null; then
     ahead="$(git --no-pager rev-list --count "$remote_ref".."$branch")"
     behind="$(git --no-pager rev-list --count "$branch".."$remote_ref")"
   else
     ahead="$(git --no-pager rev-list --count "$branch")"; behind=0   # new branch on remote
   fi
   echo "ahead=$ahead behind=$behind"
   git --no-pager log --oneline --no-merges "$remote_ref".."$branch" 2>/dev/null \
     || git --no-pager log --oneline --no-merges "$branch"
   ```
   - If `ahead` is `0`, there is nothing to push. **Stop** and tell the user the branch is already up to date on `origin`.
   - If `behind` is greater than `0`, the push would be **non-fast-forward** (the remote has commits the local branch lacks). A plain push will be rejected. **Stop and report** — tell the user to `$git-pull` first; never force.

6. **Ask for explicit consent — this gate is mandatory.** Present the exact push: the branch, the remote (`origin`), the commit count, and the outgoing commit subjects from step 5. Then call `AskUserQuestion` with options **Push** (recommended) and **Cancel**. Push **only** if the user picks Push. On Cancel — or any other answer — do nothing and stop.

7. **Push over SSH** (only after approval). Set the key inline via `GIT_SSH_COMMAND`; no force, no tags, `origin` only:
   ```bash
   GIT_SSH_COMMAND="ssh -F $config -i $key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
     git push origin "$branch"
   ```

8. **Report the outcome** in plain words: pushed (with the `old..new` range git prints), or already up to date. If the push was rejected despite the checks — a race where the remote advanced between step 4 and step 7 — show git's message and stop; do not retry with force.

## Rules

- Always use `--no-pager` for read commands.
- **Never push without the explicit `AskUserQuestion` approval** from step 6.
- **Push only, non-destructive.** Never `--force`, `--force-with-lease`, `--tags`, `--mirror`, `--delete`, or push any remote but `origin`.
- Pass the key (`-i admin/github`) and the host config (`-F admin/config`) through **`GIT_SSH_COMMAND`** inline; never write `git config core.sshCommand` or any persistent config.
- Never read, copy, print, or modify the key's contents. The one allowed write is `chmod 600` when the mode is too open.
- Resolve the key and config from the **repo root** (`admin/github`, `admin/config`), not a relative guess.
- Nothing to push (already up to date) or a non-fast-forward divergence: **stop and report** — never force, and point the user at `$git-pull` for divergence.
- Do not auto-invoke; run only on explicit `$git-push`.

## Example consent prompt

```
About to push to origin over SSH (admin/github):

  branch:  release/v0.2-otg-2  ->  origin/release/v0.2-otg-2
  commits: 2 ahead, 0 behind (fast-forward)

  - fix(auth): gate spec/read behind session-write-ready
  - docs(sdlc): land BLG-0778 DONE

Approve the push?   [ Push ]  [ Cancel ]
```

## Example output

```
Pushed release/v0.2-otg-2 to origin over SSH using admin/github.

- 04850bc..a1b2c3d  (2 commits, fast-forward).
```
