#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Strategy Package
--------------
Contains strategy implementations for the trading simulator.
"""

from .base_strategy import BaseStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .momentum_strategy import MomentumStrategy

__all__ = ['BaseStrategy', 'MeanReversionStrategy', 'MomentumStrategy']