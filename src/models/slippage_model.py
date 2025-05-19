#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Slippage Model
-------------
Estimates slippage for market orders based on order book depth.
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class SlippageModel:
    """
    Estimates slippage for market orders based on order book depth.
    
    Slippage is calculated as the percentage difference between the average execution
    price and the mid-price, based on the available liquidity in the order book.
    """
    
    def __init__(self):
        """Initialize the slippage model."""
        logger.info("Initializing SlippageModel")
    
    def estimate(self, order_size: float, side: str, order_book: dict) -> float:
        """
        Estimate slippage for a given market order.
        
        Args:
            order_size: Size of the order in base currency (e.g., BTC)
            side: Order side ('buy' or 'sell')
            order_book: Dictionary containing 'bids' and 'asks' as lists of (price, quantity) tuples
            
        Returns:
            float: Estimated slippage as a percentage (e.g., 0.127 for 0.127%)
        """
        if not order_book or 'bids' not in order_book or 'asks' not in order_book:
            logger.warning("Invalid order book data provided")
            return 0.0
            
        if order_size <= 0:
            logger.warning(f"Invalid order size: {order_size}")
            return 0.0
            
        # Calculate mid price
        best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
        best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
        
        if best_bid == 0 or best_ask == 0:
            logger.warning("Invalid bid/ask prices in order book")
            return 0.0
            
        mid_price = (best_bid + best_ask) / 2
        
        # Determine which side of the book to use
        book_side = order_book['asks'] if side.lower() == 'buy' else order_book['bids']
        
        # Calculate average execution price
        remaining_size = order_size
        total_cost = 0.0
        
        for price, quantity in book_side:
            if remaining_size <= 0:
                break
                
            executed_quantity = min(remaining_size, quantity)
            total_cost += executed_quantity * price
            remaining_size -= executed_quantity
            
        # If we couldn't fill the entire order with the available liquidity
        if remaining_size > 0:
            logger.warning(f"Insufficient liquidity to fill order of size {order_size}")
            # Use the last price for the remaining quantity
            if book_side:
                total_cost += remaining_size * book_side[-1][0]
            else:
                return 0.0
                
        avg_execution_price = total_cost / order_size
        
        # Calculate slippage
        if side.lower() == 'buy':
            slippage_pct = ((avg_execution_price - mid_price) / mid_price) * 100
        else:  # sell
            slippage_pct = ((mid_price - avg_execution_price) / mid_price) * 100
            
        # Round to 3 decimal places
        slippage_pct = round(slippage_pct, 3)
        
        logger.debug(f"Estimated slippage for {order_size} {side}: {slippage_pct}%")
        return slippage_pct