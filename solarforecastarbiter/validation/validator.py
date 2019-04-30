# -*- coding: utf-8 -*-
"""
Created on Fri Feb 15 14:08:20 2019

@author: cwhanse
"""

import numpy as np
import pandas as pd
from pvlib.tools import cosd
from pvlib.irradiance import clearsky_index


QCRAD_LIMITS = {'ghi_ub': {'mult': 1.5, 'exp': 1.2, 'min': 100},
                'dhi_ub': {'mult': 0.95, 'exp': 1.2, 'min': 50},
                'dni_ub': {'mult': 1.0, 'exp': 0.0, 'min': 0},
                'ghi_lb': -4, 'dhi_lb': -4, 'dni_lb': -4}

QCRAD_CONSISTENCY = {
    'ghi_ratio':
        {'low_zenith':
            {'zenith_bounds': [0.0, 75], 'ghi_bounds': [50, np.Inf],
             'ratio_bounds': [0.92, 1.08]},
         'high_zenith':
            {'zenith_bounds': [75, 93], 'ghi_bounds': [50, np.Inf],
             'ratio_bounds': [0.85, 1.15]}},
    'dhi_ratio':
        {'low_zenith':
            {'zenith_bounds': [0.0, 75], 'ghi_bounds': [50, np.Inf],
             'ratio_bounds': [0.0, 1.05]},
         'high_zenith':
            {'zenith_bounds': [75, 93], 'ghi_bounds': [50, np.Inf],
             'ratio_bounds': [0.0, 1.10]}}}


def _check_limits(val, lb=None, ub=None, lb_ge=False, ub_le=False):
    """ Returns True where lb < (or <=) val < (or <=) ub
    """
    if lb_ge:
        lb_op = np.greater_equal
    else:
        lb_op = np.greater
    if ub_le:
        ub_op = np.less_equal
    else:
        ub_op = np.less

    if (lb is not None) & (ub is not None):
        return lb_op(val, lb) & ub_op(val, ub)
    elif lb is not None:
        return lb_op(val, lb)
    elif ub is not None:
        return ub_op(val, ub)
    else:
        raise ValueError('must provide either upper or lower bound')


def _QCRad_ub(dni_extra, sza, lim):
    return lim['mult'] * dni_extra * cosd(sza)**lim['exp'] + lim['min']


def check_ghi_limits_QCRad(ghi, solar_zenith, dni_extra, limits=None):
    """
    Tests for physical limits on GHI using the QCRad criteria.

    Test passes if a value > lower bound and value < upper bound. Lower bounds
    are constant for all tests. Upper bounds are calculated as

    .. math::
        ub = min + mult * dni_extra * cos( solar_zenith)^exp

    Parameters:
    -----------
    ghi : Series
        Global horizontal irradiance in W/m^2
    solar_zenith : Series
        Solar zenith angle in degrees
    dni_extra : Series
        Extraterrestrial normal irradiance in W/m^2
    limits : dict, default QCRAD_LIMITS
        for keys 'ghi_ub', 'dhi_ub', 'dni_ub', value is a dict with
        keys {'mult', 'exp', 'min'}. For keys 'ghi_lb', 'dhi_lb', 'dni_lb',
        value is a float.

    Returns:
    --------
    ghi_limit_flag : Series
        True if value passes physically-possible test
    """
    if not limits:
        limits = QCRAD_LIMITS

    ghi_ub = _QCRad_ub(dni_extra, solar_zenith, limits['ghi_ub'])

    ghi_limit_flag = _check_limits(ghi, limits['ghi_lb'], ghi_ub)
    ghi_limit_flag.name = 'ghi_limit_flag'

    return ghi_limit_flag


def check_dhi_limits_QCRad(dhi, solar_zenith, dni_extra, limits=None):
    """
    Tests for physical limits on DHI using the QCRad criteria.

    Test passes if a value > lower bound and value < upper bound. Lower bounds
    are constant for all tests. Upper bounds are calculated as

    .. math::
        ub = min + mult * dni_extra * cos( solar_zenith)^exp

    Parameters:
    -----------
    ghi : Series
        Diffuse horizontal irradiance in W/m^2
    solar_zenith : Series
        Solar zenith angle in degrees
    dni_extra : Series
        Extraterrestrial normal irradiance in W/m^2
    limits : dict, default QCRAD_LIMITS
        for keys 'ghi_ub', 'dhi_ub', 'dni_ub', value is a dict with
        keys {'mult', 'exp', 'min'}. For keys 'ghi_lb', 'dhi_lb', 'dni_lb',
        value is a float.

    Returns:
    --------
    ghi_limit_flag : Series
        True if value passes physically-possible test
    """
    if not limits:
        limits = QCRAD_LIMITS

    dhi_ub = _QCRad_ub(dni_extra, solar_zenith, limits['dhi_ub'])

    dhi_limit_flag = _check_limits(dhi, limits['dhi_lb'], dhi_ub)
    dhi_limit_flag.name = 'dhi_limit_flag'

    return dhi_limit_flag


def check_dni_limits_QCRad(dni, solar_zenith, dni_extra, limits=None):
    """
    Tests for physical limits on DNI using the QCRad criteria.

    Test passes if a value > lower bound and value < upper bound. Lower bounds
    are constant for all tests. Upper bounds are calculated as

    .. math::
        ub = min + mult * dni_extra * cos( solar_zenith)^exp

    Parameters:
    -----------
    dni : Series
        Direct normal irradiance in W/m^2
    solar_zenith : Series
        Solar zenith angle in degrees
    dni_extra : Series
        Extraterrestrial normal irradiance in W/m^2
    limits : dict, default QCRAD_LIMITS
        for keys 'ghi_ub', 'dhi_ub', 'dni_ub', value is a dict with
        keys {'mult', 'exp', 'min'}. For keys 'ghi_lb', 'dhi_lb', 'dni_lb',
        value is a float.

    Returns:
    --------
    dni_limit_flag : Series
        True if value passes physically-possible test
    """
    if not limits:
        limits = QCRAD_LIMITS

    dni_ub = _QCRad_ub(dni_extra, solar_zenith, limits['dni_ub'])

    dni_limit_flag = _check_limits(dni, limits['dni_lb'], dni_ub)
    dni_limit_flag.name = 'dni_limit_flag'

    return dni_limit_flag


def check_irradiance_limits_QCRad(solar_zenith, dni_extra, ghi=None, dhi=None,
                                  dni=None, limits=None):
    """
    Tests for physical limits on GHI, DHI or DNI using the QCRad criteria.

    Test passes if a value > lower bound and value < upper bound. Lower bounds
    are constant for all tests. Upper bounds are calculated as

    .. math::
        ub = min + mult * dni_extra * cos( solar_zenith)^exp

    Parameters:
    -----------
    solar_zenith : Series
        Solar zenith angle in degrees
    dni_extra : Series
        Extraterrestrial normal irradiance in W/m^2
    ghi : Series or None, default None
        Global horizontal irradiance in W/m^2
    dhi : Series or None, default None
        Diffuse horizontal irradiance in W/m^2
    dni : Series or None, default None
        Direct normal irradiance in W/m^2
    limits : dict, default QCRAD_LIMITS
        for keys 'ghi_ub', 'dhi_ub', 'dni_ub', value is a dict with
        keys {'mult', 'exp', 'min'}. For keys 'ghi_lb', 'dhi_lb', 'dni_lb',
        value is a float.

    Returns:
    --------
    ghi_limit_flag : Series or None, default None
        True if value passes physically-possible test
    dhi_limit_flag : Series or None, default None
    dhi_limit_flag : Series or None, default None
    """
    if not limits:
        limits = QCRAD_LIMITS

    if ghi is not None:
        ghi_limit_flag = check_ghi_limits_QCRad(ghi, solar_zenith, dni_extra,
                                                limits=None)
    else:
        ghi_limit_flag = None

    if dhi is not None:
        dhi_limit_flag = check_dhi_limits_QCRad(dhi, solar_zenith, dni_extra,
                                                limits=None)
    else:
        dhi_limit_flag = None

    if dni is not None:
        dni_limit_flag = check_dni_limits_QCRad(dni, solar_zenith, dni_extra,
                                                limits=None)
    else:
        dni_limit_flag = None

    return ghi_limit_flag, dhi_limit_flag, dni_limit_flag


def _get_bounds(bounds):
    return (bounds['ghi_bounds'][0], bounds['ghi_bounds'][1],
            bounds['zenith_bounds'][0], bounds['zenith_bounds'][1],
            bounds['ratio_bounds'][0], bounds['ratio_bounds'][1])


def _check_irrad_ratio(ratio, ghi, sza, bounds):
    # unpack bounds dict
    ghi_lb, ghi_ub, sza_lb, sza_ub, ratio_lb, ratio_ub = _get_bounds(bounds)
    # for zenith set lb_ge to handle edge cases, e.g., zenith=0
    return ((_check_limits(sza, lb=sza_lb, ub=sza_ub, lb_ge=True)) &
            (_check_limits(ghi, lb=ghi_lb, ub=ghi_ub)) &
            (_check_limits(ratio, lb=ratio_lb, ub=ratio_ub)))


def check_irradiance_consistency_QCRad(ghi, solar_zenith, dni_extra, dhi, dni,
                                       param=None):
    """
    Checks consistency of GHI, DHI and DNI.

    Parameters:
    -----------
    ghi : Series
        Global horizontal irradiance in W/m^2
    solar_zenith : Series
        Solar zenith angle in degrees
    dni_extra : Series
        Extraterrestrial normal irradiance in W/m^2
    dhi : Series
        Diffuse horizontal irradiance in W/m^2
    dni : Series
        Direct normal irradiance in W/m^2
    param : dict
        keys are 'ghi_ratio' and 'dhi_ratio'. For each key, value is a dict
        with keys 'high_zenith' and 'low_zenith'; for each of these keys,
        value is a dict with keys 'zenith_bounds', 'ghi_bounds', and
        'ratio_bounds' and value is an ordered pair [lower, upper]
        of float.

    Returns:
    --------
    consistent_components : Series
        True if ghi, dhi and dni components are consistent.
    diffuse_ratio_limit : Series
        True if diffuse to ghi ratio passes limit test.
    """

    if not param:
        param = QCRAD_CONSISTENCY

    # sum of components
    component_sum = dni * cosd(solar_zenith) + dhi
    ghi_ratio = ghi / component_sum
    dhi_ratio = dhi / ghi

    bounds = param['ghi_ratio']
    consistent_components = (
        _check_irrad_ratio(ratio=ghi_ratio, ghi=component_sum,
                           sza=solar_zenith, bounds=bounds['high_zenith']) |
        _check_irrad_ratio(ratio=ghi_ratio, ghi=component_sum,
                           sza=solar_zenith, bounds=bounds['low_zenith']))
    consistent_components.name = 'consistent_components'

    bounds = param['dhi_ratio']
    diffuse_ratio_limit = (
        _check_irrad_ratio(ratio=dhi_ratio, ghi=ghi, sza=solar_zenith,
                           bounds=bounds['high_zenith']) |
        _check_irrad_ratio(ratio=dhi_ratio, ghi=ghi, sza=solar_zenith,
                           bounds=bounds['low_zenith']))
    diffuse_ratio_limit.name = 'diffuse_ratio_limit'

    return consistent_components, diffuse_ratio_limit


def check_temperature_limits(temp_air, temp_limits=(-10., 50.)):
    """ Checks for extreme temperatures.

    Parameters:
    -----------
    temp_air : Series
        Air temperature in Celsius
    temp_limits : tuple, default (-10, 50)
        (lower bound, upper bound) for temperature.

    Returns:
    --------
    extreme_temp_flag : Series
        True if temp_air > lower bound and temp_air < upper bound.
    """

    extreme_temp_flag = _check_limits(temp_air, lb=temp_limits[0],
                                      ub=temp_limits[1])
    extreme_temp_flag.name = 'extreme_temp_flag'
    return extreme_temp_flag


def check_wind_limits(wind_speed, wind_limits=(0., 60.)):
    """ Checks for extreme wind speeds.

    Parameters:
    -----------
    wind_speed : Series
        Wind speed m/s
    wind_limits : tuple, default (0, 60)
        (lower bound, upper bound) for wind speed.

    Returns:
    --------
    extreme_wind_flag : DataFrame
        True if wind_speed > lower bound and wind_speed < upper bound.
    """
    extreme_wind_flag = _check_limits(wind_speed, lb=wind_limits[0],
                                      ub=wind_limits[1])
    extreme_wind_flag.name = 'extreme_wind_flag'
    return extreme_wind_flag


def check_rh_limits(rh, rh_limits=(0, 100)):
    """ Checks for extreme relative humidity.

    Parameters:
    -----------
    rh : Series
        Relative humidity in %
    rh_limits : tuple, default (0, 100)
        (lower bound, upper bound) for relative humidity

    Returns:
    --------
    flags : DataFrame
        True if rh >= lower bound and rh <= upper bound.
    """

    flags = pd.Series(index=rh.index, data=None, name='extreme_rh_flag')
    flags = _check_limits(rh, lb=rh_limits[0], ub=rh_limits[1], lb_ge=True,
                          ub_le=True)
    return flags


def get_solarposition(location, times, **kwargs):
    """ Calculates solar position.

    Wraps pvlib.location.Location.get_solarposition.

    Parameters:
    -----------
    location : pvlib.Location
    times : DatetimeIndex
    optional kwargs include
        pressure : float, Pa
        temperature : float, degrees C
        method : str, default 'nrel_numpy'
            Other values are 'nrel_c', 'nrel_numba', 'pyephem', and 'ephemeris'
    Other kwargs are passed to the underlying solar position function
    specified by method kwarg.

    Returns
    -------
    solar_position : DataFrame
        Columns depend on the ``method`` kwarg, but always include
        ``zenith`` and ``azimuth``.
    """
    return location.get_solarposition(times, **kwargs)


def get_clearsky(location, times, **kwargs):
    """ Calculates clear-sky GHI, DNI, DHI.

    Wraps pvlib.location.Location.get_clearsky.

    Parameters:
    -----------
    location : pvlib.Location
    times : DatetimeIndex
    optional kwargs include
        solar_position : None or DataFrame, default None
        dni_extra: None or numeric, default None
        model: str, default 'ineichen'
            Other values are 'haurwitz', 'simplified_solis'.
    Other kwargs are passed to the underlying solar position function
    specified by model kwarg.

    Returns
    -------
    clearsky : DataFrame
        Column names are: ``ghi, dni, dhi``.
    """
    return location.get_clearsky(times, **kwargs)


def check_ghi_clearsky(irrad, clearsky=None, location=None, kt_max=1.1):
    """
    Flags GHI values greater than clearsky values.

    If clearsky is not provided, a Location is required and clear-sky
    irradiance is calculated by pvlib.location.Location.get_clearsky.

    Parameters:
    -----------
    irrad : DataFrame
        ghi : float
            Global horizontal irradiance in W/m^2
    clearsky : DataFrame, default None
        ghi : float
            Global horizontal irradiance in W/m^2
    location : Location, default None
        instance of pvlib.location.Location
    kt_max : float
        maximum clearness index that defines when ghi exceeds clear-sky value.

    Returns:
    --------
    flags : DataFrame
        ghi_clearsky : boolean
            True if ghi is less than or equal to clear sky value.
    """
    times = irrad.index

    if clearsky is None and location is None:
        raise ValueError("Either clearsky or location is required")
    elif clearsky is None and location is not None:
        clearsky = get_clearsky(location, times)

    flags = pd.DataFrame(index=times, data=None, columns=['ghi_clearsky'])
    kt = clearsky_index(irrad['ghi'], clearsky['ghi'],
                        max_clearsky_index=np.Inf)
    flags['ghi_clearsky'] = _check_limits(kt, ub=kt_max, ub_le=True)
    return flags


def check_poa_clearsky(poa_global, poa_clearsky, kt_max=1.1):
    """
    Flags plane of array irradiance values greater than clearsky values.

    Parameters:
    -----------
    poa_global : Series
        Plane of array irradiance in W/m^2
    poa_clearsky : Series
        Plane of array irradiance under clear sky conditions, in W/m^2
    kt_max : float
        maximum allowed ratio of poa_global to poa_clearsky

    Returns:
    --------
    flags : Series
        True if poa_global is less than or equal to clear sky value.
    """
    kt = clearsky_index(poa_global, poa_clearsky,
                        max_clearsky_index=np.Inf)
    flags = _check_limits(kt, ub=kt_max, ub_le=True)
    return flags


def check_irradiance_day_night(times, solar_position=None, location=None,
                               max_zenith=87):
    """ Checks for day/night periods based on solar zenith.

    If solar_position is not provide, location must be provided and solar
    position will be calculated.

    Parameters
    ----------
    times : DatetimeIndex
    solar_position : None or DataFrame, default None
        If DataFrame, columns must include ``zenith``.
    location : None or pvlib.location.Location, default None
    max_zenith : maximum zenith angle for a daylight time

    Returns
    -------
    flags : DataFrame
        True when solar zenith is greater than max_zenith.
    """
    if solar_position is None and location is None:
        raise ValueError("Either solar_position or location is required")
    elif solar_position is None and location is not None:
        solar_position = get_solarposition(location, times)

    flags = pd.DataFrame(index=times, data=None, columns=['daytime'])
    flags['daytime'] = _check_limits(solar_position['zenith'], ub=max_zenith)
    return flags


def check_timestamp_spacing(times, freq=None):
    """ Checks for even spacing of times.

    Parameters
    ----------
    times : DatetimeIndex
    freq : string or None, default None
        resolution of rounding, e.g., '1T' to round to nearest minute

    Returns
    -------
    boolean : True if the rounded timestamps are equally spaced
    """

    if times.size > 1:
        if freq is not None:
            dt = pd.Series(times.round(freq).values)
        else:
            dt = pd.Series(times.values)
        delta = dt.diff()
        gaps = delta[1:].unique()  # first value is NaT, rest are timedeltas
        return len(gaps) == 1
    else:
        return True  # singleton DatetimeIndex passes


def _all_close_to_first(x, rtol=1e-5, atol=1e-8):
    """ Returns True if all values in x are close to x[0].

    Parameters
    ----------
    x : array
    rtol : float, default 1e-5
        relative tolerance for detecting a change in data values
    atol : float, default 1e-8
        absolute tolerance for detecting a change in data values

    Returns
    -------
    Boolean
    """
    return np.allclose(a=x, b=x[0], rtol=rtol, atol=atol)


def detect_stale_values(x, window=3, rtol=1e-5, atol=1e-8):
    """ Detects stale data.

    For a window of length N, the last value (index N-1) is considered stale
    if all values in the window are close to the first value (index 0).

    Parameters
    ----------
    x : Series
        data to be processed
    window : int, default 3
        number of consecutive values which, if unchanged, indicates stale data
    rtol : float, default 1e-5
        relative tolerance for detecting a change in data values
    atol : float, default 1e-8
        absolute tolerance for detecting a change in data values

    Parameters rtol and atol have the same meaning as in numpy.allclose

    Returns
    -------
    flags : Series
        True if the value is part of a stale sequence of data
    Raises
    ------
        ValueError if window < 2
    """
    if window < 2:
        raise ValueError('window set to {}, must be at least 2'.format(window))

    flags = x.rolling(window=window).apply(
        _all_close_to_first, raw=True, kwargs={'rtol': rtol, 'atol': atol}
        ).fillna(False).astype(bool)
    return flags


def detect_interpolation(x, window=3, rtol=1e-5, atol=1e-8):
    """ Detects sequences of data which appear linear.

    Sequences are linear if the first difference appears to be constant.
    For a window of length N, the last value (index N-1) is flagged
    if all values in the window appear to be a line segment.

    Parameters
    ----------
    x : series
        data to be processed
    window : int, default 3
        number of sequential values that, if the first difference is constant,
        are classified as a linear sequence
    rtol : float, default 1e-5
        tolerance relative to max(abs(x.diff()) for detecting a change
    atol : float, default 1e-8
        absolute tolerance for detecting a change in first difference

    Returns
    -------
    flags : Series
        True if the value is part of a linear sequence

    Raises
    ------
        ValueError if window < 3
    """
    if window < 3:
        raise ValueError('window set to {}, must be at least 3'.format(window))

    # reduce window by 1 because we're passing the first difference
    flags = detect_stale_values(x.diff(periods=1), window=window-1, rtol=rtol,
                                atol=atol)
    return flags


def detect_levels(x, count=3, num_bins=100):
    """ Detects plateau levels in data.

    Parameters
    ----------
    x : Series
        data to be processed
    count : int
        number of plateaus to return
    num_bins : int
        number of bins to use in histogram that finds plateau levels

    Returns
    -------
    levels : list of tuples
        (left, right) values of the interval in x with a detected plateau, in
        decreasing order of count of x values in the interval. List length is
        given by the kwarg count
    """
    hist, bin_edges = np.histogram(x, bins=num_bins, density=True)
    level_index = np.argsort(hist * -1)  # decreasing order
    levels = [(bin_edges[i], bin_edges[i + 1]) for i in level_index[:count]]
    return levels, bin_edges


def _label_clipping(x, window, frac):
    """ Returns Series with True at the end of each window with
    sum(x(window)) >= window * frac.
    """
    tmp = x.rolling(window).sum()
    y = (tmp >= window * frac) & x.astype(bool)
    return y


def detect_clipping(ac_power, window=4, fraction_in_window=0.75, rtol=5e-3,
                    levels=2):
    """ Detects clipping in a series of AC power.

    Possible clipped power levels are found by detect_levels. Within each
    sliding window, clipping is indicated when at least fraction_in_window
    of points are close to a clipped power level.

    Parameters
    ----------
    ac_power : Series
        data to be processed

    window : int
        number of data points defining the length of a rolling window

    fraction_in_window : float
        fraction of points which indicate clipping if AC power at each point
        is close to the plateau level

    rtol : float
        a point is close to a clipped level M if
        abs(ac_power - M) < rtol * max(ac_power)

    levels : int
        number of clipped power levels to consider.

    Returns
    -------
    flags : Series
        True when clipping is indicated.
    """
    num_bins = np.ceil(1.0 / rtol).astype(int)
    flags = pd.Series(index=ac_power.index, data=False)
    power_plateaus, bins = detect_levels(ac_power, count=levels,
                                         num_bins=num_bins)
    for lower, upper in power_plateaus:
        temp = pd.Series(index=ac_power.index, data=0.0)
        temp.loc[(ac_power >= lower) & (ac_power <= upper)] = 1.0
        flags = flags | _label_clipping(temp, window=window,
                                        frac=fraction_in_window)
    return flags
