#!/bin/env python
# -*- coding: utf-8 -*-
#
# Created on 21.12.20
#
# Created for torch-assimilate
#
# @author: Tobias Sebastian Finn, tobias.sebastian.finn@uni-hamburg.de
#
#    Copyright (C) {2020}  {Tobias Sebastian Finn}


# System modules
import logging
from typing import Union, Iterable

# External modules
import torch
import torch.nn

# Internal modules
from .letkf import LETKF
from ..core.ketkf import KETKFModule
from ..kernels.base_kernels import BaseKernel
from ..kernels.linear import LinearKernel
from ..localization.localization import BaseLocalization
from ..transform.base import BaseTransformer


logger = logging.getLogger(__name__)


class LKETKF(LETKF):
    """
    This is a kernelised implementation of the
    `localized ensemble transform Kalman filter` :cite:`hunt_efficient_2007`.
    This kernelised ensemble Kalman filter is a deterministic filter, where the
    state is globally updated. Ensemble weights are estimated in a reduced
    ensemble space, and then applied to a given state. This kernelised data
    assimilation can be used for non-linear observation operators. The
    observation operator is approximated by the ensemble and a given kernel.
    Furthermore, this implementation allows filtering in time and ensemble
    smoothing, similar to :cite:`hunt_four-dimensional_2004`. This LKETKF
    implementation is less efficient for a linear kernel than
    :py:class:`pytassim.interface.filter.etkf.LETKF`, which should be
    then used instead.

    Parameters
    ----------
    localization : obj or None, optional
        This localization is used to localize and constrain observations
        spatially. If this localization is None, no localization is applied such
        it is an inefficient version of the
        `kernelized ensemble transform Kalman filter`.
        Default value is None, indicating no localization at all.
    kernel : child of :py:class:`pytassim.kernels.base_kernels.BaseKernel`
        This kernel is used to estimate the ensemble distance matrix.
        If no child of :py:class:`pytassim.kernels.base_kernels.BaseKernel`
        is used, the kernel should have atleast a :py:func:`forward` method.
    inf_factor : float, optional
        Multiplicative inflation factor :math:`\\rho``, which is applied to the
        background precision. An inflation factor greater one increases the
        ensemble spread, while a factor less one decreases the spread. Default
        is 1.0, which is the same as no inflation at all.
    smoother : bool, optional
        Indicates if this filter should be run in smoothing or in filtering
        mode. In smoothing mode, no analysis time is selected from given state
        and the ensemble weights are applied to the whole state. In filtering
        mode, the weights are applied only on selected analysis time. Default
        is False, indicating filtering mode.
    gpu : bool, optional
        Indicator if the weight estimation should be done on either GPU (True)
        or CPU (False): Default is None. For small models, estimation of the
        weights on CPU is faster than on GPU!.
    """
    def __init__(
            self,
            localization: Union[None, BaseLocalization] = None,
            kernel: BaseKernel = LinearKernel(),
            inf_factor: Union[float, torch.Tensor, torch.nn.Parameter] = 1.0,
            smoother: bool = False,
            gpu: bool = False,
            pre_transform: Union[None, Iterable[BaseTransformer]] = None,
            post_transform: Union[None, Iterable[BaseTransformer]] = None,
            chunksize: int = 10,
    ):
        self._core_module = KETKFModule(kernel=kernel, inf_factor=inf_factor)
        super().__init__(
            localization=localization,
            inf_factor=inf_factor,
            smoother=smoother,
            gpu=gpu,
            pre_transform=pre_transform,
            post_transform=post_transform,
            chunksize=chunksize
        )
        self.kernel = kernel

    def __str__(self):
        return 'Localized KETKF(rho={0}, loc={1}, kernel={2})'.format(
            str(self.inf_factor), str(self.localization), str(self.kernel)
        )

    def __repr__(self):
        return 'LKETKF({0},{1},{2})'.format(
            repr(self.inf_factor), repr(self.localization), repr(self.kernel)
        )

    @property
    def inf_factor(self):
        return self._core_module.inf_factor

    @inf_factor.setter
    def inf_factor(self, new_factor):
        self._core_module = KETKFModule(
            inf_factor=new_factor, kernel=self.kernel
        )

    @property
    def kernel(self):
        return self._core_module.kernel

    @kernel.setter
    def kernel(self, new_kernel):
        self._core_module = KETKFModule(
            kernel=new_kernel, inf_factor=self.inf_factor
        )