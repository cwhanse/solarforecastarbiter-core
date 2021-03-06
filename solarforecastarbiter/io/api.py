"""
Functions to connect to and process data from SolarForecastArbiter API
"""
import json
import logging
import requests
from urllib3 import Retry


from solarforecastarbiter import datamodel
from solarforecastarbiter.io.utils import (
    json_payload_to_observation_df,
    json_payload_to_forecast_series,
    observation_df_to_json_payload,
    forecast_object_to_json,
    adjust_timeseries_for_interval_label,
    serialize_data, deserialize_data,
    serialize_raw_report, deserialize_raw_report,
    HiddenToken, ensure_timestamps)


BASE_URL = 'https://api.solarforecastarbiter.org'
logger = logging.getLogger(__name__)


def request_cli_access_token(user, password):
    req = requests.post(
        'https://solarforecastarbiter.auth0.com/oauth/token',
        data={'grant_type': 'password', 'username': user,
              'audience': BASE_URL,
              'password': password,
              'client_id': 'c16EJo48lbTCQEhqSztGGlmxxxmZ4zX7'})
    req.raise_for_status()
    return req.json()['access_token']


class APISession(requests.Session):
    """
    Subclass of requests.Session to handle requets to the SolarForecastArbiter
    API. The Session provides connection pooling, automatic retries for certain
    types of requets, default timeouts, and a default base url. Responses are
    converted into the appropriate class from datamodel.py or a pandas object.

    Parameters
    ----------
    access_token : string or HiddenToken
        The base64 encoded Bearer token to authenticate with the API
    default_timeout : float or tuple, optional
        A default timeout to add to all requests. If a tuple, the first element
        is the connection timeout and the second is the read timeout.
        Default is 10 seconds for connection and 60 seconds to read from the
        server.
    base_url : string
        URL to use as the base for endpoints to APISession
    """

    def __init__(self, access_token, default_timeout=(10, 60),
                 base_url=None):
        super().__init__()
        if isinstance(access_token, HiddenToken):
            access_token = access_token.token
        self.headers = {'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/json',
                        'Accept-Encoding': 'gzip,deflate'}
        self.default_timeout = default_timeout
        self.base_url = base_url or BASE_URL
        # set requests to automatically retry
        retries = Retry(total=10, connect=3, read=3, status=3,
                        status_forcelist=[408, 423, 444, 500, 501, 502, 503,
                                          504, 507, 508, 511, 599],
                        backoff_factor=0.5,
                        raise_on_status=False,
                        remove_headers_on_redirect=[])
        adapter = requests.adapters.HTTPAdapter(max_retries=retries)
        self.mount(self.base_url, adapter)

    def request(self, method, url, *args, **kwargs):
        """
        Modify the default Session.request to add in the default timeout
        and make requests relative to the base_url. Users will likely
        use the standard get and post methods instead of calling this directly.

        Raises
        ------
        requests.exceptions.HTTPError
            When an error is encountered in when making the request to the API
        """
        if url.startswith('/'):
            url = f'{self.base_url}{url}'
        else:
            url = f'{self.base_url}/{url}'
        # set a defautl timeout so we never hang indefinitely
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.default_timeout

        result = super().request(method, url, *args, **kwargs)
        if result.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f'{result.status_code} API Request Error: {result.reason} for '
                f'url: {result.url} and text: {result.text}',
                response=result)

        return result

    def _process_site_dict(self, site_dict):
        if (
                site_dict.get('modeling_parameters', {}).get(
                    'tracking_type', '') in ('fixed', 'single_axis')
        ):
            return datamodel.SolarPowerPlant.from_dict(site_dict)
        else:
            return datamodel.Site.from_dict(site_dict)

    def get_site(self, site_id):
        """
        Retrieve site metadata for site_id from the API and process
        into the proper model.

        Parameters
        ----------
        site_id : string
            UUID of the site to retrieve metadata for

        Returns
        -------
        datamodel.Site or datamodel.SolarPowerPlant
           Dataclass with all the metadata for the site depending on if
           the Site is a power plant with modeling parameters or not.
        """
        req = self.get(f'/sites/{site_id}')
        site_dict = req.json()
        return self._process_site_dict(site_dict)

    def list_sites(self):
        """
        List all the sites available to a user.

        Returns
        -------
        list of datamodel.Sites and datamodel.SolarPowerPlants
        """
        req = self.get('/sites/')
        return [self._process_site_dict(site_dict)
                for site_dict in req.json()]

    def create_site(self, site):
        """
        Create a new site in the API with the given Site model

        Parameters
        ----------
        site : datamodel.Site or datamodel.SolarPowerPlant
            Site to create in the API

        Returns
        -------
        datamodel.Site or datamodel.SolarPowerPlant
            With the appropriate parameters such as site_id set by the API
        """
        site_dict = site.to_dict()
        for k in ('site_id', 'provider'):
            site_dict.pop(k, None)
        site_json = json.dumps(site_dict)
        req = self.post('/sites/', data=site_json,
                        headers={'Content-Type': 'application/json'})
        new_id = req.text
        return self.get_site(new_id)

    def get_observation(self, observation_id):
        """
        Get the metadata from the API for the a given observation_id
        in an Observation object.

        Parameters
        ----------
        observation_id : string
            UUID of the observation to retrieve

        Returns
        -------
        datamodel.Observation
        """
        req = self.get(f'/observations/{observation_id}/metadata')
        obs_dict = req.json()
        site = self.get_site(obs_dict['site_id'])
        obs_dict['site'] = site
        return datamodel.Observation.from_dict(obs_dict)

    def list_observations(self):
        """
        List the observations a user has access to.

        Returns
        -------
        list of datamodel.Observation
        """
        req = self.get('/observations/')
        obs_dicts = req.json()
        if len(obs_dicts) == 0:
            return []
        sites = {site.site_id: site for site in self.list_sites()}
        out = []
        for obs_dict in obs_dicts:
            obs_dict['site'] = sites.get(obs_dict['site_id'])
            out.append(datamodel.Observation.from_dict(obs_dict))
        return out

    def create_observation(self, observation):
        """
        Create a new observation in the API with the given Observation model

        Parameters
        ----------
        observation : datamodel.Observation
            Observation to create in the API

        Returns
        -------
        datamodel.Observation
            With the appropriate parameters such as observation_id set by the
            API
        """
        obs_dict = observation.to_dict()
        obs_dict.pop('observation_id')
        site = obs_dict.pop('site')
        obs_dict['site_id'] = site['site_id']
        obs_json = json.dumps(obs_dict)
        req = self.post('/observations/', data=obs_json,
                        headers={'Content-Type': 'application/json'})
        new_id = req.text
        return self.get_observation(new_id)

    def get_forecast(self, forecast_id):
        """
        Get Forecast metadata from the API for the given forecast_id

        Parameters
        ----------
        forecast_id : string
            UUID of the forecast to get metadata for

        Returns
        -------
        datamodel.Forecast
        """
        req = self.get(f'/forecasts/single/{forecast_id}/metadata')
        fx_dict = req.json()
        site = self.get_site(fx_dict['site_id'])
        fx_dict['site'] = site
        return datamodel.Forecast.from_dict(fx_dict)

    def list_forecasts(self):
        """
        List all Forecasts a user has access to.

        Returns
        -------
        list of datamodel.Forecast
        """
        req = self.get('/forecasts/single/')
        fx_dicts = req.json()
        if len(fx_dicts) == 0:
            return []
        sites = {site.site_id: site for site in self.list_sites()}
        out = []
        for fx_dict in fx_dicts:
            fx_dict['site'] = sites.get(fx_dict['site_id'])
            out.append(datamodel.Forecast.from_dict(fx_dict))
        return out

    def create_forecast(self, forecast):
        """
        Create a new forecast in the API with the given Forecast model

        Parameters
        ----------
        forecast : datamodel.Forecast
            Forecast to create in the API

        Returns
        -------
        datamodel.Forecast
            With the appropriate parameters such as forecast_id set by the API
        """
        fx_dict = forecast.to_dict()
        fx_dict.pop('forecast_id')
        site = fx_dict.pop('site')
        fx_dict['site_id'] = site['site_id']
        fx_json = json.dumps(fx_dict)
        req = self.post('/forecasts/single/', data=fx_json,
                        headers={'Content-Type': 'application/json'})
        new_id = req.text
        return self.get_forecast(new_id)

    def list_probabilistic_forecasts(self):
        """
        List all ProbabilisticForecasts a user has access to.

        Returns
        -------
        list of datamodel.ProbabilisticForecast
        """
        req = self.get('/forecasts/cdf/')
        fx_dicts = req.json()
        if len(fx_dicts) == 0:
            return []
        sites = {site.site_id: site for site in self.list_sites()}
        out = []
        for fx_dict in fx_dicts:
            site = sites.get(fx_dict['site_id'])
            fx_dict['site'] = site
            cvs = []
            for constant_value_dict in fx_dict['constant_values']:
                cvs.append(self.get_probabilistic_forecast_constant_value(
                    constant_value_dict['forecast_id'], site=site))
            fx_dict['constant_values'] = cvs
            out.append(datamodel.ProbabilisticForecast.from_dict(fx_dict))
        return out

    def get_probabilistic_forecast(self, forecast_id):
        """
        Get ProbabilisticForecast metadata from the API for the given
        forecast_id.

        Parameters
        ----------
        forecast_id : string
            UUID of the forecast to get metadata for

        Returns
        -------
        datamodel.ProbabilisticForecast
        """
        # add /metadata after
        # https://github.com/SolarArbiter/solarforecastarbiter-api/issues/158
        req = self.get(f'/forecasts/cdf/{forecast_id}')
        fx_dict = req.json()
        site = self.get_site(fx_dict['site_id'])
        fx_dict['site'] = site
        cvs = []
        for constant_value_dict in fx_dict['constant_values']:
            cvs.append(self.get_probabilistic_forecast_constant_value(
                constant_value_dict['forecast_id'], site=site))
        fx_dict['constant_values'] = cvs
        return datamodel.ProbabilisticForecast.from_dict(fx_dict)

    def get_probabilistic_forecast_constant_value(self, forecast_id,
                                                  site=None):
        """
        Get ProbabilisticForecastConstantValue metadata from the API for
        the given forecast_id.

        Parameters
        ----------
        forecast_id : string
            UUID of the forecast to get metadata for
        site : datamodel.Site or None
            If provided, the object will be attached to the returned
            value (faster). If None, object will be created from site
            metadata obtained from the database (slower).

        Returns
        -------
        datamodel.ProbabilisticForecastConstantValue

        Raises
        ------
        ValueError
            If provided site.site_id does not match database record of
            forecast object's linked site_id.
        """
        # add /metadata after
        # https://github.com/SolarArbiter/solarforecastarbiter-api/issues/158
        req = self.get(f'/forecasts/cdf/single/{forecast_id}')
        fx_dict = req.json()
        site_id = fx_dict['site_id']
        if site is None:
            site = self.get_site(site_id)
        elif site.site_id != site_id:
            raise ValueError('Supplied site.site_id does not match site_id'
                             f'from database. site.site_id: {site.site_id} '
                             f'database site_id: {site_id}')
        fx_dict['site'] = site
        return datamodel.ProbabilisticForecastConstantValue.from_dict(fx_dict)

    def create_probabilistic_forecast(self, forecast):
        """
        Create a new forecast in the API with the given
        ProbabilisticForecast model

        Parameters
        ----------
        forecast : datamodel.ProbabilisticForecast
            Probabilistic forecast to create in the API

        Returns
        -------
        datamodel.ProbabilisticForecast
            With the appropriate parameters such as forecast_id set by the API
        """
        fx_dict = forecast.to_dict()
        fx_dict.pop('forecast_id')
        site = fx_dict.pop('site')
        fx_dict['site_id'] = site['site_id']
        # fx_dict['constant_values'] is tuple of dict representations of
        # all ProbabilisticForecastConstantValue objects in the
        # ProbabilisticForecast. We need to extract just the numeric
        # values from these dicts and put them into a list for the API.
        constant_values_fxs = fx_dict.pop('constant_values')
        constant_values = [fx['constant_value'] for fx in constant_values_fxs]
        fx_dict['constant_values'] = constant_values
        fx_json = json.dumps(fx_dict)
        req = self.post('/forecasts/cdf/', data=fx_json,
                        headers={'Content-Type': 'application/json'})
        new_id = req.text
        return self.get_probabilistic_forecast(new_id)

    @ensure_timestamps('start', 'end')
    def get_observation_values(self, observation_id, start, end,
                               interval_label=None):
        """
        Get observation values from start to end for observation_id from the
        API

        Parameters
        ----------
        observation_id : string
            UUID of the observation object.
        start : timelike object
            Start time in interval to retrieve values for
        end : timelike object
            End time of the interval
        interval_label : str or None
            If beginning, ending, adjust the data to return only data that is
            valid between start and end. If None or instant, return any data
            between start and end inclusive of the endpoints.

        Returns
        -------
        pandas.DataFrame
            With a datetime index and (value, quality_flag) columns

        Raises
        ------
        ValueError
            If start or end cannot be converted into a Pandas Timestamp
        """
        req = self.get(f'/observations/{observation_id}/values',
                       params={'start': start, 'end': end})
        out = json_payload_to_observation_df(req.json())
        return adjust_timeseries_for_interval_label(
            out, interval_label, start, end)

    @ensure_timestamps('start', 'end')
    def get_forecast_values(self, forecast_id, start, end,
                            interval_label=None):
        """
        Get forecast values from start to end for forecast_id

        Parameters
        ----------
        forecast_id : string
            UUID of the forecast object
        start : timelike object
            Start of the interval to retrieve values for
        end : timelike object
            End of the interval
        interval_label : str or None
            If beginning, ending, adjust the data to return only data that is
            valid between start and end. If None or instant, return any data
            between start and end inclusive of the endpoints.

        Returns
        -------
        pandas.Series
           With the forecast values and a datetime index

        Raises
        ------
        ValueError
            If start or end cannot be converted into a Pandas Timestamp
        """
        req = self.get(f'/forecasts/single/{forecast_id}/values',
                       params={'start': start, 'end': end})
        out = json_payload_to_forecast_series(req.json())
        return adjust_timeseries_for_interval_label(
            out, interval_label, start, end)

    @ensure_timestamps('start', 'end')
    def get_probabilistic_forecast_constant_value_values(
            self, forecast_id, start, end, interval_label=None):
        """
        Get forecast values from start to end for forecast_id

        Parameters
        ----------
        forecast_id : string
            UUID of the forecast object
        start : timelike object
            Start of the interval to retrieve values for
        end : timelike object
            End of the interval
        interval_label : str or None
            If beginning, ending, adjust the data to return only data that is
            valid between start and end. If None or instant, return any data
            between start and end inclusive of the endpoints.

        Returns
        -------
        pandas.Series
           With the forecast values and a datetime index

        Raises
        ------
        ValueError
            If start or end cannot be converted into a Pandas Timestamp
        """
        req = self.get(f'/forecasts/cdf/single/{forecast_id}/values',
                       params={'start': start, 'end': end})
        out = json_payload_to_forecast_series(req.json())
        return adjust_timeseries_for_interval_label(
            out, interval_label, start, end)

    def post_observation_values(self, observation_id, observation_df,
                                params=None):
        """
        Upload the given observation values to the appropriate observation_id
        of the API.

        Parameters
        ----------
        observation_id : string
            UUID of the observation to add values for
        observation_df : pandas.DataFrame
            Dataframe with a datetime index and the (required) value and
            quality_flag columns to upload to the API.
        params : dict, list, string, default None
            Parameters passed through POST request. Types are the same as
            Requests <https://2.python-requests.org/en/master/api/#requests.Request>
        """  # NOQA
        json_vals = observation_df_to_json_payload(observation_df)
        self.post(f'/observations/{observation_id}/values',
                  data=json_vals, params=params,
                  headers={'Content-Type': 'application/json'})

    def post_forecast_values(self, forecast_id, forecast_series):
        """
        Upload the given forecast values to the appropriate forecast_id of the
        API

        Parameters
        ----------
        forecast_id : string
            UUID of the forecast to upload values to
        forecast_obj : pandas.Series
            Pandas series with a datetime index that contains the values to
            upload to the API
        """
        json_vals = forecast_object_to_json(forecast_series)
        self.post(f'/forecasts/single/{forecast_id}/values',
                  data=json_vals,
                  headers={'Content-Type': 'application/json'})

    def post_probabilistic_forecast_constant_value_values(self, forecast_id,
                                                          forecast_series):
        """
        Upload the given forecast values to the appropriate forecast_id of the
        API

        Parameters
        ----------
        forecast_id : string
            UUID of the forecast to upload values to
        forecast_obj : pandas.Series
            Pandas series with a datetime index that contains the values to
            upload to the API
        """
        json_vals = forecast_object_to_json(forecast_series)
        self.post(f'/forecasts/cdf/single/{forecast_id}/values',
                  data=json_vals,
                  headers={'Content-Type': 'application/json'})

    def _process_report_dict(self, rep_dict):
        req_dict = rep_dict['report_parameters']
        for key in ('name', 'report_id', 'status'):
            req_dict[key] = rep_dict[key]
        req_dict['metrics'] = tuple(req_dict['metrics'])
        req_dict['forecast_observations'] = tuple([
            datamodel.ForecastObservation(self.get_forecast(o[0]),
                                          self.get_observation(o[1]))
            for o in req_dict['object_pairs']])
        return datamodel.Report.from_dict(req_dict)

    def get_report(self, report_id):
        """
        Get the metadata, and possible raw report if it has processed,
        from the API for the given report_id in a Report object.

        Parameters
        ----------
        report_id : string
            UUID of the report to retrieve

        Returns
        -------
        datamodel.Report
        """
        req = self.get(f'/reports/{report_id}')
        resp = req.json()
        raw = resp.pop('raw_report')
        report = self._process_report_dict(resp)
        if raw is not None:
            raw_report = deserialize_raw_report(raw)
            processed_fxobs = self.get_raw_report_processed_data(
                report_id, raw_report, resp['values'])
            report = report.replace(raw_report=raw_report.replace(
                processed_forecasts_observations=processed_fxobs))
        return report

    def list_reports(self):
        """
        List the reports a user has access to.  Does not load the raw
        report data, use :py:meth:`~.APISession.get_report`.

        Returns
        -------
        list of datamodel.Report

        """
        req = self.get('/reports')
        rep_dicts = req.json()
        if len(rep_dicts) == 0:
            return []
        out = []
        for rep_dict in rep_dicts:
            out.append(self._process_report_dict(rep_dict))
        return out

    def create_report(self, report):
        """
        Post the report request to the API. A completed report should post
        the raw_report with :py:meth:`~.APISession.post_raw_report`.

        Parameters
        ----------
        report : datamodel.Report

        Returns
        -------
        datamodel.Report
           As returned by the API
        """
        report_dict = report.to_dict()
        report_dict.pop('report_id')
        name = report_dict.pop('name')
        for key in ('raw_report', '__version__', 'status'):
            del report_dict[key]
        report_dict['filters'] = []
        fxobs = report_dict.pop('forecast_observations')
        report_dict['object_pairs'] = [
            (_fo['forecast']['forecast_id'],
             _fo['observation']['observation_id'])
            for _fo in fxobs]
        params = {'name': name,
                  'report_parameters': report_dict}
        req = self.post('/reports/', json=params,
                        headers={'Content-Type': 'application/json'})
        new_id = req.text
        return self.get_report(new_id)

    def post_raw_report_processed_data(self, report_id, raw_report):
        """
        Post the processed data that was used to make the report to the
        API.

        Parameters
        ----------
        report_id : str
            ID of the report to post values to
        raw_report : datamodel.RawReport
            The raw report object with processed_forecasts_observations

        Returns
        -------
        tuple
            of datamodel.ProcessedForecastObservation with `forecast_values`
            and `observations_values` replaced with report value IDs for later
            retrieval
        """
        posted_fxobs = []
        for fxobs in raw_report.processed_forecasts_observations:
            fx_data = {
                'object_id': fxobs.original.forecast.forecast_id,
                'processed_values': serialize_data(fxobs.forecast_values)}
            fx_post = self.post(
                f'/reports/{report_id}/values',
                json=fx_data, headers={'Content-Type': 'application/json'})
            obs_data = {
                'object_id': fxobs.original.observation.observation_id,
                'processed_values': serialize_data(fxobs.observation_values)}
            obs_post = self.post(
                f'/reports/{report_id}/values',
                json=obs_data, headers={'Content-Type': 'application/json'})
            processed_fx_id = fx_post.text
            processed_obs_id = obs_post.text
            new_fxobs = fxobs.replace(forecast_values=processed_fx_id,
                                      observation_values=processed_obs_id)
            posted_fxobs.append(new_fxobs)
        return tuple(posted_fxobs)

    def get_raw_report_processed_data(self, report_id, raw_report,
                                      values=None):
        """
        Load the processed forecast/observation data into the
        datamodel.ProcessedForecastObservation objects of the raw_report.

        Parameters
        ----------
        report_id : str
            ID of the report that values will be loaded from
        raw_report : datamodel.RawReport
            The raw report with processed_forecasts_observations to
            be replaced
        values : list or None
            The report values dict as returned by the API. If None, fetch
            the values from the API for the given report_id

        Returns
        -------
        tuple
           Of datamodel.ProcessedForecastObservation with values loaded into
           `forecast_values` and `observation_values`
        """
        if values is None:
            val_req = self.get(f'/reports/{report_id}/values')
            values = val_req.json()
        val_dict = {v['id']: v['processed_values'] for v in values}
        out = []
        for fxobs in raw_report.processed_forecasts_observations:
            fx_vals = val_dict.get(fxobs.forecast_values, None)
            if fx_vals is not None:
                fx_vals = deserialize_data(fx_vals)
            obs_vals = val_dict.get(fxobs.observation_values, None)
            if obs_vals is not None:
                obs_vals = deserialize_data(obs_vals)
            new_fxobs = fxobs.replace(forecast_values=fx_vals,
                                      observation_values=obs_vals)
            out.append(new_fxobs)
        return tuple(out)

    def post_raw_report(self, report_id, raw_report):
        """
        Update the report with the raw report and metrics

        Parameters
        ----------
        report_id : str
           ID of the report to update
        raw_report : datamodel.RawReport
           The raw report object to add to the report
        """
        posted_fxobs = self.post_raw_report_processed_data(
            report_id, raw_report)
        to_post = raw_report.replace(
            processed_forecasts_observations=posted_fxobs)
        compressed_bundle = serialize_raw_report(to_post)
        # metrics not really meaningful right now as JSON
        self.post(f'/reports/{report_id}/metrics',
                  json={'metrics': {}, 'raw_report': compressed_bundle},
                  headers={'Content-Type': 'application/json'})
        self.update_report_status(report_id, 'complete')

    def update_report_status(self, report_id, status):
        """
        Update the status of the report

        Parameters
        ----------
        report_id : str
           ID of the report to update
        status : str
           New status of the report
        """
        self.post(f'/reports/{report_id}/status/{status}')
