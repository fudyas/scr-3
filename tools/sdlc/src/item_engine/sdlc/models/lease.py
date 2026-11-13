from typing import Optional

from primitives.models.strict_model import StrictModel



class LeaseHolder(StrictModel):
    """The record of who holds a lease and since when."""

    # Names the lease
    name: str

    # Identifies the holder of the lease
    holder_id: str

    # Names the host of the holder
    host: str

    # Gives the process id of the holder
    pid: int

    # Gives the time the lease was taken
    acquired_at: str

    # Gives the time the lease was taken, in epoch seconds
    acquired_epoch: float


class LeaseAcquisition(StrictModel):
    """The result of a lease acquisition, including how long it waited."""

    # Holds the record of the new holder
    holder: LeaseHolder

    # Gives the time spent waiting for the lease, in seconds
    waited_seconds: float

    # Identifies the previous holder when the lease was taken over
    stolen_from: Optional[str] = None
