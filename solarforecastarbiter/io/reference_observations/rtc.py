import logging
import os


from requests.exceptions import HTTPError


from solarforecastarbiter.io.fetch import rtc
from solarforecastarbiter.io.reference_observations import common


logger = logging.getLogger('reference_data')


DOE_RTC_VARIABLE_MAP = {
    'GlobalIrrad': 'ghi',
    'DiffuseIrrad': 'dhi',
    'DirectIrrad': 'dni',
    'AmbientTemp_weather': 'air_temperature',
    'WindSpeed': 'wind_speed',
    'RelativeHumidity': 'relative_humidity',
    'PyranometerIrrad': 'poa_global',
    'Sys1Wac': 'ac_power'
}


def adjust_site_parameters(site):
    """Add the PV modeling parameters"""
    out = site.copy()
    modeling_params = {
        'ac_capacity': 0.00324,  # no clipping
        'dc_capacity': 0.00324,
        'temperature_coefficient': -0.00420,
        'dc_loss_factor': 0,
        'ac_loss_factor': 0,
        'surface_tilt': 35,
        'surface_azimuth': 180,
        'tracking_type': 'fixed'}
    out['modeling_parameters'] = modeling_params
    out['extra_parameters']['module'] = 'Suniva 270W'
    return out


def initialize_site_observations(api, site):
    """Creates an observation at the site for each variable in
    DOE_RTC_VARIABLE_MAP

    Parameters
    ----------
    api : solarforecastarbiter.io.api.APISession
        An active Reference user session.
    site : datamodel.Site
        The site object for which to create Observations.
    """
    for sfa_var in DOE_RTC_VARIABLE_MAP.values():
        logger.info(f'Creating {sfa_var} at {site.name}')
        try:
            common.create_observation(
                api, site, sfa_var)
        except HTTPError as e:
            logger.error(f'Could not create Observation for "{sfa_var}" '
                         f'at DOE RTC site {site.name}')
            logger.debug(f'Error: {e.response.text}')


def initialize_site_forecasts(api, site):
    """
    Create a forecasts for each variable in DOE_RTC_VARIABLE_MAP at each site

    Parameters
    ----------
    api : solarforecastarbiter.io.api.APISession
        An active Reference user session.
    site : datamodel.Site
        The site object for which to create Forecasts.
    """
    common.create_forecasts(api, site, DOE_RTC_VARIABLE_MAP.values())


def update_observation_data(api, sites, observations, start, end):
    """Post new observation data to a list of DOE RTC Observations
    from start to end.

    api : solarforecastarbiter.io.api.APISession
        An active Reference user session.
    sites: list of solarforecastarbiter.datamodel.Site
        List of all reference sites as Objects
    observations: list of solarforecastarbiter.datamodel.Observation
        List of all reference observations.
    start : datetime
        The beginning of the period to request data for.
    end : datetime
        The end of the period to request data for.
    """
    doe_rtc_api_key = os.getenv('DOE_RTC_API_KEY')
    if doe_rtc_api_key is None:
        raise KeyError('"DOE_RTC_API_KEY" environment variable must be '
                       'set to update DOE RTC observation data.')
    doe_rtc_sites = common.filter_by_networks(sites, 'DOE RTC')
    for site in doe_rtc_sites:
        try:
            site_extra_params = common.decode_extra_parameters(site)
        except ValueError:
            continue
        doe_rtc_site_id = site_extra_params['network_api_id']
        obs_df = rtc.fetch_doe_rtc(
            doe_rtc_site_id, doe_rtc_api_key,
            start.tz_convert(site.timezone), end.tz_convert(site.timezone))
        obs_df = obs_df.rename(columns=DOE_RTC_VARIABLE_MAP).tz_localize(
            site.timezone)
        # W to MW
        if 'ac_power' in obs_df:
            obs_df['ac_power'] = obs_df['ac_power'] / 1e6
        data_in_range = obs_df[start:end]
        if data_in_range.empty:
            logger.warning(f'Data for site {site.name} contained no '
                           f'entries from {start} to {end}.')
            continue
        site_observations = [obs for obs in observations if obs.site == site]
        for obs in site_observations:
            common.post_observation_data(api, obs, data_in_range, start, end)
