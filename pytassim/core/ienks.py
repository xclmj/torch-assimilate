#!/bin/env python
# -*- coding: utf-8 -*-
#
# Created on 26.12.20
#
# Created for torch-assimilate
#
# @author: Tobias Sebastian Finn, tobias.sebastian.finn@uni-hamburg.de
#
#    Copyright (C) {2020}  {Tobias Sebastian Finn}


# System modules
import logging
from typing import Union, Tuple

# External modules
import torch

# Internal modules
from .base import BaseModule
from .utils import svd, rev_svd, matrix_product, diagonal_add


logger = logging.getLogger(__name__)


class IEnKSTransformModule(BaseModule):
    """
    The core module for the transform version of the Iterative Ensemble
    Kalman Smoother (IEnKS).
    This version of the IEnKS uses a learning rate :math:`\\tau` to mitigate
    sampling errors within the linearized observation operator.
    """
    def __init__(
            self,
            tau: Union[torch.Tensor, torch.nn.Parameter] = torch.tensor(1.0)
    ):
        super().__init__()
        self.tau = tau

    def __str__(self) -> str:
        return 'TransformModule(tau={0})'.format(self.tau)

    def __repr__(self) -> str:
        return 'TransformModule'

    @staticmethod
    def _split_weights(
            weights: torch.Tensor,
            ens_size: int
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        weights_deviation = diagonal_add(weights, -1.)
        weights_mean = weights_deviation.mean(dim=1, keepdim=True)
        weights_perts = weights - weights_mean
        return weights_mean, weights_perts

    def _decompose_weights(
            self,
            weights: torch.Tensor,
            ens_size: int,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        w_mean, w_perts = self._split_weights(weights, ens_size)
        u, s, v = svd(w_perts)
        s_inv = 1 / s
        s_prec = s_inv.square()
        w_perts_inv = rev_svd(u, s_inv, v).transpose(-1, -2)
        w_prec = rev_svd(u, s_prec, u) * (ens_size - 1)
        return w_mean, w_perts_inv, w_prec

    def _get_dh_dw(
            self,
            normed_perts: torch.Tensor,
            weights_perts_inv: torch.Tensor
    ) -> torch.Tensor:
        dh_dw = torch.matmul(weights_perts_inv, normed_perts)
        return dh_dw

    def _get_gradient(
            self,
            w_mean: torch.Tensor,
            dh_dw: torch.Tensor,
            normed_obs: torch.Tensor,
            ens_size: int
    ) -> torch.Tensor:
        dlobs_dh = -normed_obs
        grad_obs = matrix_product(dh_dw, dlobs_dh)
        grad_back = (ens_size - 1) * w_mean
        grad = grad_back + grad_obs
        return grad

    def _update_covariance(
            self,
            w_prec: torch.Tensor,
            dh_dw: torch.Tensor,
            ens_size: int,
    ):
        new_prec = matrix_product(dh_dw, dh_dw)
        new_prec = diagonal_add(new_prec, ens_size-1.)
        updated_prec = (1-self.tau) * w_prec + self.tau * new_prec
        u, s, v = svd(updated_prec, reg_value=0.0)
        s_inv = 1 / s
        weights_cov = rev_svd(u, s_inv, v)
        s_perts = (s_inv * (ens_size - 1)).sqrt()
        weights_perts = rev_svd(u, s_perts, v)
        return weights_cov, weights_perts

    def _update_weights(
            self,
            weights: torch.Tensor,
            normed_perts: torch.Tensor,
            normed_obs: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        ens_size = weights.shape[-2]

        w_mean, w_perts_inv, w_prec = self._decompose_weights(
            weights, ens_size
        )
        dh_dw = self._get_dh_dw(normed_perts, w_perts_inv)
        grad = self._get_gradient(w_mean, dh_dw, normed_obs, ens_size)
        w_cov, w_perts = self._update_covariance(w_prec, dh_dw, ens_size)
        delta_weight = torch.matmul(w_cov, grad)
        w_mean = w_mean - self.tau * delta_weight
        return w_mean, w_perts

    def forward(
            self,
            weights: torch.Tensor,
            normed_perts: torch.Tensor,
            normed_obs: torch.Tensor
    ) -> torch.Tensor:
        self._test_sizes(normed_perts, normed_obs)
        weights = self._view_as_2d(weights)
        if normed_perts.shape[-1] > 0:
            normed_perts = self._view_as_2d(normed_perts)
            normed_obs = self._view_as_2d(normed_obs)
            w_mean, w_perts = self._update_weights(
                weights, normed_perts, normed_obs
            )
            weights = w_mean + w_perts
        return weights


class IEnKSBundleModule(IEnKSTransformModule):
    """
    The core for the bundle version of the Iterative Ensemble Kalman Smoother (
    IEnKS) with :math:`\\epsilon` as parameter.
    """
    def __init__(
            self,
            epsilon: Union[torch.Tensor, torch.nn.Parameter] =
                torch.tensor(1E-4),
            tau: Union[torch.Tensor, torch.nn.Parameter] = torch.tensor(1.0)
    ):
        super().__init__(tau=tau)
        self.epsilon = epsilon

    def __str__(self):
        return 'IEnKSBundleModule(eps={0}, tau={1}'.format(
            str(self.epsilon), str(self.tau)
        )

    def __repr__(self):
        return 'IEnKSBundle({0}, {1})'.format(
            repr(self.epsilon), repr(self.tau)
        )

    def _get_dh_dw(
            self,
            normed_perts: torch.Tensor,
            weights_perts_inv: torch.Tensor
    ) -> torch.Tensor:
        dh_dw = normed_perts / self.epsilon
        return dh_dw
