from nereid_api.analytics import principal_thermocline, strongest_salinity_gradient


DEPTHS = [0, 10, 20, 30, 40, 60, 100]
CONSERVATIVE_TEMPERATURE = [28, 27.8, 27.5, 24, 20, 18, 15]
ABSOLUTE_SALINITY = [34, 34.1, 34.2, 34.6, 35.2, 35.3, 35.4]


def test_principal_thermocline_reference_cast():
    metric = principal_thermocline(DEPTHS, CONSERVATIVE_TEMPERATURE)

    assert metric is not None
    assert abs(metric.depth_m - 30) <= 10
    assert metric.units
    assert metric.uncertainty_m > 0


def test_strongest_salinity_gradient_reference_cast():
    metric = strongest_salinity_gradient(DEPTHS, ABSOLUTE_SALINITY)

    assert metric is not None
    assert abs(metric.depth_m - 40) <= 10
    assert metric.units
    assert metric.uncertainty_m > 0


def test_analytics_reject_insufficient_valid_levels():
    assert principal_thermocline([0, 20, 60], [28, 25, 20]) is None
    assert strongest_salinity_gradient([0, 20, 60], [34, 34.5, 35]) is None
