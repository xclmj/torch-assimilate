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
import types
from inspect import signature

# External modules
from xarray import register_dataset_accessor

# Internal modules


logger = logging.getLogger(__name__)


class ObservationError(Exception):  # pragma: no cover
    """
    This error is an error if given observation is not valid or if there is
    something strange with the observations.
    """
    pass


@register_dataset_accessor('obs')
class Observation(object):
    """
    This class represents an observation subset. Within an observation subset,
    the observations can be spatial correlated. Different observation subsets
    are per definition uncorrelated. This class is registered under
    :py:attr:`xarray.Dataset.obs`, where the here defined attributes and methods
    can be accessed. The assimilation algorithms will use the abstract method
    :py:meth:`xarray.Dataset.obs.operator` to convert the given model field into
    an observation equivalent. Thus, the `operator` method needs to be
    overwritten for every observation subset independently.

    Arguments
    ---------
    xr_ds : :py:class:`~xarray.Dataset`
        This :py:class:`~xarray.Dataset` is used for the observation operator.
        The dataset needs two variables:

            observations
                (time, obs_grid_1), the actual observations

            covariance
                (obs_grid_1, obs_grid_2), the covariance between different
                observations

        ``obs_grid_1`` and ``obs_grid_2`` are the same, but due to internals of
        xarray they are saved under different coordinates. It is possible to
        define different observation times within the `time` coordinate of the
        given :py:class:`~xarray.Dataset`.

    Warnings
    --------
    **To use this observation subset, you need to overwrite the observation
    operator**
    """
    def __init__(self, xr_ds):
        self.ds = xr_ds

    @property
    def _valid_dims(self):
        """
        Checks if ``time``, ``obs_grid_1`` and ``obs_grid_2`` are available
        within the :py:class:`~xarray.Dataset`.

        Returns
        -------
        keys_avail : bool
            If the dimensions are available.
        """
        necessary_dims = (
            'time', 'obs_grid_1', 'obs_grid_2'
        )
        keys_avail = all(
            True if d in tuple(self.ds.dims.keys()) else False
            for d in necessary_dims
        )
        return keys_avail

    @property
    def _valid_obs(self):
        """
        Checks if dimensions of the ``observation``
        :py:class:`~xarray.DataArray` within the set dataset are valid.

        Returns
        -------
        valid_obs : bool
            If the ``observation`` :py:class:`~xarray.DataArray` is valid.
        """
        valid_dims = ('time', 'obs_grid_1')
        valid_obs = valid_dims == self.ds['observations'].dims[-2:]
        return valid_obs

    @property
    def _valid_cov(self):
        """
        Checks if shape and dimensions of the ``covariance``
        :py:class:`~xarray.DataArray` within the set dataset are valid.

        Returns
        -------
        valid_cov : bool
            If the ``covariance`` :py:class:`~xarray.DataArray` is valid.
        """
        dim_order = ('obs_grid_1', 'obs_grid_2')
        checked_dims = dim_order == self.ds['covariance'].dims[-2:]

        obs_grid_len = self.ds['observations'].shape[-1]
        valid_shape = (obs_grid_len, obs_grid_len)
        checked_shape = valid_shape == self.ds['covariance'].shape

        try:
            checked_coord_values = self.ds['obs_grid_1'].to_index().equals(
                self.ds['obs_grid_2'].to_index()
            )
        except KeyError:
            checked_coord_values = False

        valid_cov = checked_dims and checked_shape and checked_coord_values
        return valid_cov

    @property
    def _valid_arrays(self):
        """
        Checks if ``observations`` and ``covariance``
        :py:class:`~xarray.DataArray`s within the set dataset are valid.

        Returns
        -------
        valid_arrays : bool
            If the two :py:class:`~xarray.DataArray`s are valid.
        """
        try:
            valid_array = self._valid_obs and self._valid_cov
        except KeyError:
            valid_array = False
        return valid_array

    @property
    def valid(self):
        """
        Checks if set :py:class:`~xarray.Dataset` is valid.

        Returns
        -------
        valid_ds : bool
            If set :py:class:`~xarray.Dataset` is valid.
        """
        valid_ds = False
        if self._valid_dims and self._valid_arrays:
            valid_ds = True
        return valid_ds

    def _operator(self, state):
        raise NotImplementedError('No observation operator is set!')

    @property
    def operator(self):
        """
        This method is used as observation operator within the assimilation
        algorithms. **If you overwrite this method, please take care of the
        in- and output!**

        Parameters
        ----------
        state : :py:class:`~xarray.DataArray`
            The pseudo observations are created based on this state. The given
            state needs to be valid.

        Returns
        -------
        pseudo_obs : :py:class:`~xarray.DataArray`
            The created pseudo observations based on the given state and this
            observation operator. The last two dimensions are the same
            dimensions as the ``observations`` :py:class:`~xarray.DataArray`
            in set observation subset.
        """
        return self._operator

    @operator.setter
    def operator(self, new_operator):
        if len(signature(new_operator).parameters) != 2:
            raise ValueError('Only ``self`` and ``state`` should be arguments '
                             'within the observation operator!')
        self._operator = types.MethodType(new_operator, self)