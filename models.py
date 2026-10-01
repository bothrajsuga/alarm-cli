from dataclasses import dataclass
from datetime import datetime


@dataclass
class Alarm:
    id: int
    fire_at: datetime
    label: str = ""
    fired: bool = False
    cancelled: bool = False
