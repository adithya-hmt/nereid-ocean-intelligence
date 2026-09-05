from datetime import datetime, timezone

from nereid_api.analytics import principal_thermocline, strongest_salinity_gradient
from nereid_api.models import DerivedObservationSeries, ProfileSeries, QcPolicy

DEPTHS = [0, 10, 20, 30, 40, 60, 100]
CONSERVATIVE_TEMPERATURE = [28, 27.8, 27.5, 24, 20, 18, 15]
ABSOLUTE_SALINITY = [34, 34.1, 34.2, 34.6, 35.2, 35.3, 35.4]


def _observations(values, qc=1):
    return DerivedObservationSeries(
        values=values,
        adjusted_qc=[qc] * len(values),
        adjusted_errors=[0.01] * len(values),
    )


def _profile(temperature_qc=1, salinity_qc=1):
    return ProfileSeries(
        wmo="1234567",
        cycle=1,
        depth_m=DEPTHS,
        latitude=10,
        longitude=20,
        timestamp=datetime(2023, 3, 1, tzinfo=timezone.utc),
        data_mode="D",
        conservative_temperature=_observations(
            CONSERVATIVE_TEMPERATURE, temperature_qc
        ),
        absolute_salinity=_observations(ABSOLUTE_SALINITY, salinity_qc),
        pressure_adjusted_qc=[1] * len(DEPTHS),
        pressure_adjusted_errors=[0.1] * len(DEPTHS),
    )


def test_principal_thermocline_reference_cast():
    metric = principal_thermocline(_profile(), QcPolicy.RESEARCH)

    assert metric is not None
    assert abs(metric.depth_m - 30) <= 10
    assert metric.units
    assert metric.uncertainty_m > 0


def test_strongest_salinity_gradient_reference_cast():
    metric = strongest_salinity_gradient(_profile(), QcPolicy.RESEARCH)

    assert metric is not None
    assert abs(metric.depth_m - 40) <= 10
    assert metric.units
    assert metric.uncertainty_m > 0


def test_research_uses_adjusted_qc_one_and_excludes_qc_two():
    profile = _profile(temperature_qc=2, salinity_qc=2)

    assert principal_thermocline(profile, QcPolicy.RESEARCH) is None
    assert strongest_salinity_gradient(profile, QcPolicy.RESEARCH) is None


def test_qc_three_and_four_are_excluded_in_every_policy():
    profile = _profile(temperature_qc=3, salinity_qc=4)

    assert principal_thermocline(profile, QcPolicy.EXPLORATORY) is None
    assert strongest_salinity_gradient(profile, QcPolicy.EXPLORATORY) is None


def test_research_uses_adjusted_values_not_raw_values():
    profile = _profile()
    profile.conservative_temperature.values = [28, 27.8, 27.5, 24, 20, 18, 15]

    metric = principal_thermocline(profile, QcPolicy.RESEARCH)

    assert metric is not None
    assert abs(metric.depth_m - 30) <= 10


def test_exploratory_includes_qc_two_with_visible_label():
    profile = _profile(temperature_qc=2, salinity_qc=2)

    thermocline = principal_thermocline(profile, QcPolicy.EXPLORATORY)
    salinity_gradient = strongest_salinity_gradient(profile, QcPolicy.EXPLORATORY)

    assert thermocline is not None
    assert salinity_gradient is not None
    assert (
        thermocline.quality_label
        == "Exploratory: adjusted observations with adjusted QC=1 or 2"
    )
    assert (
        salinity_gradient.quality_label
        == "Exploratory: adjusted observations with adjusted QC=1 or 2"
    )


def test_analytics_reject_insufficient_qc_filtered_levels():
    profile = _profile()
    profile.conservative_temperature.adjusted_qc[-1] = 3
    profile.conservative_temperature.adjusted_qc[-2] = 3
    profile.conservative_temperature.adjusted_qc[-3] = 3

    assert principal_thermocline(profile, QcPolicy.RESEARCH) is None
