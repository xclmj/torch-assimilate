#!/bin/env python
# -*- coding: utf-8 -*-
#
# Created on 23.11.18
#
# Created for torch-assim
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

# External modules

# Internal modules


logger = logging.getLogger(__name__)


class BaseIntegrator(object):
    def __init__(self, model, dt):
        self._dt = None
        self._model = None
        self.model = model
        self.dt = dt

    @property
    def dt(self):
        return self._dt

    @dt.setter
    def dt(self, new_dt):
        self._dt = new_dt

    @abc.abstractmethod
    def _calc_inc(self, state):
        pass

    def integrate(self, state):
        pass