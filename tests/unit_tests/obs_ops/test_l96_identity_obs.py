#!/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 1/30/19

Created for torch-assimilate

@author: Tobias Sebastian Finn, tobias.sebastian.finn@uni-hamburg.de

    Copyright (C) {2019}  {Tobias Sebastian Finn}

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
import numpy as np
import torch

# Internal modules
from pytassim.obs_ops.lorenz_96.identity import IdentityOperator


logging.basicConfig(level=logging.INFO)

BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA_PATH = os.path.join(os.path.dirname(BASE_PATH), 'data')


class TestIdentityOps(unittest.TestCase):
    def setUp(self):
        state_path = os.path.join(DATA_PATH, 'test_state.nc')
        self.state = xr.open_dataarray(state_path)
        obs_path = os.path.join(DATA_PATH, 'test_single_obs.nc')
        self.obs = xr.open_dataset(obs_path)
        self.operator = IdentityOperator()

    def test_obs_points_returns_priv_obs_points(self):
        self.assertNotEqual(self.operator.obs_points, 10)
        self.operator._obs_points = 10
        self.assertEqual(self.operator.obs_points, 10)

    def test_obs_points_sets_lists(self):
        self.operator._obs_points = None
        self.operator.obs_points = [1, 2]
        self.assertListEqual(self.operator._sel_obs_points, [1, 2])

    def test_obs_points_sets_private(self):
        self.operator._obs_points = None
        self.operator.obs_points = [1, 2]
        self.assertListEqual(self.operator._obs_points, [1, 2])

    def test_obs_points_sets_np_arange_if_none(self):
        self.operator._obs_points = None
        self.operator.obs_points = None
        np.testing.assert_equal(self.operator._sel_obs_points,
                                np.arange(self.operator.len_grid),)

    def test_obs_points_sets_random(self):
        rnd = np.random.RandomState(10)
        drawn = rnd.choice(self.operator.len_grid, size=4, replace=False)
        rnd = np.random.RandomState(10)
        self.operator.random_state = rnd
        self.operator.obs_points = 4
        np.testing.assert_equal(self.operator._sel_obs_points, drawn)

    def test_obs_op_select_x_var(self):
        self.operator.obs_points = None
        pseudo_obs = self.state.sel(var_name='x')
        ret_obs = self.operator.obs_op(self.state)
        xr.testing.assert_equal(pseudo_obs, ret_obs)

    def test_obs_op_selects_sel_obs_points(self):
        self.operator.obs_points = [1, 2, 3]
        pseudo_obs = self.state.sel(var_name='x',
                                    grid=self.operator._sel_obs_points)
        ret_obs = self.operator.obs_op(self.state)
        xr.testing.assert_equal(pseudo_obs, ret_obs)

    def test_torch_operator_returns_same_as_obs_op(self):
        self.operator.obs_points = [1, 2, 3]
        pseudo_obs = self.operator.obs_op(self.state)
        pseudo_obs = pseudo_obs.values.reshape(-1, 3)

        torch_op = self.operator.torch_operator()
        torch_state = torch.from_numpy(self.state.sel(var_name='x').values)
        torch_state = torch_state.view(-1, self.operator.len_grid).float()
        ret_obs = torch_op(torch_state).numpy()

        np.testing.assert_almost_equal(ret_obs, pseudo_obs)

    def test_torch_operator_parameter_no_req_gradient(self):
        torch_op = self.operator.torch_operator()
        for param in torch_op.parameters():
            self.assertFalse(param.requires_grad)


if __name__ == '__main__':
    unittest.main()
