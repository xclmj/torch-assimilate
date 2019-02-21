#!/bin/env python
# -*- coding: utf-8 -*-
#
# Created on 14.03.18
#
# Created for torch-assimilate
#
# @author: Tobias Sebastian Finn, tobias.sebastian.finn@uni-hamburg.de
#
#    Copyright (C) {2018}  {Tobias Sebastian Finn}
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# System modules
import logging
import abc
import warnings
import time
import datetime

# External modules
import xarray as xr
import numpy as np
import scipy.linalg
import pandas as pd
import torch

# Internal modules
from pytassim.state import StateError
from pytassim.observation import ObservationError


logger = logging.getLogger(__name__)


class BaseAssimilation(object):
    """
    BaseAssimilation is used as base class for all assimilation algorithms for
    fast prototyping of assimilation prototyping. To implement a data
    assimilation, one needs to overwrite
    :py:meth:`~pytassim.assimilation.base.BaseAssimilation.update_state`.
    """
    def __init__(self, smoother=False, gpu=False, pre_transform=None,
                 post_transform=None):
        self.smoother = smoother
        self.gpu = gpu
        self.pre_transform = pre_transform
        self.post_transform = post_transform
        self.dtype = torch.double
        self._correlated = True

    def _states_to_torch(self, *states):
        if self.gpu:
            torch_states = [torch.tensor(s, dtype=self.dtype).cuda()
                            for s in states]
        else:
            torch_states = [torch.tensor(s, dtype=self.dtype)
                            for s in states]
        return torch_states

    @staticmethod
    def _validate_state(state):
        if not isinstance(state, xr.DataArray):
            raise TypeError('*** Given state is not a valid '
                            '``xarray.DataArray`` ***\n{0:s}'.format(state))
        if not state.state.valid:
            err_msg = '*** Given state is not a valid state ***\n{0:s}'
            raise StateError(err_msg.format(str(state)))

    def _validate_single_obs(self, observation):
        if not isinstance(observation, xr.Dataset):
            raise TypeError('*** Given observation is not a valid'
                            '``xarray.Dataset`` ***\n{0:s}'.format(observation))
        if not observation.obs.valid:
            err_msg = '*** Given observation is not a valid observation ***' \
                      '\n{0:s}'
            raise ObservationError(err_msg.format(str(observation)))
        if observation.obs.correlated != self._correlated:
            err_msg = '*** The correlation of the observation {0:s} is not ' \
                      'the same as the asked correlation of this ' \
                      'assimilation algorithm (asked: {1:s}, actual: {2:s}) ***'
            raise ObservationError(
                err_msg.format(str(observation), str(self._correlated),
                               str(observation.obs.correlated))
            )

    def _validate_observations(self, observations):
        if isinstance(observations, (list, set, tuple)):
            for obs in observations:
                self._validate_single_obs(obs)
        else:
            self._validate_single_obs(observations)

    @staticmethod
    def _get_analysis_time(state, analysis_time=None):
        if analysis_time is None:
            valid_time = state.time[-1]
        else:
            try:
                valid_time = state.time.sel(time=analysis_time, method=None)
            except KeyError:
                valid_time = state.time.sel(time=analysis_time,
                                            method='nearest')
                warnings.warn(
                    'Given analysis time {0:s} is not within state, used '
                    'instead nearest neighbor {1:s}'.format(
                        str(analysis_time), str(valid_time.values)
                    ),
                    category=UserWarning
                )
        return valid_time.values

    @staticmethod
    def _apply_obs_operator(state, observations):
        """
        This method applies the observation operator on given state. The
        observation operator has to be set within given observations. It is
        possible to overwrite this method to implement an own observation
        operator, which was not set in given observations.

        Parameters
        ----------
        state : :py:class:`xarray.DataArray`
            This state is used as base state to apply set observation operator.
        observations : iterable(:py:class:`xarray.Dataset`)
            These observations are used as basis for the observation operators.
            The observation operator should be set as method
            :py:meth:`xarray.Dataset.obs.operator`.

        Returns
        -------
        obs_equivalent : iterable(:py:class:`xarray.DataArray`)
            A list with observation equivalents as :py:class:`xarray.DataArray`.
            These observation equivalents have three dimensions, ``ensemble``,
            ``time`` and ``obs_grid``. The order within these observation
            equivalent is the same as in the observations.
        filtered_observations : list(:py:class:`xarray.Dataset`)
            These observations are filtered such that observations without an
            observation operator are dropped.
        """
        obs_equivalent = []
        filtered_observations = []
        for obs in observations:
            try:
                obs_equivalent.append(obs.obs.operator(state))
                filtered_observations.append(obs)
            except NotImplementedError:
                pass
        return obs_equivalent, filtered_observations

    def _prepare_obs(self, observations):
        state_stacked_list = []
        cov_stacked_list = []
        for obs in observations:
            if isinstance(obs.indexes['obs_grid_1'], pd.MultiIndex):
                obs['obs_grid_1'] = pd.Index(
                    obs.indexes['obs_grid_1'].values, tupleize_cols=False
                )
            stacked_obs = obs['observations'].stack(
                obs_id=('time', 'obs_grid_1')
            )
            len_time = len(obs.time)
            # Cannot use indexing or tiling due to possible rank deficiency
            stacked_cov = [obs['covariance'].values] * len_time
            if self._correlated:
                stacked_cov = scipy.linalg.block_diag(*stacked_cov)
            else:
                stacked_cov = np.concatenate(stacked_cov)
            state_stacked_list.append(stacked_obs)
            cov_stacked_list.append(stacked_cov)
        state_concat = xr.concat(state_stacked_list, dim='obs_id')
        state_values = state_concat.values
        state_grid = state_concat.obs_grid_1.values
        if self._correlated:
            state_covariance = scipy.linalg.block_diag(*cov_stacked_list)
        else:
            state_covariance = np.concatenate(cov_stacked_list)
        return state_values, state_covariance, state_grid

    @abc.abstractmethod
    def update_state(self, state, observations, analysis_time):
        """
        This method is called by
        :py:meth:`~pytassim.assimilation.base.BaseAssimilation.assimilate` and
        has to be overwritten to implement a data assimilation algorithm.

        Parameters
        ----------
        state : :py:class:`xarray.DataArray`
            This state is used to generate an observation-equivalent. It is
            further updated by this assimilation algorithm and given
            ``observation``. This :py:class:`~xarray.DataArray` should have
            four coordinates, which are specified in
            :py:class:`pytassim.state.ModelState`.
        observations : :py:class:`xarray.Dataset` or \
        iterable(:py:class:`xarray.Dataset`)
            These observations are used to update given state. An iterable of
            many :py:class:`xarray.Dataset` can be used to assimilate different
            variables. For the observation state, these observations are
            stacked such that the observation state contains all observations.
            The :py:class:`xarray.Dataset` are validated with
            :py:class:`pytassim.observation.Observation.valid`
        analysis_time : :py:class:`datetime.datetime`
            This analysis time determines at which point the state is updated.

        Returns
        -------
        analysis : :py:class:`xarray.DataArray`
            The analysed state based on given state and observations. The
            analysis has same coordinates as given ``state`` except ``time``,
            which should contain only one time step.
        """
        pass

    def assimilate(self, state, observations, analysis_time=None):
        """
        This assimilate the ``observations`` in given background ``state`` and
        creates an analysis for given ``analysis_time``. The observations need
        an observation operator, which translate given state into an
        observation-equivalent. The state, observations, observation covariance
        and and the observation-equivalent are used to update given state. This
        method validates given state and observations, gets analysis time and
        calls
        :py:meth:`~pytassim.assimilation.base.BaseAssimilation.update_state`.

        Parameters
        ----------
        state : :py:class:`xarray.DataArray`
            This state is used to generate an observation-equivalent. It is
            further updated by this assimilation algorithm and given
            ``observation``. This :py:class:`~xarray.DataArray` should have
            four coordinates, which are specified in
            :py:class:`pytassim.state.ModelState`.
        observations : :py:class:`xarray.Dataset` or \
        iterable(:py:class:`xarray.Dataset`)
            These observations are used to update given state. An iterable of
            many :py:class:`xarray.Dataset` can be used to assimilate different
            variables. For the observation state, these observations are
            stacked such that the observation state contains all observations.
            The :py:class:`xarray.Dataset` are validated with
            :py:class:`pytassim.observation.Observation.valid`
        analysis_time : :py:class:`datetime.datetime` or None, optional
            This analysis time determines at which point the state is updated.
            If the analysis time is None, than the last time point in given
            state is used.

        Returns
        -------
        analysis : :py:class:`xarray.DataArray`
            The analysed state based on given state and observations. The
            analysis has same coordinates as given ``state`` except ``time``,
            which contains only one time step.
        """
        start_time = time.time()
        logger.info('Starting assimilation')
        if isinstance(analysis_time, datetime.datetime):
            logger.info('Analysis time: {0:s}'.format(
                analysis_time.strftime('%Y-%m-%d %H:%M UTC')))
        if not observations:
            warnings.warn('No observation is given, I will return the '
                          'background state!', UserWarning)
            return state
        if not isinstance(observations, (list, set, tuple)):
            observations = (observations, )
        self._validate_state(state)
        self._validate_observations(observations)
        analysis_time = self._get_analysis_time(state, analysis_time)
        if self.smoother:
            back_state = state
        else:
            logger.info('Assimilation in non-smoother mode')
            back_state = state.sel(time=[analysis_time, ])
            observations = [obs.sel(time=[analysis_time, ])
                            for obs in observations]
        if self.pre_transform:
            for trans in self.pre_transform:
                back_state, observations = trans.pre(back_state, observations)
        logger.info('Finished with general preparation')
        analysis = self.update_state(back_state, observations, analysis_time)
        logger.info('Created the analysis, starting with post-processing')
        if self.post_transform:
            for trans in self.post_transform:
                analysis = trans.post(analysis, back_state, observations)
        self._validate_state(analysis)
        end_time = time.time()
        logger.info('Finished assimilation after {0:.2f} s'.format(
            end_time-start_time
        ))
        return analysis
