"""vendor 适配层公共基座。仅依赖标准库，供各适配器复用。"""

from .result import Check, emit, run
from .paths import VENDOR_ROOT, repo_dir, venv_python, node_exe
from .coords import (
    MAP_SPACES,
    MINIMAP_SIZES,
    AffineMap,
    calibrate,
    normalize_rect,
    scale_from_minimap,
    solve_affine,
)

__all__ = [
    "Check",
    "emit",
    "run",
    "VENDOR_ROOT",
    "repo_dir",
    "venv_python",
    "node_exe",
    "MAP_SPACES",
    "MINIMAP_SIZES",
    "AffineMap",
    "calibrate",
    "solve_affine",
    "normalize_rect",
    "scale_from_minimap",
]
