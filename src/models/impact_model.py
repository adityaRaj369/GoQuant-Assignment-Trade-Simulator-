#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Market Impact Model
------------------
Estimates market impact for orders based on the Almgren-Chriss model.
"""

import logging
import math
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class MarketImpactModel:
    """
    Estimates market impact for orders based on the Almgren-Chriss model.
    
    Market impact is calculated as: impact = k * (quantity / ADV) ** alpha
    where k and alpha are tunable constants and ADV is the approximate daily volume.
    """
    
    def __init__(self, k: float = 0.1, alpha: float = 0.5, adv: float = 1000.0):
        """
        Initialize the market impact model.
        
        Args:
            k: Constant factor in the Almgren-Chriss model (default: 0.1)
            alpha: Exponent in the Almgren-Chriss model (default: 0.5)
            adv: Approximate daily volume in base currency (default: 1000 BTC)
        """
        self.k = k
        self.alpha = alpha
        self.adv = adv
        logger.info(f"Initializing MarketImpactModel with k={k}, alpha={alpha}, ADV={adv}")
    
    def estimate(self, order_size: float, side: str, order_book: dict) -> float:
        """
        Estimate market impact for a given order.
        
        Args:
            order_size: Size of the order in base currency (e.g., BTC)
            side: Order side ('buy' or 'sell')
            order_book: Dictionary containing 'bids' and 'asks' as lists of (price, quantity) tuples
            
        Returns:
            float: Estimated market impact in basis points (bps)
        """
        if order_size <= 0:
            logger.warning(f"Invalid order size: {order_size}")
            return 0.0
            
        # Calculate market impact using Almgren-Chriss model
        impact_pct = self.k * (order_size / self.adv) ** self.alpha
        
        # Convert percentage to basis points (1% = 100 bps)
        impact_bps = impact_pct * 100
        
        # Adjust impact based on order book depth (optional enhancement)
        # This is a simple adjustment based on the spread
        if order_book and 'bids' in order_book and 'asks' in order_book:
            best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
            best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
            
            if best_bid > 0 and best_ask > 0:
                spread_bps = ((best_ask - best_bid) / best_bid) * 10000  # Convert to bps
                # Wider spreads typically indicate less liquidity, which increases impact
                impact_bps *= (1 + (spread_bps / 1000))
        
        logger.debug(f"Estimated market impact for {order_size} {side}: {impact_bps} bps")
        return round(impact_bps, 2)