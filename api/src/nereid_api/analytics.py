"""Deterministic profile metrics calculated from native observation levels."""

from collections.abc import Sequence

import numpy as np

from nereid_api.models import DerivedMetric

_MINIMUM_LEVELS = 4
_MINIMUM_VERTICAL_SPAN_M = 50.0


def _valid_sorted_levels(
    depth_m: Sequence[float], values: Sequence[float]
) -> tuple[np.ndarray, np.ndarray] | None:
    """Return finite, depth-sorted unique observation pairs when coverage is adequate."""
    depths = np.asarray(depth_m, dtype=float)
    measurements = np.asarray(values, dtype=float)
    if depths.ndim != 1 or measurements.ndim != 1 or len(depths) != len(measurements):
        return None

    finite = np.isfinite(depths) & np.isfinite(measurements)
    depths, measurements = depths[finite], measurements[finite]
    order = np.argsort(depths)
    depths, measurements = depths[order], measurements[order]
    depths, unique_indices = np.unique(depths, return_index=True)
    measurements = measurements[unique_indices]

    if len(depths) < _MINIMUM_LEVELS or depths[-1] - depths[0] < _MINIMUM_VERTICAL_SPAN_M:
        return None
    return depths, measurements


def _uncertainty(depths: np.ndarray, index: int) -> float:
    adjacent_spacings: list[float] = []
    if index:
        adjacent_spacings.append(depths[index] - depths[index - 1])
    if index < len(depths) - 1:
        adjacent_spacings.append(depths[index + 1] - depths[index])
    return max(adjacent_spacings) / 2


def principal_thermocline(
    depth_m: Sequence[float], conservative_temperature: Sequence[float]
) -> DerivedMetric | None:
    """Find the strongest native negative Conservative Temperature gradient at 10–500 m."""
    levels = _valid_sorted_levels(depth_m, conservative_temperature)
    if levels is None:
        return None
    depths, temperatures = levels
    gradients = np.gradient(temperatures, depths)
    candidates = np.flatnonzero((depths >= 10) & (depths <= 500) & (gradients < 0))
    if not len(candidates):
        return None

    index = candidates[np.argmin(gradients[candidates])]
    return DerivedMetric(
        name="principal_thermocline",
        depth_m=float(depths[index]),
        value=float(gradients[index]),
        units="°C m⁻¹",
        uncertainty_m=float(_uncertainty(depths, int(index))),
        algorithm="strongest_negative_native_temperature_gradient",
        parameters={
            "gradient": "numpy.gradient",
            "depth_range_m": [10, 500],
            "minimum_unique_levels": _MINIMUM_LEVELS,
            "minimum_vertical_span_m": _MINIMUM_VERTICAL_SPAN_M,
        },
    )


def strongest_salinity_gradient(
    depth_m: Sequence[float], absolute_salinity: Sequence[float]
) -> DerivedMetric | None:
    """Find the largest-magnitude native Absolute Salinity gradient and preserve its sign."""
    levels = _valid_sorted_levels(depth_m, absolute_salinity)
    if levels is None:
        return None
    depths, salinities = levels
    gradients = np.gradient(salinities, depths)
    index = int(np.argmax(np.abs(gradients)))

    return DerivedMetric(
        name="strongest_salinity_gradient",
        depth_m=float(depths[index]),
        value=float(gradients[index]),
        units="g kg⁻¹ m⁻¹",
        uncertainty_m=float(_uncertainty(depths, index)),
        algorithm="strongest_absolute_native_salinity_gradient",
        parameters={
            "gradient": "numpy.gradient",
            "minimum_unique_levels": _MINIMUM_LEVELS,
            "minimum_vertical_span_m": _MINIMUM_VERTICAL_SPAN_M,
        },
    )
