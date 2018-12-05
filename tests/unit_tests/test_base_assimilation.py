#!/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 12/5/18

Created for torch-assimilate

@author: Tobias Sebastian Finn, tobias.sebastian.finn@uni-hamburg.de

    Copyright (C) {2018}  {Tobias Sebastian Finn}

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
# System modules
import unittest
import logging
import os
from unittest.mock import patch, PropertyMock
import warnings

# External modules
import xarray as xr

# Internal modules
from pytassim.assimilation.base import BaseAssimilation
from pytassim.state import StateError
from pytassim.observation import ObservationError


logging.basicConfig(level=logging.DEBUG)

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(os.path.dirname(BASE_PATH), 'data')


def dummy_update(state, observations, analysis_time):   # pragma: no cover
    return state.sel(time=(analysis_time, ))


class TestBaseAssimilation(unittest.TestCase):
    def setUp(self):
        self.algorithm = BaseAssimilation()
        state_path = os.path.join(DATA_PATH, 'test_state.nc')
        self.state = xr.open_dataarray(state_path)
        obs_path = os.path.join(DATA_PATH, 'test_single_obs.nc')
        self.obs = xr.open_dataset(obs_path)

    def test_validate_state_calls_valid_from_state(self):
        with patch('pytassim.state.ModelState.valid',
                   new_callable=PropertyMock) as mock_state_valid:
            self.algorithm._validate_state(self.state)
        mock_state_valid.assert_called_once()

    def test_validate_state_raises_state_error_if_not_valid(self):
        self.state = self.state.rename(var_name='var_test')
        with self.assertRaises(StateError) as e:
            self.algorithm._validate_state(self.state)

    def test_validate_state_raises_type_error_if_not_dataarray(self):
        with self.assertRaises(TypeError):
            self.algorithm._validate_state(self.state.values)

    def test_validate_single_obs_calls_valid_from_obs(self):
        with patch('pytassim.observation.Observation.valid',
                   new_callable=PropertyMock) as mock_obs_valid:
            self.algorithm._validate_single_obs(self.obs)
            mock_obs_valid.assert_called_once()

    def test_validate_single_obs_raises_obs_error(self):
        self.obs = self.obs.rename(obs_grid_1='obs_grid')
        with self.assertRaises(ObservationError) as e:
            self.algorithm._validate_single_obs(self.obs)

    def test_validate_single_obs_tests_type(self):
        with self.assertRaises(TypeError) as e:
            self.algorithm._validate_single_obs(self.obs['observations'])

    def test_validate_multi_observations_calls_valid_single_obs(self):
        observations = (self.obs, self.obs)
        with patch('pytassim.assimilation.base.BaseAssimilation.'
                   '_validate_single_obs') as single_obs_patch:
            self.algorithm._validate_observations(observations)
            self.assertEqual(single_obs_patch.call_count, 2)

    def test_validate_single_observations_calls_valid_single_obs(self):
        with patch('pytassim.assimilation.base.BaseAssimilation.'
                   '_validate_single_obs') as single_obs_patch:
            self.algorithm._validate_observations(self.obs)
        single_obs_patch.assert_called_once_with(self.obs)

    def test_get_analysis_time_uses_analysis_time_if_valid(self):
        valid_time = self.state.time[-1]
        returned_time = self.algorithm._get_analysis_time(
            self.state, analysis_time=valid_time
        )
        xr.testing.assert_equal(valid_time, returned_time)

    def test_get_analysis_time_return_latest_time_if_none(self):
        valid_time = self.state.time[-1]
        returned_time = self.algorithm._get_analysis_time(
            self.state, analysis_time=None
        )
        xr.testing.assert_equal(valid_time, returned_time)

    def test_get_analysis_returns_nearest_time_if_not_valid(self):
        valid_time = self.state.time[0]
        with self.assertWarns(UserWarning) as w:
            returned_time = self.algorithm._get_analysis_time(
                self.state, analysis_time='1991'
            )
        xr.testing.assert_equal(valid_time, returned_time)

    @patch('pytassim.assimilation.base.BaseAssimilation.update_state',
           side_effect=dummy_update)
    def test_assimilate_uses_latest_state_time(self, update_mock):
        pass

    def test_assimilate_validates_state(self):
        pass

    def test_assimilate_validates_observations(self):
        pass

    def test_assimilate_calls_update_state(self):
        pass

    def test_assimilate_validates_analysis(self):
        pass


if __name__ == '__main__':
    unittest.main()
