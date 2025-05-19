#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Market Impact Model
------------------
Estimates market impact for orders using the Almgren-Chriss model.

"""

import numpy as np
import pandas as pd
import logging

class MarketImpactModel:
    """Model for estimating market impact using Almgren-Chriss model."""
    
    def __init__(self, sigma=0.3, daily_volume=1000000, participation_rate=0.1):
        """
        Initialize the market impact model.
        
        Args:
            sigma (float): Volatility of the asset
            daily_volume (float): Average daily trading volume
            participation_rate (float): Participation rate in the market
        """
        self.sigma = sigma
        self.daily_volume = daily_volume
        self.participation_rate = participation_rate
        self.logger = logging.getLogger(__name__)
        
    def calculate_temporary_impact(self, order_size, current_price):
        """
        Calculate temporary market impact.
        
        Args:
            order_size (float): Size of the order
            current_price (float): Current price of the asset
            
        Returns:
            float: Temporary market impact
        """
        # Simplified Almgren-Chriss temporary impact formula
        impact_factor = 0.1  # Placeholder for impact factor
        return impact_factor * self.sigma * current_price * np.sqrt(order_size / self.daily_volume)
        
    def calculate_permanent_impact(self, order_size, current_price):
        """
        Calculate permanent market impact.
        
        Args:
            order_size (float): Size of the order
            current_price (float): Current price of the asset
            
        Returns:
            float: Permanent market impact
        """
        # Simplified Almgren-Chriss permanent impact formula
        impact_factor = 0.1  # Placeholder for impact factor
        return impact_factor * current_price * (order_size / self.daily_volume)
        
    def calculate_total_impact(self, order_size, current_price):
        """
        Calculate total market impact.
        
        Args:
            order_size (float): Size of the order
            current_price (float): Current price of the asset
            
        Returns:
            float: Total market impact
        """
        temp_impact = self.calculate_temporary_impact(order_size, current_price)
        perm_impact = self.calculate_permanent_impact(order_size, current_price)
        
        self.logger.info(f"Calculated market impact: temp={temp_impact}, perm={perm_impact}")
        return temp_impact + perm_impact