import logging


from pvlib.irradiance import get_extra_radiation


from solarforecastarbiter import pvmodel
from solarforecastarbiter.io.api import APISession
from solarforecastarbiter.validation import validator


logger = logging.getLogger(__name__)


def _validate_timestamp(observation, values):
    return validator.check_timestamp_spacing(
        values.index, observation.interval_length, _return_mask=True)


def _solpos_dni_extra(observation, values):
    solar_position = pvmodel.calculate_solar_position(
        observation.site.latitude, observation.site.longitude,
        observation.site.elevation, values.index)
    dni_extra = get_extra_radiation(values.index)
    timestamp_flag = _validate_timestamp(observation, values)
    night_flag = validator.check_irradiance_day_night(solar_position['zenith'],
                                                      _return_mask=True)
    return solar_position, dni_extra, timestamp_flag, night_flag


def validate_ghi(observation, values):
    """
    Run validation checks on a GHI observation.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`,
        `validator.check_irradiance_day_night`,
        `validator.check_ghi_limits_QCRad`,
        `validator.check_ghi_clearsky`
    """
    solar_position, dni_extra, timestamp_flag, night_flag = _solpos_dni_extra(
        observation, values)
    clearsky = pvmodel.calculate_clearsky(
        observation.site.latitude, observation.site.longitude,
        observation.site.elevation, solar_position['apparent_zenith'])

    ghi_limit_flag = validator.check_ghi_limits_QCRad(
        values, solar_position['zenith'], dni_extra,
        _return_mask=True)
    ghi_clearsky_flag = validator.check_ghi_clearsky(values, clearsky['ghi'],
                                                     _return_mask=True)
    return timestamp_flag, night_flag, ghi_limit_flag, ghi_clearsky_flag


def validate_dni(observation, values):
    """
    Run validation checks on a DNI observation.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`,
        `validator.check_irradiance_day_night`,
        `validator.check_dni_limits_QCRad`
    """
    solar_position, dni_extra, timestamp_flag, night_flag = _solpos_dni_extra(
        observation, values)
    dni_limit_flag = validator.check_dni_limits_QCRad(values,
                                                      solar_position['zenith'],
                                                      dni_extra,
                                                      _return_mask=True)
    return timestamp_flag, night_flag, dni_limit_flag


def validate_dhi(observation, values):
    """
    Run validation checks on a DHI observation.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`,
        `validator.check_irradiance_day_night`,
        `validator.check_dhi_limits_QCRad`
    """
    solar_position, dni_extra, timestamp_flag, night_flag = _solpos_dni_extra(
        observation, values)
    dhi_limit_flag = validator.check_dhi_limits_QCRad(values,
                                                      solar_position['zenith'],
                                                      dni_extra,
                                                      _return_mask=True)
    return timestamp_flag, night_flag, dhi_limit_flag


def validate_poa_global(observation, values):
    """
    Run validation checks on a POA observation.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`,
        `validator.check_irradiance_day_night`,
        `validator.check_poa_clearsky`
    """
    solar_position, dni_extra, timestamp_flag, night_flag = _solpos_dni_extra(
        observation, values)
    clearsky = pvmodel.calculate_clearsky(
        observation.site.latitude, observation.site.longitude,
        observation.site.elevation, solar_position['apparent_zenith'])
    aoi_func = pvmodel.aoi_func_factory(observation.site.modeling_parameters)
    poa_clearsky = pvmodel.calculate_poa_effective(
        aoi_func=aoi_func, apparent_zenith=solar_position['apparent_zenith'],
        azimuth=solar_position['azimuth'], ghi=clearsky['ghi'],
        dni=clearsky['dni'], dhi=clearsky['dhi'])
    poa_clearsky_flag = validator.check_poa_clearsky(values, poa_clearsky,
                                                     _return_mask=True)
    return timestamp_flag, night_flag, poa_clearsky_flag


def validate_air_temperature(observation, values):
    """
    Run validation checks on an air temperature observation.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`,
        `validator.check_temperature_limits`
    """
    timestamp_flag = _validate_timestamp(observation, values)
    temp_limit_flag = validator.check_temperature_limits(
        values, _return_mask=True)
    return timestamp_flag, temp_limit_flag


def validate_wind_speed(observation, values):
    """
    Run validation checks on a wind speed observation.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`,
        `validator.check_wind_limits`
    """
    timestamp_flag = _validate_timestamp(observation, values)
    wind_limit_flag = validator.check_wind_limits(values,
                                                  _return_mask=True)
    return timestamp_flag, wind_limit_flag


def validate_relative_humidity(observation, values):
    """
    Run validation checks on a relative humidity observation.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`,
        `validator.check_rh_limits`
    """
    timestamp_flag = _validate_timestamp(observation, values)
    rh_limit_flag = validator.check_rh_limits(values, _return_mask=True)
    return timestamp_flag, rh_limit_flag


def validate_timestamp(observation, values):
    """
    Run validation checks on an observation.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`
    """
    return (_validate_timestamp(observation, values),)


def validate_daily_ghi(observation, values):
    """
    Run validation on a daily timeseries of GHI. First,
    all checks of `validate_ghi` are run in addition to
    detecting stale values and interpolation

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        tests from `validate_ghi`
        `validator.detect_stale_values`
        `validator.detect_interpolation`
    """
    ghi_flags = validate_ghi(observation, values)
    stale_flag = validator.detect_stale_values(values, _return_mask=True)
    interpolation_flag = validator.detect_interpolation(values,
                                                        _return_mask=True)
    return (*ghi_flags, stale_flag, interpolation_flag)


def validate_daily_dc_power(observation, values):
    """
    Run validation on a daily timeseries of DC power.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`
        `validator.detect_stale_values`
        `validator.detect_interpolation`
    """
    timestamp_flag = _validate_timestamp(observation, values)
    stale_flag = validator.detect_stale_values(values, _return_mask=True)
    interpolation_flag = validator.detect_interpolation(values,
                                                        _return_mask=True)
    return (timestamp_flag, stale_flag, interpolation_flag)


def validate_daily_ac_power(observation, values):
    """
    Run a number of validation checks on a daily timeseries of AC power.

    Parameters
    ----------
    observation : solarforecastarbiter.datamodel.Observation
       Observation object that the data is associated with
    values : pandas.Series
       Series of observation values

    Returns
    -------
    tuple
        Tuple of integer bitmask series of flags from the following tests, in
        order,
        `validator.check_timestamp_spacing`
        `validator.detect_stale_values`
        `validator.detect_interpolation`
        `validator.detect_clipping`
    """
    timestamp_flag = _validate_timestamp(observation, values)
    stale_flag = validator.detect_stale_values(values, _return_mask=True)
    interpolation_flag = validator.detect_interpolation(values,
                                                        _return_mask=True)
    clipping_flag = validator.detect_clipping(values, _return_mask=True)
    return (timestamp_flag, stale_flag, interpolation_flag, clipping_flag)


IMMEDIATE_VALIDATION_FUNCS = {
    'air_temperature': validate_air_temperature,
    'wind_speed': validate_wind_speed,
    'ghi': validate_ghi,
    'dni': validate_dni,
    'dhi': validate_dhi,
    'poa_global': validate_poa_global,
    'relative_humidity': validate_relative_humidity
}


def immediate_observation_validation(access_token, observation_id, start, end,
                                     base_url=None):
    """
    Task that will run immediately after Observation values are uploaded to the
    API to validate the data.
    """
    session = APISession(access_token, base_url=base_url)
    observation = session.get_observation(observation_id)
    observation_values = session.get_observation_values(observation_id, start,
                                                        end)
    value_series = observation_values['value']
    quality_flags = observation_values['quality_flag'].copy()

    validation_func = IMMEDIATE_VALIDATION_FUNCS.get(
        observation.variable, validate_timestamp)
    validation_flags = validation_func(observation, value_series)

    for flag in validation_flags:
        quality_flags |= flag

    quality_flags.name = 'quality_flag'
    observation_values.update(quality_flags)
    session.post_observation_values(observation_id, observation_values,
                                    params='donotvalidate')


DAILY_VALIDATION_FUNCS = {
    'ghi': validate_daily_ghi,
    'dc_power': validate_daily_dc_power,
    'ac_power': validate_daily_ac_power
}


def _daily_validation(session, observation, start, end, base_url):
    logger.info('Validating data for %s from %s to %s',
                observation.name, start, end)
    observation_values = session.get_observation_values(
        observation.observation_id, start, end)
    value_series = observation_values['value']
    if len(value_series.dropna()) < 10:
        raise IndexError(
            'Data series does not have at least 10 datapoints to validate')
    quality_flags = observation_values['quality_flag'].copy()

    # if the variable has a daily check, run that, else run the
    # immediate validation, else validate timestamps
    validation_func = DAILY_VALIDATION_FUNCS.get(
        observation.variable, IMMEDIATE_VALIDATION_FUNCS.get(
            observation.variable, validate_timestamp))
    validation_flags = validation_func(observation, value_series)

    for flag in validation_flags:
        quality_flags |= flag

    quality_flags.name = 'quality_flag'
    observation_values.update(quality_flags)
    session.post_observation_values(observation.observation_id,
                                    observation_values,
                                    params='donotvalidate')


def daily_single_observation_validation(access_token, observation_id, start,
                                        end, base_url=None):
    """
    Task that expects a longer, likely daily timeseries of Observation values
    that will be validated.
    """
    session = APISession(access_token, base_url=base_url)
    observation = session.get_observation(observation_id)
    try:
        _daily_validation(session, observation, start, end, base_url)
    except IndexError:
        logger.warning(
            'Daily validation for %s failed: not enough values',
            observation.name)


def daily_observation_validation(access_token, start, end, base_url=None):
    """
    Run the daily observation validation for all observations that the user
    has access to.
    """
    session = APISession(access_token, base_url=base_url)
    observations = session.list_observations()
    for observation in observations:
        try:
            _daily_validation(session, observation, start, end, base_url)
        except IndexError:
            logger.warning(('Skipping daily validation of %s '
                            'not enough values'), observation.name)
            continue
