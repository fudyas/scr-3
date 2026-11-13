from pathlib import Path

from primitives.models.strict_model import StrictModel



class WorktreeInfo(StrictModel):
    """One item worktree and the branch it checks out."""

    # Locates the worktree directory
    path: Path

    # Names the branch that the worktree checks out
    branch: str

    # Tells whether the call created the worktree
    created: bool


class PresentedChange(StrictModel):
    """The item change that the integration worktree shows as staged changes for review."""

    # Gives the commit where the item branch left the target branch
    merge_base: str

    # Gives the tip commit of the built item change
    built_tip: str

    # Counts the files that the change shows as staged
    file_count: int

    # Tells whether the call created the staged presentation
    created: bool
