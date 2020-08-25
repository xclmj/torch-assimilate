#!/bin/env python
# -*- coding: utf-8 -*-
#
# Created on 03.08.20
#
# Created for 20_kernel_etkf
#
# @author: Tobias Sebastian Finn, tobias.sebastian.finn@uni-hamburg.de
#
#    Copyright (C) {2020}  {Tobias Sebastian Finn}
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

# External modules
import torch
import torch.nn

# Internal modules
from .base_kernels import BaseKernel
from .utils import dot_product


logger = logging.getLogger(__name__)


class TanhKernel(BaseKernel):
    def __init__(self, coeff=1., const=0.):
        super().__init__()
        self.coeff = coeff
        self.const = const

    def forward(self, x, y):
        xy = dot_product(x, y)
        logit = self.coeff * xy + self.const
        kernel_mat = torch.tanh(logit)
        return kernel_mat
