#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Execution Engine
--------------
Core execution logic for simulating cryptocurrency trades with
realistic market behavior, slippage, impact, and fees.
"""

import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Union

from src.slippage_model import SlippageModel
from src.impact_model import MarketImpactModel
from src.fee_model import MakerTakerFeeModel

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """
    Trade execution engine that simulates realistic order execution
    with slippage, market impact, and fees.
    """
    
    def __init__(self):
        """Initialize the execution engine with required models."""
        self.slippage_model = SlippageModel()
        self.impact_model = MarketImpactModel()
        self.fee_model = MakerTakerFeeModel()
        logger.info("Execution engine initialized with all models")
    
    def simulate_order_execution(self, 
                               side: str,
                               order_type: str,
                               order_quantity: float,
                               order_book: Dict[str, List[List[float]]],
                               order_price: Optional[float] = None,
                               latency: int = 0,
                               user_fee_profile: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Simulate order execution with realistic market behavior.
        
        Args:
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market' or 'limit')
            order_quantity: Size of the order in quote currency (e.g., USDT)
            order_book: Dictionary containing 'bids' and 'asks' as lists of [price, quantity]
            order_price: Limit price (required for limit orders)
            latency: Simulated network latency in milliseconds
            user_fee_profile: User's fee profile with maker and taker rates
            
        Returns:
            Dict: Execution results including executed quantity, price, slippage, impact, etc.
        """
        # Validate inputs
        if not self._validate_inputs(side, order_type, order_quantity, order_book, order_price):
            return self._create_error_result("Invalid input parameters")
        
        # Apply latency simulation if specified
        if latency > 0:
            order_book = self._apply_latency_simulation(order_book, latency)
        
        # Set default fee profile if not provided
        if user_fee_profile is None:
            user_fee_profile = {"maker": 0.06, "taker": 0.08}
        
        # Determine which side of the book to use
        book_side = 'asks' if side.lower() == 'buy' else 'bids'
        opposite_side = 'bids' if side.lower() == 'buy' else 'asks'
        
        # Get reference prices
        best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
        best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
        mid_price = (best_bid + best_ask) / 2
        
        # For limit orders, check if the order is marketable
        is_marketable = False
        if order_type.lower() == 'limit':
            if side.lower() == 'buy' and order_price >= best_ask:
                is_marketable = True
            elif side.lower() == 'sell' and order_price <= best_bid:
                is_marketable = True
        else:  # Market orders are always marketable
            is_marketable = True
        
        # Initialize execution variables
        executed_quantity_base = 0.0  # in base currency (e.g., BTC)
        executed_quantity_quote = 0.0  # in quote currency (e.g., USDT)
        remaining_quantity_quote = order_quantity
        execution_type = "fail"
        warnings = []
        
        # Walk the order book to simulate fills
        if is_marketable:
            execution_type = "taker"
            
            for level in order_book[book_side]:
                price, quantity = level
                
                # For limit orders, respect the limit price
                if order_type.lower() == 'limit':
                    if (side.lower() == 'buy' and price > order_price) or \
                       (side.lower() == 'sell' and price < order_price):
                        break
                
                # Calculate how much we can execute at this level
                if side.lower() == 'buy':
                    # For buy orders, we're spending quote currency (e.g., USDT)
                    max_executable_quote = price * quantity
                    executable_quote = min(remaining_quantity_quote, max_executable_quote)
                    executable_base = executable_quote / price
                else:
                    # For sell orders, we're selling base currency equivalent to quote value
                    executable_base = min(remaining_quantity_quote / price, quantity)
                    executable_quote = executable_base * price
                
                # Update execution totals
                executed_quantity_base += executable_base
                executed_quantity_quote += executable_quote
                remaining_quantity_quote -= executable_quote
                
                # Check if order is fully filled
                if remaining_quantity_quote <= 0.01:  # Small threshold to account for floating point errors
                    break
        
        elif order_type.lower() == 'limit':
            # Non-marketable limit order would be a maker order
            execution_type = "maker"
            # For simulation purposes, we'll assume it doesn't execute immediately
            warnings.append("Limit order placed but not immediately executed")
        
        # Check if we have a partial fill
        if 0 < executed_quantity_quote < order_quantity:
            execution_type = "partial"
            warnings.append(f"Order partially filled: {executed_quantity_quote:.2f}/{order_quantity:.2f} {execution_type}")
        
        # If no execution happened
        if executed_quantity_quote <= 0:
            return self._create_error_result("No execution: insufficient liquidity or non-marketable limit order")
        
        # Calculate average execution price
        average_price = executed_quantity_quote / executed_quantity_base if executed_quantity_base > 0 else 0
        
        # Calculate slippage
        slippage_pct = self.slippage_model.calculate_slippage(
            side, mid_price, average_price, executed_quantity_quote
        )
        
        # Calculate market impact
        impact_pct = self.impact_model.calculate_impact(
            side, executed_quantity_quote, order_book
        )
        
        # Calculate fee
        fee_rate = user_fee_profile["taker"] if execution_type == "taker" else user_fee_profile["maker"]
        fee_paid = self.fee_model.calculate_fee(
            executed_quantity_quote, fee_rate, execution_type
        )
        
        # Check for large impact warning
        if impact_pct > 1.0:  # More than 1% impact
            warnings.append(f"Large market impact: {impact_pct:.2f}%")
        
        # Prepare and return the result
        result = {
            "executed_quantity_base": round(executed_quantity_base, 8),
            "executed_quantity_quote": round(executed_quantity_quote, 2),
            "average_price": round(average_price, 2),
            "slippage_pct": round(slippage_pct, 2),
            "market_impact_pct": round(impact_pct, 2),
            "fee_paid": round(fee_paid, 2),
            "execution_type": execution_type,
            "warnings": warnings
        }
        
        logger.info(f"Execution result: {result}")
        return result
    
    def _validate_inputs(self, side: str, order_type: str, order_quantity: float, 
                        order_book: Dict, order_price: Optional[float]) -> bool:
        """Validate the inputs for order execution simulation."""
        # Check side
        if side.lower() not in ['buy', 'sell']:
            logger.warning(f"Invalid order side: {side}")
            return False
        
        # Check order type
        if order_type.lower() not in ['market', 'limit']:
            logger.warning(f"Invalid order type: {order_type}")
            return False
        
        # Check order quantity
        if order_quantity <= 0:
            logger.warning(f"Invalid order quantity: {order_quantity}")
            return False
        
        # Check order book
        if not order_book or 'bids' not in order_book or 'asks' not in order_book:
            logger.warning("Invalid order book data")
            return False
        
        # Check if order book has data
        if not order_book['bids'] or not order_book['asks']:
            logger.warning("Empty order book data")
            return False
        
        # Check order price for limit orders
        if order_type.lower() == 'limit' and (order_price is None or order_price <= 0):
            logger.warning(f"Invalid limit price: {order_price}")
            return False
        
        return True
    
    def _apply_latency_simulation(self, order_book: Dict, latency: int) -> Dict:
        """
        Simulate the effect of network latency on the order book.
        
        This creates a slightly outdated version of the order book to simulate
        execution with stale data due to network latency.
        
        Args:
            order_book: Current order book
            latency: Simulated latency in milliseconds
            
        Returns:
            Dict: Simulated order book with latency effects
        """
        # For simplicity, we'll simulate latency by slightly modifying the order book
        # In a real system, you might have historical snapshots to use
        import copy
        import random
        
        # Make a deep copy to avoid modifying the original
        stale_book = copy.deepcopy(order_book)
        
        # The higher the latency, the more we modify the book
        modification_factor = min(latency / 1000, 0.1)  # Cap at 10% modification
        
        # Modify prices slightly to simulate price movement during latency
        for side in ['bids', 'asks']:
            for i in range(len(stale_book[side])):
                price = stale_book[side][i][0]
                quantity = stale_book[side][i][1]
                
                # Modify price (bids go down, asks go up during latency)
                direction = -1 if side == 'bids' else 1
                price_change = price * modification_factor * random.uniform(0, 0.5) * direction
                new_price = price + price_change
                
                # Modify quantity (randomly increase or decrease)
                qty_change = quantity * modification_factor * random.uniform(-0.5, 0.5)
                new_quantity = max(0.0001, quantity + qty_change)  # Ensure quantity is positive
                
                stale_book[side][i][0] = new_price
                stale_book[side][i][1] = new_quantity
        
        logger.debug(f"Applied latency simulation of {latency}ms to order book")
        return stale_book
    
    def _create_error_result(self, error_message: str) -> Dict:
        """Create an error result dictionary."""
        logger.error(error_message)
        return {
            "executed_quantity_base": 0,
            "executed_quantity_quote": 0,
            "average_price": 0,
            "slippage_pct": 0,
            "market_impact_pct": 0,
            "fee_paid": 0,
            "execution_type": "fail",
            "warnings": [error_message]
        }