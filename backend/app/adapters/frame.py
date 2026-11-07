from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict

import numpy as np


@dataclass
class Frame:
    image: np.ndarray
    meta: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    @property
    def width(self) -> int:
        return int(self.image.shape[1])

    @property
    def height(self) -> int:
        return int(self.image.shape[0])

    def summary(self) -> Dict[str, Any]:
        return {"width": self.width, "height": self.height, **self.meta}
