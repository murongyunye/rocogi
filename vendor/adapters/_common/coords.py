"""坐标系适配：6144×5888 与 8192×8192 之间必须用 3 点仿射，禁止只做缩放。

同时提供小地图尺寸与 DPI 归一化工具，尺寸全部来自配置表，不写死在业务代码里。
"""

from __future__ import annotations

from dataclasses import dataclass

MAP_SPACES: dict[str, tuple[int, int]] = {
    "main_6144x5888": (6144, 5888),
    "world_8192x8192": (8192, 8192),
}

# 已知小地图尺寸（150×150 / 162×162 / 255×235），允许配置覆盖。
MINIMAP_SIZES: dict[str, tuple[int, int]] = {
    "compact_150": (150, 150),
    "standard_162": (162, 162),
    "rounded_255x235": (255, 235),
}


class AffineError(ValueError):
    pass


def _solve_linear(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """高斯消元求 6×6 线性方程，用于解仿射参数。"""
    n = len(rhs)
    a = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-9:
            raise AffineError("三点共线或退化，无法求解仿射变换")
        a[col], a[pivot] = a[pivot], a[col]
        inv = 1.0 / a[col][col]
        for j in range(col, n + 1):
            a[col][j] *= inv
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col]
            if factor:
                for j in range(col, n + 1):
                    a[r][j] -= factor * a[col][j]
    return [a[i][n] for i in range(n)]


def solve_affine(
    src: list[tuple[float, float]],
    dst: list[tuple[float, float]],
) -> tuple[float, float, float, float, float, float]:
    """由 3 组对应点求 x'=a*x+b*y+c, y'=d*x+e*y+f。"""
    if len(src) != 3 or len(dst) != 3:
        raise AffineError("必须提供且仅提供 3 组对应点")
    rows: list[list[float]] = []
    rhs: list[float] = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([x, y, 1.0, 0.0, 0.0, 0.0])
        rhs.append(u)
        rows.append([0.0, 0.0, 0.0, x, y, 1.0])
        rhs.append(v)
    a, b, c, d, e, f = _solve_linear(rows, rhs)
    return a, b, c, d, e, f


@dataclass(frozen=True)
class AffineMap:
    params: tuple[float, float, float, float, float, float]
    source: str
    target: str

    def apply(self, x: float, y: float) -> tuple[float, float]:
        a, b, c, d, e, f = self.params
        return a * x + b * y + c, d * x + e * y + f

    def residual(self, src: list[tuple[float, float]], dst: list[tuple[float, float]]) -> float:
        return max(
            max(abs(px - ux), abs(py - uy))
            for (px, py), (ux, uy) in zip(
                (self.apply(x, y) for x, y in src), dst
            )
        )

    def as_dict(self) -> dict[str, object]:
        keys = ("a", "b", "c", "d", "e", "f")
        return {
            "source": self.source,
            "target": self.target,
            "params": dict(zip(keys, self.params)),
        }


def calibrate(source: str, target: str, pairs: list[tuple[tuple[float, float], tuple[float, float]]]) -> AffineMap:
    """三点标定入口；pairs = [((sx,sy),(tx,ty)) × 3]。"""
    src = [p[0] for p in pairs]
    dst = [p[1] for p in pairs]
    return AffineMap(solve_affine(src, dst), source, target)


def normalize_rect(
    rect: tuple[int, int, int, int],
    capture_size: tuple[int, int],
    baseline_size: tuple[int, int] = (1920, 1080),
) -> tuple[int, int, int, int]:
    """把任意分辨率下的像素 ROI 归一化到基准分辨率（DPI/分辨率归一化）。"""
    left, top, width, height = rect
    cw, ch = capture_size
    bw, bh = baseline_size
    sx, sy = bw / cw, bh / ch
    return round(left * sx), round(top * sy), round(width * sx), round(height * sy)


def scale_from_minimap(sample_size: tuple[int, int], reference_size: tuple[int, int]) -> float:
    """小地图尺寸不一致时的等比缩放系数（仅用于同一空间的显示尺寸对齐）。"""
    return min(sample_size[0] / reference_size[0], sample_size[1] / reference_size[1])
