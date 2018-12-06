#!/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 12/6/18

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

# External modules
import xarray as xr

# Internal modules
from pytassim.assimilation.base import BaseAssimilation
import pytassim.testing.dummy as utils


logging.basicConfig(level=logging.DEBUG)

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(os.path.dirname(BASE_PATH), 'data')


class TestTestingUtilities(unittest.TestCase):
    def setUp(self):
        state_path = os.path.join(DATA_PATH, 'test_state.nc')
        self.state = xr.open_dataarray(state_path)
        obs_path = os.path.join(DATA_PATH, 'test_single_obs.nc')
        self.obs = xr.open_dataset(obs_path)

    def test_dummy_update_returns_sliced_date(self):
        assimilation = BaseAssimilation()
        ana_time = self.state.time[-1]
        sliced_state = self.state.isel(time=slice(-1, None))
        returned_state = utils.dummy_update_state(assimilation, self.state,
                                                  self.obs, ana_time)
        self.assertIsInstance(returned_state, xr.DataArray)
        xr.testing.assert_equal(sliced_state, returned_state)

    def test_dummy_obs_operator_returns_pseudo_obs(self):
        pseudo_obs = self.state.sel(var_name='x')
        pseudo_obs = pseudo_obs.rename(grid='obs_grid_1')
        pseudo_obs['time'] = self.obs.time.values
        pseudo_obs['obs_grid_1'] = self.obs.obs_grid_1.values

        returned_pseudo_obs = utils.dummy_obs_operator(self.obs, self.state)

        xr.testing.assert_equal(pseudo_obs, returned_pseudo_obs)


if __name__ == '__main__':
    unittest.main()
