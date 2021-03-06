# coding: utf-8

"""Collection of Functions to convert API responses into python objects
and vice versa.
"""
import base64
from functools import wraps
from inspect import signature
import zlib


import pandas as pd
import pyarrow as pa


from solarforecastarbiter import datamodel


def _dataframe_to_json(payload_df):
    payload_df.index.name = 'timestamp'
    json_vals = payload_df.tz_convert("UTC").reset_index().to_json(
        orient="records", date_format='iso', date_unit='s')
    return '{"values":' + json_vals + '}'


def observation_df_to_json_payload(
        observation_df, default_quality_flag=None):
    """Extracts a variable from an observation DataFrame and formats it
    into a JSON payload for posting to the Solar Forecast Arbiter API.

    Parameters
    ----------
    observation_df : DataFrame
        Dataframe of observation data. Must contain a tz-aware DateTimeIndex
        and a 'value' column. May contain a column of data quality
        flags labeled 'quality_flag'.
    default_quality_flag : int
        If 'quality_flag' is not a column, the quality flag for each row is
        set to this value.

    Returns
    -------
    string
        SolarForecastArbiter API JSON payload for posting to the observation
        endpoint. See Notes section for example.

    Notes
    -----
    Function returns an object in the following format:

    .. code::

        {
          'values': [
            {
              “timestamp”: “2018-11-22T12:01:48Z”, # ISO 8601 datetime in UTC
              “value”: 10.23, # floating point value of observation
              “quality_flag”: 0
            },...
          ]
        }

    Raises
    ------
    KeyError
       When 'value' is missing from the columns or 'quality_flag'
       is missing and default_quality_flag is None
    """
    if default_quality_flag is None:
        payload_df = observation_df[['value', 'quality_flag']]
    else:
        payload_df = observation_df[['value']]
        payload_df['quality_flag'] = int(default_quality_flag)
    return _dataframe_to_json(payload_df)


def forecast_object_to_json(forecast_series):
    """
    Converts a forecast Series to JSON to post to the
    SolarForecastArbiter API.

    Parameters
    ----------
    forecast_series : pandas.Series
        The series that contains the forecast values with a
        datetime index.

    Returns
    -------
    string
        The JSON encoded forecast values dict
    """
    payload_df = forecast_series.to_frame('value')
    return _dataframe_to_json(payload_df)


def _json_to_dataframe(json_payload):
    # in the future, might worry about reading the response in chunks
    # to stream the data and avoid having it all in memory at once,
    # but 30 days of 1 minute data is probably ~4 MB of text. A better
    # approach would probably be to switch to a binary format.
    vals = json_payload['values']
    if len(vals) == 0:
        df = pd.DataFrame([], columns=['value', 'quality_flag'],
                          index=pd.DatetimeIndex([], name='timestamp'))
    else:
        df = pd.DataFrame.from_dict(json_payload['values'])
        df.index = pd.to_datetime(df['timestamp'], utc=True,
                                  infer_datetime_format=True)
    return df


def json_payload_to_observation_df(json_payload):
    """
    Convert the JSON payload dict as returned by the SolarForecastArbiter API
    observations/values endpoint into a DataFrame

    Parameters
    ----------
    json_payload : dict
        Dictionary as returned by the API with a "values" key which is a list
        of dicts like {'timestamp': <timestamp>, 'value': <float>,
        'quality_flag': <int>}

    Returns
    -------
    pandas.DataFrame
       With a tz-aware DatetimeIndex and ['value', 'quality_flag'] columns
    """
    df = _json_to_dataframe(json_payload)
    return df[['value', 'quality_flag']]


def json_payload_to_forecast_series(json_payload):
    """
    Convert the JSON payload dict as returned by the SolarForecastArbiter API
    forecasts/values endpoing into a Series

    Parameters
    ----------
    json_payload : dict
        Dictionary as returned by the API with a "values" key which is a list
        of dicts like {'timestamp': <timestamp>, 'value': <float>}

    Returns
    -------
    pandas.Series
       With a tz-aware DatetimeIndex
    """

    df = _json_to_dataframe(json_payload)
    return df['value']


def adjust_start_end_for_interval_label(interval_label, start, end,
                                        limit_instant=False):
    """
    Adjusts the start and end times depending on the interval_label.

    Parameters
    ----------
    interval_label : str or None
       The interval label for the the object the data represents
    start : pandas.Timestamp
       Start time to restrict data to
    end : pandas.Timestamp
       End time to restrict data to
    limit_instant : boolean
       If true, an interval label of 'instant' will remove a nanosecond
       from end to ensure forecasts do not overlap. If False, instant
       returns start, end unmodified

    Returns
    -------
    start, end
       Return the adjusted start and end

    Raises
    ------
    ValueError
       If an invalid interval_label is given

    Examples
    --------
    .. testsetup::

       from solarforecastarbiter.io.utils import *

    Define input start/end:

    >>> start = pd.Timestamp('20190101 1200Z')
    >>> end = pd.Timestamp('20190101 1300Z')

    Beginning:

    >>> adjust_start_end_for_interval_label('beginning', start, end)
    (Timestamp('2019-01-01 12:00:00+0000', tz='UTC'), Timestamp('2019-01-01 12:59:59.999999999+0000', tz='UTC'))

    Ending:

    >>> adjust_start_end_for_interval_label('ending', start, end)
    (Timestamp('2019-01-01 12:00:00.000000001+0000', tz='UTC'), Timestamp('2019-01-01 13:00:00+0000', tz='UTC'))

    Instantaneous:

    >>> adjust_start_end_for_interval_label('instant', start, end)
    (Timestamp('2019-01-01 12:00:00+0000', tz='UTC'), Timestamp('2019-01-01 13:00:00+0000', tz='UTC'))

    >>> adjust_start_end_for_interval_label('instant', start, end,
    ...                                     limit_instant=True)
    (Timestamp('2019-01-01 12:00:00+0000', tz='UTC'), Timestamp('2019-01-01 12:59:59.999999999+0000', tz='UTC'))

    """ # NOQA

    if (
            interval_label is not None and
            interval_label not in ('instant', 'beginning', 'ending')
    ):
        raise ValueError('Invalid interval_label')

    if (
            interval_label == 'beginning' or
            (interval_label == 'instant' and limit_instant)
    ):
        end -= pd.Timedelta(1, unit='nano')
    elif interval_label == 'ending':
        start += pd.Timedelta(1, unit='nano')
    return start, end


def adjust_timeseries_for_interval_label(data, interval_label, start, end):
    """
    Adjusts the index of the data depending on the interval_label, start,
    and end. Will always return the data located between start, end.

    Parameters
    ----------
    data : pandas.Series or pandas.DataFrame
       The data with a localized DatetimeIndex
    interval_label : str or None
       The interval label for the the object the data represents
    start : pandas.Timestamp
       Start time to restrict data to
    end : pandas.Timestamp
       End time to restrict data to

    Returns
    -------
    pandas.Series or pandas.DataFrame
       Return data between start and end, in/excluding the endpoints
       depending on interval_label

    Raises
    ------
    ValueError
       If an invalid interval_label is given or data is not localized.
    """
    start, end = adjust_start_end_for_interval_label(interval_label, start,
                                                     end)
    data = data.sort_index(axis=0)
    # pandas >= 0.25.1 requires start, end to have same tzinfo.
    # unexpected behavior when data is not localized, so prevent that
    if data.empty:
        return data
    if data.index.tzinfo is None:
        raise ValueError('data must be localized')
    start = start.tz_convert(data.index.tzinfo)
    end = end.tz_convert(data.index.tzinfo)
    return data.loc[start:end]


def serialize_data(values):
    serialized_buf = pa.serialize(values).to_buffer()
    compressed_bytes = zlib.compress(serialized_buf)
    encoded = base64.b64encode(compressed_bytes)
    return encoded.decode('ascii')  # bytes to str


def deserialize_data(data):
    compressed = base64.b64decode(data)
    serialized = zlib.decompress(compressed)
    values = pa.deserialize(serialized)
    return values


def serialize_raw_report(raw):
    bundle = {'metrics': raw.metrics,
              'template': raw.template,
              'metadata': raw.metadata.to_dict(),
              'processed_forecasts_observations': [
                  pfx.to_dict() for pfx in
                  raw.processed_forecasts_observations]}
    return serialize_data(bundle)


def deserialize_raw_report(encoded_bundle, version=0):
    bundle = deserialize_data(encoded_bundle)
    return datamodel.RawReport.from_dict(bundle)


class HiddenToken:
    """
    Obscure the representation of the input string `token` to avoid saving
    or displaying access tokens in logs.
    """
    def __init__(self, token):
        self.token = str(token)  # make sure it isn't a localproxy

    def __repr__(self):
        return '****ACCESS*TOKEN****'


def ensure_timestamps(*time_args):
    """
    Decorator that converts the specified time arguments of the wrapped
    function to pandas.Timestamp objects

    Parameters
    ----------
    strings
       Function arguments to convert to pandas.Timestamp before
       executing function

    Raises
    ------
    ValueError
        If any of time_args cannot be converted to pandas.Timestamp

    Examples
    --------
    .. testsetup::

       import datetime as dt
       from solarforecastarbiter.io.utils import *

    >>> @ensure_timestamps('start', 'end')
    ... def get_values(start, end, other_arg):
    ...     # do stuff with start, end assumed to be pandas.Timestamps
    ...     if isinstance(start, pd.Timestamp):
    ...         return True

    >>> get_values('2019-01-01T00:00Z', dt.datetime(2019, 1, 2, 12), 'other')
    True
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            sig = signature(f)
            inds = {k: None for k in time_args}
            for i, k in enumerate(sig.parameters.keys()):
                if k in inds:
                    inds[k] = i
            nargs = list(args)
            for k, ind in inds.items():
                if k in kwargs:
                    kwargs[k] = pd.Timestamp(kwargs[k])
                elif ind is not None:
                    nargs[ind] = pd.Timestamp(args[ind])
            return f(*nargs, **kwargs)
        return wrapper
    return decorator
