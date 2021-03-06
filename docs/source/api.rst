.. currentmodule:: solarforecastarbiter

#############
API reference
#############

Data model
==========

The data model.

.. autosummary::
   :toctree: generated/

   datamodel

There are two kinds of sites:

.. autosummary::
   :toctree: generated/

   datamodel.Site
   datamodel.SolarPowerPlant

The several model parameters are associated with the solar power plant site:

.. autosummary::
   :toctree: generated/

   datamodel.PVModelingParameters
   datamodel.FixedTiltModelingParameters
   datamodel.SingleAxisModelingParameters

The Observation and Forecast:

.. autosummary::
   :toctree: generated/

   datamodel.Observation
   datamodel.Forecast

Probabilistic forecasts:

.. autosummary::
   :toctree: generated/

   datamodel.ProbabilisticForecast
   datamodel.ProbabilisticForecastConstantValue

All :py:mod:`~solarforecastarbiter.datamodel` objects have ``from_dict`` and
``to_dict`` methods:

.. autosummary::
   :toctree: generated/

   datamodel.BaseModel.from_dict
   datamodel.BaseModel.to_dict


PV modeling
===========

The :py:mod:`~solarforecastarbiter.pvmodel` module contains functions
closely associated with PV modeling.

.. autosummary::
   :toctree: generated/

   pvmodel

Several utility functions wrap pvlib functions:

.. autosummary::
   :toctree: generated/

   pvmodel.calculate_solar_position
   pvmodel.complete_irradiance_components
   pvmodel.calculate_clearsky


Three functions are useful for determining AOI, surface tilt, and
surface azimuth. :py:func:`~pvmodel.aoi_func_factory` is helpful for
standardizing the calculations for tracking and fixed systems.
See :py:func:`~pvmodel.calculate_poa_effective`, for example.

.. autosummary::
   :toctree: generated/

   pvmodel.aoi_func_factory
   pvmodel.aoi_fixed
   pvmodel.aoi_tracking


.. autosummary::
   :toctree: generated/

   pvmodel.calculate_poa_effective_explicit
   pvmodel.calculate_poa_effective
   pvmodel.calculate_power
   pvmodel.irradiance_to_power


Reference forecasts
===================

Entry points
------------

High-level functions for NWP and persistence forecasts.

.. autosummary::
   :toctree: generated/

   reference_forecasts.main.run_nwp
   reference_forecasts.main.run_persistence
   reference_forecasts.main.find_reference_nwp_forecasts
   reference_forecasts.main.process_nwp_forecast_groups
   reference_forecasts.main.make_latest_nwp_forecasts

NWP models
----------

.. autosummary::
   :toctree: generated/

   reference_forecasts.models.hrrr_subhourly_to_subhourly_instantaneous
   reference_forecasts.models.hrrr_subhourly_to_hourly_mean
   reference_forecasts.models.rap_ghi_to_instantaneous
   reference_forecasts.models.rap_cloud_cover_to_hourly_mean
   reference_forecasts.models.gfs_quarter_deg_3hour_to_hourly_mean
   reference_forecasts.models.gfs_quarter_deg_hourly_to_hourly_mean
   reference_forecasts.models.gfs_quarter_deg_to_hourly_mean
   reference_forecasts.models.nam_12km_hourly_to_hourly_instantaneous
   reference_forecasts.models.nam_12km_cloud_cover_to_hourly_mean

Probabilistic NWP models
------------------------

.. autosummary::
   :toctree: generated/

   reference_forecasts.models.gefs_half_deg_to_hourly_mean

Forecast processing
-------------------

Functions that process forecast data.

.. autosummary::
   :toctree: generated/

   reference_forecasts.forecast.cloud_cover_to_ghi_linear
   reference_forecasts.forecast.cloud_cover_to_irradiance_ghi_clear
   reference_forecasts.forecast.cloud_cover_to_irradiance
   reference_forecasts.forecast.resample
   reference_forecasts.forecast.reindex_fill_slice
   reference_forecasts.forecast.unmix_intervals
   reference_forecasts.forecast.sort_gefs_frame

Persistence
-----------

.. autosummary::
   :toctree: generated/

   reference_forecasts.persistence.persistence_scalar
   reference_forecasts.persistence.persistence_interval
   reference_forecasts.persistence.persistence_scalar_index


Fetching external data
======================

ARM
---

.. autosummary::
   :toctree: generated/

   io.fetch.arm.format_date
   io.fetch.arm.request_arm_file_list
   io.fetch.arm.list_arm_filenames
   io.fetch.arm.request_arm_file
   io.fetch.arm.retrieve_arm_dataset
   io.fetch.arm.extract_arm_variables
   io.fetch.arm.fetch_arm

NWP
---

.. autosummary::
   :toctree: generated/

   io.fetch.nwp.get_with_retries
   io.fetch.nwp.get_available_dirs
   io.fetch.nwp.check_next_inittime
   io.fetch.nwp.get_filename
   io.fetch.nwp.files_to_retrieve
   io.fetch.nwp.process_grib_to_netcdf
   io.fetch.nwp.optimize_netcdf
   io.fetch.nwp.sleep_until_inittime
   io.fetch.nwp.startup_find_next_runtime
   io.fetch.nwp.next_run_time
   io.fetch.nwp.run
   io.fetch.nwp.optimize_only
   io.fetch.nwp.check_wgrib2

DOE RTC
-------

.. autosummary::
   :toctree: generated/

   io.fetch.rtc.request_doe_rtc_data
   io.fetch.rtc.fetch_doe_rtc

Reference observations
----------------------

.. autosummary::
   :toctree: generated/

   io.reference_observations.common
   io.reference_observations.crn
   io.reference_observations.midc_config
   io.reference_observations.midc
   io.reference_observations.reference_data
   io.reference_observations.rtc
   io.reference_observations.solrad
   io.reference_observations.srml
   io.reference_observations.surfrad

SFA API
=======

Token
-----

Get an API token.

.. autosummary::
   :toctree: generated/

   io.api.request_cli_access_token

API Session
-----------

Class for communicating with the Solar Forecast Arbiter API.

.. autosummary::
   :toctree: generated/

   io.api.APISession
   io.api.APISession.request

Sites

.. autosummary::
   :toctree: generated/

   io.api.APISession.get_site
   io.api.APISession.list_sites
   io.api.APISession.create_site

Observations

.. autosummary::
   :toctree: generated/

   io.api.APISession.get_observation
   io.api.APISession.list_observations
   io.api.APISession.create_observation
   io.api.APISession.get_observation_values
   io.api.APISession.post_observation_values

Forecasts

.. autosummary::
   :toctree: generated/

   io.api.APISession.get_forecast
   io.api.APISession.list_forecasts
   io.api.APISession.create_forecast
   io.api.APISession.get_forecast_values
   io.api.APISession.post_forecast_values

Probabilistic Forecasts
-----------------------

.. autosummary::
   :toctree: generated/

   io.api.APISession.get_probabilistic_forecast
   io.api.APISession.list_probabilistic_forecasts
   io.api.APISession.create_probabilistic_forecast
   io.api.APISession.get_probabilistic_forecast_constant_value
   io.api.APISession.get_probabilistic_forecast_constant_value_values
   io.api.APISession.post_probabilistic_forecast_constant_value_values

Utils
-----

Utility functions for data IO.

.. autosummary::
   :toctree: generated/

   io.utils.observation_df_to_json_payload
   io.utils.forecast_object_to_json
   io.utils.json_payload_to_observation_df
   io.utils.json_payload_to_forecast_series
   io.utils.adjust_start_end_for_interval_label
   io.utils.adjust_timeseries_for_interval_label
   io.utils.ensure_timestamps


Metrics
=======

Entry points for calculating metrics for
:py:class:`~solarforecastarbiter.datamodel.Forecast` and
:py:class:`~solarforecastarbiter.datamodel.Observation`:

.. autosummary::
   :toctree: generated/

   metrics.calculator.calculate_metrics_for_processed_pairs
   metrics.calculator.calculate_metrics

Functions for preparing the timeseries data before calculating metrics:

.. autosummary::
   :toctree: generated/

   metrics.preprocessing.apply_validation
   metrics.preprocessing.resample_and_align
   metrics.preprocessing.exclude

Functions to compute forecast deterministic performance metrics:

.. autosummary::
   :toctree: generated/

   metrics.deterministic.mean_absolute
   metrics.deterministic.mean_bias
   metrics.deterministic.root_mean_square
   metrics.deterministic.normalized_root_mean_square
   metrics.deterministic.centered_root_mean_square
   metrics.deterministic.mean_absolute_percentage
   metrics.deterministic.forecast_skill
   metrics.deterministic.pearson_correlation_coeff
   metrics.deterministic.coeff_determination


Reports
=======

.. autosummary::
   :toctree: generated/

   reports


Validation
==========

Validator
---------

Functions to perform validation.

.. autosummary::
   :toctree: generated/

   validation.validator.check_ghi_limits_QCRad
   validation.validator.check_dhi_limits_QCRad
   validation.validator.check_dni_limits_QCRad
   validation.validator.check_irradiance_limits_QCRad
   validation.validator.check_irradiance_consistency_QCRad
   validation.validator.check_temperature_limits
   validation.validator.check_wind_limits
   validation.validator.check_rh_limits
   validation.validator.check_ghi_clearsky
   validation.validator.check_poa_clearsky
   validation.validator.check_irradiance_day_night
   validation.validator.check_timestamp_spacing
   validation.validator.detect_stale_values
   validation.validator.detect_interpolation
   validation.validator.detect_levels
   validation.validator.detect_clipping
   validation.validator.detect_clearsky_ghi


Tasks
-----

Perform a sequence of validation steps. Used by the API to initiate validation.

.. autosummary::
   :toctree: generated/

   validation.tasks.validate_ghi
   validation.tasks.validate_dni
   validation.tasks.validate_dhi
   validation.tasks.validate_poa_global
   validation.tasks.validate_air_temperature
   validation.tasks.validate_wind_speed
   validation.tasks.validate_relative_humidity
   validation.tasks.validate_timestamp
   validation.tasks.validate_daily_ghi
   validation.tasks.validate_daily_dc_power
   validation.tasks.validate_daily_ac_power
   validation.tasks.immediate_observation_validation
   validation.tasks.daily_single_observation_validation
   validation.tasks.daily_observation_validation


Quality flag mapping
--------------------

Functions to handle the translation of validation results and database storage.

.. autosummary::
   :toctree: generated/

   validation.quality_mapping.convert_bool_flags_to_flag_mask
   validation.quality_mapping.mask_flags
   validation.quality_mapping.has_data_been_validated
   validation.quality_mapping.get_version
   validation.quality_mapping.check_if_single_value_flagged
   validation.quality_mapping.which_data_is_ok
   validation.quality_mapping.check_for_all_descriptions
   validation.quality_mapping.convert_mask_into_dataframe
   validation.quality_mapping.convert_flag_frame_to_strings
   validation.quality_mapping.check_if_series_flagged



Plotting
========

Timeseries
----------

Time series plotting.

.. autosummary::
   :toctree: generated/

   plotting.timeseries.build_figure_title
   plotting.timeseries.make_quality_bars
   plotting.timeseries.add_hover_tool
   plotting.timeseries.make_basic_timeseries
   plotting.timeseries.generate_forecast_figure
   plotting.timeseries.generate_observation_figure

Utils
-----

Utility functions for plotting.

.. autosummary::
   :toctree: generated/

   plotting.utils.format_variable_name
   plotting.utils.align_index
   plotting.utils.line_or_step
