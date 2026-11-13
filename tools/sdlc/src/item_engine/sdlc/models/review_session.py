from pathlib import Path
from typing import List, Optional

from pydantic import Field

from primitives.models.strict_model import StrictModel
from sdlc.models.artifact import ArtifactBinding


class ReviewSession(StrictModel):
    """The host-local review workspace and the exact trees selected for verification and approval."""

    # Identifies the item under review
    item_id: str

    # Locates the integration worktree
    worktree: Path

    # Names the integration branch
    branch: str

    # Names the branch that receives the promotion
    target_branch: str

    # Gives the commit that the review diff is taken against
    # After a target merge on integration, present moves it to the merged target commit
    base_commit: str

    # Gives the tip commit of the built item change
    built_tip: str

    # Names the review phase, such as SHOW, VERIFY, PROMOTE, or DONE
    phase: str = "SHOW"

    # Gives the tree hash of the frozen snapshot
    snapshot_tree: Optional[str] = None

    # Gives the commit of the frozen snapshot
    snapshot_commit: Optional[str] = None

    # Locates the detached worktree that holds the snapshot
    verification_worktree: Optional[Path] = None

    # Gives the tree hash that passed verification
    verified_tree: Optional[str] = None

    # Gives the tree hash that the user approved
    approved_tree: Optional[str] = None

    # Gives the target branch tip that the promotion builds on
    promotion_base: Optional[str] = None

    # Gives the commit prepared for promotion
    promotion_commit: Optional[str] = None

    # Locates the worktree that holds the promotion commit
    promotion_worktree: Optional[Path] = None

    # Tells whether the promotion merge tree differs from the verified snapshot and needs a system run
    promotion_system_required: bool = False

    merged_parents: List[str] = Field(
        default_factory=list,
        description="Extra parents that settle recorded, so a later settle after a present keeps them.",
    )

    # Binds the immutable artifact inputs to the source snapshot
    snapshot_artifacts: Optional[ArtifactBinding] = None

    # Gives the input digest that passed verification
    verified_artifacts: Optional[str] = None

    # Gives the input digest that the user approved
    approved_artifacts: Optional[str] = None

    # Pins the immutable QA result for the source and input pair
    qa_artifacts: Optional[ArtifactBinding] = None
