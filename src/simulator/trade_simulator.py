#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trade Simulator
--------------
Core execution engine for simulating cryptocurrency trades.
Integrates slippage, market impact, and fee models to provide
realistic trade execution estimates.
"""

import logging
from typing import Dict, Tuple, Optional

from src.models import SlippageModel, MarketImpactModel, MakerTakerModel

logger = logging.getLogger(__name__)

class TradeSimulator:
    """
    Trade execution simulator that integrates multiple models to estimate
    realistic trade execution costs and outcomes.
    """
    
    def __init__(self):
        """Initialize the trade simulator with required models."""
        self.slippage_model = SlippageModel()
        self.impact_model = MarketImpactModel()
        self.fee_model = MakerTakerModel()
        logger.info("Trade simulator initialized with all models")
        
    def simulate_trade(self, 
                      order_size: float, 
                      side: str, 
                      order_book: Dict) -> Dict:
        """
        Simulate a trade execution with the current order book state.
        
        Args:
            order_size: Size of the order in base currency (e.g., BTC)
            side: Order side ('buy' or 'sell')
            order_book: Dictionary containing 'bids' and 'asks' as lists of (price, quantity) tuples
            
        Returns:
            Dict: Execution results including:
                - executed_price: Final price after slippage
                - slippage_pct: Estimated slippage percentage
                - impact_bps: Market impact in basis points
                - fee_pct: Fee percentage applied
                - net_price: Net effective price after all costs
                - total_cost: Total cost in quote currency
        """
        if not self._validate_inputs(order_size, side, order_book):
            return self._create_error_result()
            
        # Get base price (mid price)
        best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
        best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
        mid_price = (best_bid + best_ask) / 2
        
        # Estimate slippage
        slippage_pct = self.slippage_model.estimate(order_size, side, order_book)
        
        # Calculate executed price after slippage
        if side.lower() == 'buy':
            executed_price = mid_price * (1 + slippage_pct/100)
        else:  # sell
            executed_price = mid_price * (1 - slippage_pct/100)
            
        # Estimate market impact
        impact_bps = self.impact_model.estimate(order_size, side, order_book)
        
        # Estimate fee
        fee_pct = self.fee_model.estimate(order_size, side, order_book)
        
        # Calculate net price after all costs
        if side.lower() == 'buy':
            # For buys: higher price = worse, so add impact and fees
            net_price = executed_price * (1 + impact_bps/10000) * (1 + fee_pct/100)
            total_cost = net_price * order_size
        else:  # sell
            # For sells: lower price = worse, so subtract impact and fees
            net_price = executed_price * (1 - impact_bps/10000) * (1 - fee_pct/100)
            total_cost = net_price * order_size
            
        # Log the simulation results
        logger.info(f"Trade simulation results for {order_size} {side}:")
        logger.info(f"  Executed price: {executed_price:.2f}")
        logger.info(f"  Slippage: {slippage_pct:.3f}%")
        logger.info(f"  Market impact: {impact_bps:.2f} bps")
        logger.info(f"  Fee: {fee_pct:.4f}%")
        logger.info(f"  Net price: {net_price:.2f}")
        logger.info(f"  Total cost: {total_cost:.2f}")
        
        # Return the simulation results
        return {
            'executed_price': round(executed_price, 2),
            'slippage_pct': slippage_pct,
            'impact_bps': impact_bps,
            'fee_pct': fee_pct,
            'net_price': round(net_price, 2),
            'total_cost': round(total_cost, 2),
            'base_price': round(mid_price, 2),
            'best_bid': round(best_bid, 2),
            'best_ask': round(best_ask, 2)
        }
        
    def _validate_inputs(self, order_size: float, side: str, order_book: Dict) -> bool:
        """Validate the inputs for trade simulation."""
        # Check order size
        if order_size <= 0:
            logger.warning(f"Invalid order size: {order_size}")
            return False
            
        # Check side
        if side.lower() not in ['buy', 'sell']:
            logger.warning(f"Invalid order side: {side}")
            return False
            
        # Check order book
        if not order_book or 'bids' not in order_book or 'asks' not in order_book:
            logger.warning("Invalid order book data")
            return False
            
        # Check if order book has data
        if not order_book['bids'] or not order_book['asks']:
            logger.warning("Empty order book data")
            return False
            
        return True
        
    def _create_error_result(self) -> Dict:
        """Create an error result dictionary."""
        return {
            'executed_price': 0,
            'slippage_pct': 0,
            'impact_bps': 0,
            'fee_pct': 0,
            'net_price': 0,
            'total_cost': 0,
            'error': 'Invalid inputs for trade simulation'
        }