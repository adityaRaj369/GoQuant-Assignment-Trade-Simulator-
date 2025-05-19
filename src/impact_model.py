#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Market Impact Model
------------------
Implementation of the Almgren-Chriss model for estimating market impact
of cryptocurrency trades.
"""

import logging
import math
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class MarketImpactModel:
    """
    Model for estimating market impact using the Almgren-Chriss model.
    
    Market impact is calculated as: Impact = γ * (order_quantity / ADV)^δ
    where γ and δ are tunable constants and ADV is the average daily volume.
    """
    
    def __init__(self, gamma: float = 0.1, delta: float = 0.5, adv: Optional[Dict[str, float]] = None):
        """
        Initialize the market impact model.
        
        Args:
            gamma: Constant factor in the Almgren-Chriss model (default: 0.1)
            delta: Exponent in the Almgren-Chriss model (default: 0.5)
            adv: Dictionary mapping asset symbols to their average daily volumes
        """
        self.gamma = gamma
        self.delta = delta
        
        # Default ADV values for common assets (in quote currency, e.g., USDT)
        self.adv = adv or {
            "BTC-USDT": 1000000000,  # $1B daily volume for BTC
            "ETH-USDT": 500000000,   # $500M daily volume for ETH
            "default": 100000000     # Default $100M for other assets
        }
        
        logger.info(f"Market impact model initialized with gamma={gamma}, delta={delta}")
    
    def calculate_impact(self, side: str, order_size: float, 
                        order_book: Dict[str, List[List[float]]], 
                        symbol: str = "default") -> float:
        """
        Calculate market impact for an order.
        
        Args:
            side: Order side ('buy' or 'sell')
            order_size: Size of the order in quote currency
            order_book: Order book with bids and asks
            symbol: Trading symbol (e.g., 'BTC-USDT')
            
        Returns:
            float: Market impact as a percentage
        """
        # Get ADV for the symbol
        adv = self.adv.get(symbol, self.adv["default"])
        
        # Calculate base impact using Almgren-Chriss model
        relative_size = order_size / adv
        base_impact_pct = self.gamma * (relative_size ** self.delta)
        
        # Adjust impact based on order book liquidity
        liquidity_factor = self._calculate_liquidity_factor(side, order_book)
        
        # Apply liquidity adjustment
        adjusted_impact = base_impact_pct * liquidity_factor
        
        logger.debug(f"Calculated market impact for {order_size} {side}: {adjusted_impact:.4f}%")
        return adjusted_impact
    
    def _calculate_liquidity_factor(self, side: str, order_book: Dict[str, List[List[float]]]) -> float:
        """
        Calculate a liquidity factor based on order book depth.
        
        Args:
            side: Order side ('buy' or 'sell')
            order_book: Order book with bids and asks
            
        Returns:
            float: Liquidity factor (higher means less liquidity, more impact)
        """
        # Get reference prices
        best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
        best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
        
        if best_bid <= 0 or best_ask <= 0:
            return 1.5  # Default factor for invalid prices
        
        # Calculate spread in basis points
        mid_price = (best_bid + best_ask) / 2
        spread_bps = ((best_ask - best_bid) / mid_price) * 10000
        
        # Calculate order book imbalance
        bid_liquidity = sum(qty for _, qty in order_book['bids'][:5])
        ask_liquidity = sum(qty for _, qty in order_book['asks'][:5])
        
        # Higher imbalance against the order side means more impact
        if side.lower() == 'buy':
            imbalance_factor = 1 + max(0, (bid_liquidity - ask_liquidity) / (bid_liquidity + ask_liquidity))
        else:  # sell
            imbalance_factor = 1 + max(0, (ask_liquidity - bid_liquidity) / (bid_liquidity + ask_liquidity))
        
        # Combine spread and imbalance factors
        # Wider spread and higher imbalance both increase impact
        spread_factor = 1 + (spread_bps / 100)  # Normalize spread effect
        liquidity_factor = spread_factor * imbalance_factor
        
        # Cap the factor at reasonable values
        liquidity_factor = min(max(0.5, liquidity_factor), 3.0)
        
        logger.debug(f"Liquidity factor: {liquidity_factor:.2f} (spread: {spread_bps:.2f} bps)")
        return liquidity_factor
    
    def estimate_permanent_impact(self, order_size: float, symbol: str = "default") -> float:
        """
        Estimate permanent market impact component.
        
        Args:
            order_size: Size of the order in quote currency
            symbol: Trading symbol (e.g., 'BTC-USDT')
            
        Returns:
            float: Permanent market impact as a percentage
        """
        adv = self.adv.get(symbol, self.adv["default"])
        permanent_factor = 0.1  # Permanent impact is typically a fraction of total impact
        
        permanent_impact = permanent_factor * self.gamma * (order_size / adv) ** self.delta
        
        return permanent_impact
    
    def estimate_temporary_impact(self, order_size: float, symbol: str = "default") -> float:
        """
        Estimate temporary market impact component.
        
        Args:
            order_size: Size of the order in quote currency
            symbol: Trading symbol (e.g., 'BTC-USDT')
            
        Returns:
            float: Temporary market impact as a percentage
        """
        adv = self.adv.get(symbol, self.adv["default"])
        temporary_factor = 0.9  # Temporary impact is typically the majority of total impact
        
        temporary_impact = temporary_factor * self.gamma * (order_size / adv) ** self.delta
        
        return temporary_impact
    
    def update_adv(self, symbol: str, new_adv: float):
        """
        Update the average daily volume for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT')
            new_adv: New average daily volume in quote currency
        """
        if new_adv <= 0:
            logger.warning(f"Invalid ADV value: {new_adv}")
            return
        
        self.adv[symbol] = new_adv
        logger.info(f"Updated ADV for {symbol}: {new_adv}")