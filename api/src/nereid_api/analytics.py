"""Deterministic QC-filtered TEOS-10 profile metrics from native levels."""

from collections.abc import Sequence

import numpy as np  # pyright: ignore[reportMissingImports]

from nereid_api.models import (
    DerivedMetric,
    DerivedObservationSeries,
    ProfileSeries,
    QcPolicy,
)

_MINIMUM_LEVELS = 4
_MINIMUM_VERTICAL_SPAN_M = 50.0
_RESEARCH_LABEL = "Research: adjusted observations with adjusted QC=1"
_EXPLORATORY_LABEL = "Exploratory: adjusted observations with adjusted QC=1 or 2"


def _allowed_levels(profile: ProfileSeries, observations: DerivedObservationSeries, policy: QcPolicy, dependency: DerivedObservationSeries | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return native observations sorted by depth, retaining invalid-level adjacency."""
    allowed_qc = {1} if policy is QcPolicy.RESEARCH else {1, 2}
    depths = np.asarray(profile.depth_m, dtype=float)
    values = np.asarray(observations.values, dtype=float)
    errors = np.asarray(observations.adjusted_errors, dtype=float)
    variable_qc = np.asarray(observations.adjusted_qc, dtype=object)
    pressure_qc = np.asarray(profile.pressure_adjusted_qc, dtype=object)
    valid = np.isfinite(depths) & np.isfinite(values)
    valid &= np.fromiter((variable in allowed_qc and pressure in allowed_qc for variable, pressure in zip(variable_qc, pressure_qc, strict=True)), dtype=bool)
    if dependency is not None:
        dependency_qc = np.asarray(dependency.adjusted_qc, dtype=object)
        valid &= np.fromiter((item in allowed_qc for item in dependency_qc), dtype=bool)
    # A duplicate native depth is one level; an invalid duplicate makes that depth a break.
    order = np.argsort(depths, kind="stable")
    depths, values, errors, valid = depths[order], values[order], errors[order], valid[order]
    unique_depths, starts = np.unique(depths, return_index=True)
    selected = np.empty(len(starts), dtype=int)
    retained_valid = np.zeros(len(starts), dtype=bool)
    for index, start in enumerate(starts):
        stop = starts[index + 1] if index + 1 < len(starts) else len(depths)
        group_valid = valid[start:stop]
        retained_valid[index] = group_valid.all()
        selected[index] = start + np.argmax(group_valid) if retained_valid[index] else start
    return unique_depths, values[selected], errors[selected], retained_valid


def _valid_sorted_levels(depth_m: Sequence[float], values: Sequence[float], errors: Sequence[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    depths, measurements, measurement_errors = np.asarray(depth_m, dtype=float), np.asarray(values, dtype=float), np.asarray(errors, dtype=float)
    finite = np.isfinite(depths) & np.isfinite(measurements)
    depths, measurements, measurement_errors = depths[finite], measurements[finite], measurement_errors[finite]
    order = np.argsort(depths)
    depths, measurements, measurement_errors = depths[order], measurements[order], measurement_errors[order]
    depths, unique_indices = np.unique(depths, return_index=True)
    measurements, measurement_errors = measurements[unique_indices], measurement_errors[unique_indices]
    if len(depths) < _MINIMUM_LEVELS or depths[-1] - depths[0] < _MINIMUM_VERTICAL_SPAN_M:
        return None
    return depths, measurements, measurement_errors


def _quality_label(policy: QcPolicy) -> str:
    return _RESEARCH_LABEL if policy is QcPolicy.RESEARCH else _EXPLORATORY_LABEL


def _error_parameters(errors: np.ndarray) -> dict[str, float | int | None]:
    finite = errors[np.isfinite(errors) & (errors >= 0)]
    return {"adjusted_error_available_count": len(finite), "adjusted_error_max": float(finite.max()) if len(finite) else None}


def principal_thermocline(profile: ProfileSeries, policy: QcPolicy) -> DerivedMetric | None:
    """Use the strongest negative least-squares CT slope over contiguous native levels."""
    depths, temperatures, errors, valid = _allowed_levels(profile, profile.conservative_temperature, policy, profile.absolute_salinity)
    if valid.sum() < _MINIMUM_LEVELS or depths[valid][-1] - depths[valid][0] < _MINIMUM_VERTICAL_SPAN_M:
        return None
    candidates: list[tuple[float, int]] = []
    for index in range(len(depths) - 2):
        window_depths, window_temperatures = depths[index:index + 3], temperatures[index:index + 3]
        if not valid[index:index + 3].all() or window_depths[0] < 10 or window_depths[-1] > 500:
            continue
        slope = float(np.polyfit(window_depths, window_temperatures, 1)[0])
        if slope < 0:
            candidates.append((slope, index))
    if not candidates:
        return None
    slope, index = min(candidates)
    window_depths = depths[index:index + 3]
    return DerivedMetric(name="principal_thermocline", depth_m=float(window_depths.mean()), value=slope, units="°C m⁻¹", uncertainty_m=float((window_depths[-1] - window_depths[0]) / 2), algorithm="strongest_negative_three_level_regression", parameters={"window_levels": 3, "window_depths_m": window_depths.tolist(), "depth_range_m": [10, 500], "minimum_unique_levels": _MINIMUM_LEVELS, "minimum_vertical_span_m": _MINIMUM_VERTICAL_SPAN_M, "qc_policy": policy, **_error_parameters(errors[index:index + 3])}, quality_label=_quality_label(policy))


def strongest_salinity_gradient(profile: ProfileSeries, policy: QcPolicy) -> DerivedMetric | None:
    """Find the largest signed Absolute Salinity gradient allowed by QC policy."""
    depths, salinities, errors, valid = _allowed_levels(profile, profile.absolute_salinity, policy)
    levels = _valid_sorted_levels(depths[valid], salinities[valid], errors[valid])
    if levels is None:
        return None
    depths, salinities, errors = levels
    gradients = np.gradient(salinities, depths)
    index = int(np.argmax(np.abs(gradients)))
    spacing = [depths[index] - depths[index - 1]] if index else []
    if index < len(depths) - 1:
        spacing.append(depths[index + 1] - depths[index])
    return DerivedMetric(name="strongest_salinity_gradient", depth_m=float(depths[index]), value=float(gradients[index]), units="g kg⁻¹ m⁻¹", uncertainty_m=float(max(spacing) / 2), algorithm="strongest_absolute_native_salinity_gradient", parameters={"gradient": "numpy.gradient", "minimum_unique_levels": _MINIMUM_LEVELS, "minimum_vertical_span_m": _MINIMUM_VERTICAL_SPAN_M, "qc_policy": policy, **_error_parameters(errors)}, quality_label=_quality_label(policy))
