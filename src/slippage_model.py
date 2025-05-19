#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Slippage Model
-------------
Model for estimating slippage in cryptocurrency trades based on
order book depth and order size.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class SlippageModel:
    """
    Model for estimating slippage in cryptocurrency trades.
    
    Slippage is calculated as the percentage difference between the average
    execution price and the mid-price, based on the available liquidity in
    the order book.
    """
    
    def __init__(self, use_ml_model: bool = False):
        """
        Initialize the slippage model.
        
        Args:
            use_ml_model: Whether to use ML-based model instead of rule-based
        """
        self.use_ml_model = use_ml_model
        if use_ml_model:
            # Initialize ML model (placeholder for now)
            self.ml_model = self._initialize_ml_model()
        
        logger.info(f"Slippage model initialized (ML model: {use_ml_model})")
    
    def calculate_slippage(self, side: str, mid_price: float, 
                          executed_price: float, order_size: float) -> float:
        """
        Calculate slippage for an executed order.
        
        Args:
            side: Order side ('buy' or 'sell')
            mid_price: Mid-price before execution
            executed_price: Average execution price
            order_size: Size of the order in quote currency
            
        Returns:
            float: Slippage as a percentage
        """
        if mid_price <= 0 or executed_price <= 0:
            logger.warning("Invalid prices for slippage calculation")
            return 0.0
        
        # Calculate slippage
        if side.lower() == 'buy':
            # For buys, slippage is positive when execution price > mid price
            slippage_pct = ((executed_price - mid_price) / mid_price) * 100
        else:  # sell
            # For sells, slippage is positive when execution price < mid price
            slippage_pct = ((mid_price - executed_price) / mid_price) * 100
        
        logger.debug(f"Calculated slippage for {side} order: {slippage_pct:.4f}%")
        return max(0, slippage_pct)  # Ensure non-negative slippage
    
    def estimate_slippage(self, side: str, order_size: float, 
                         order_book: Dict[str, List[List[float]]]) -> float:
        """
        Estimate expected slippage for a potential order.
        
        Args:
            side: Order side ('buy' or 'sell')
            order_size: Size of the order in quote currency
            order_book: Order book with bids and asks
            
        Returns:
            float: Estimated slippage as a percentage
        """
        if self.use_ml_model:
            return self._estimate_slippage_ml(side, order_size, order_book)
        else:
            return self._estimate_slippage_rule_based(side, order_size, order_book)
    
    def _estimate_slippage_rule_based(self, side: str, order_size: float, 
                                     order_book: Dict[str, List[List[float]]]) -> float:
        """
        Estimate slippage using a rule-based approach by walking the order book.
        
        Args:
            side: Order side ('buy' or 'sell')
            order_size: Size of the order in quote currency
            order_book: Order book with bids and asks
            
        Returns:
            float: Estimated slippage as a percentage
        """
        # Get reference prices
        best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
        best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
        
        if best_bid <= 0 or best_ask <= 0:
            logger.warning("Invalid bid/ask prices in order book")
            return 0.0
        
        mid_price = (best_bid + best_ask) / 2
        
        # Determine which side of the book to use
        book_side = 'asks' if side.lower() == 'buy' else 'bids'
        
        # Walk the book to simulate execution
        remaining_size = order_size
        total_cost = 0.0
        total_quantity_base = 0.0
        
        for price, quantity in order_book[book_side]:
            if remaining_size <= 0:
                break
            
            # Calculate how much we can execute at this level
            if side.lower() == 'buy':
                max_executable_quote = price * quantity
                executable_quote = min(remaining_size, max_executable_quote)
                executable_base = executable_quote / price
            else:  # sell
                executable_base = min(remaining_size / price, quantity)
                executable_quote = executable_base * price
            
            # Update totals
            total_cost += executable_quote
            total_quantity_base += executable_base
            remaining_size -= executable_quote
        
        # If we couldn't fill the entire order with the available liquidity
        if remaining_size > 0:
            logger.warning(f"Insufficient liquidity to fill order of size {order_size}")
            # Use the last price for the remaining quantity
            if order_book[book_side]:
                last_price = order_book[book_side][-1][0]
                remaining_base = remaining_size / last_price
                total_cost += remaining_size
                total_quantity_base += remaining_base
        
        # Calculate average execution price
        avg_execution_price = total_cost / total_quantity_base if total_quantity_base > 0 else 0
        
        # Calculate slippage
        return self.calculate_slippage(side, mid_price, avg_execution_price, order_size)
    
    def _estimate_slippage_ml(self, side: str, order_size: float, 
                             order_book: Dict[str, List[List[float]]]) -> float:
        """
        Estimate slippage using an ML-based approach.
        
        Args:
            side: Order side ('buy' or 'sell')
            order_size: Size of the order in quote currency
            order_book: Order book with bids and asks
            
        Returns:
            float: Estimated slippage as a percentage
        """
        # Extract features from the order book
        features = self._extract_features(side, order_size, order_book)
        
        # In a real implementation, you would use your trained model here
        # For now, we'll use a simple polynomial function as a placeholder
        
        # Calculate order size relative to available liquidity
        book_side = 'asks' if side.lower() == 'buy' else 'bids'
        available_liquidity = sum(qty for _, qty in order_book[book_side])
        relative_size = order_size / available_liquidity if available_liquidity > 0 else 1
        
        # Simple polynomial model: slippage = a * (relative_size)^b
        a, b = 0.5, 1.5  # Coefficients (would be learned in a real ML model)
        estimated_slippage = a * (relative_size ** b)
        
        # Cap at reasonable values
        estimated_slippage = min(estimated_slippage, 5.0)  # Cap at 5%
        
        logger.debug(f"ML-estimated slippage for {side} order: {estimated_slippage:.4f}%")
        return estimated_slippage
    
    def _extract_features(self, side: str, order_size: float, 
                         order_book: Dict[str, List[List[float]]]) -> np.ndarray:
        """
        Extract features from the order book for ML-based slippage estimation.
        
        Args:
            side: Order side ('buy' or 'sell')
            order_size: Size of the order in quote currency
            order_book: Order book with bids and asks
            
        Returns:
            np.ndarray: Feature vector
        """
        # Get reference prices
        best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
        best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
        mid_price = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        spread_bps = (spread / mid_price) * 10000 if mid_price > 0 else 0
        
        # Calculate order book imbalance
        bid_liquidity = sum(qty for _, qty in order_book['bids'])
        ask_liquidity = sum(qty for _, qty in order_book['asks'])
        total_liquidity = bid_liquidity + ask_liquidity
        imbalance = (bid_liquidity - ask_liquidity) / total_liquidity if total_liquidity > 0 else 0
        
        # Calculate depth at different levels
        book_side = 'asks' if side.lower() == 'buy' else 'bids'
        depth_1 = order_book[book_side][0][1] if len(order_book[book_side]) > 0 else 0
        depth_3 = sum(qty for _, qty in order_book[book_side][:3]) if len(order_book[book_side]) >= 3 else depth_1
        depth_5 = sum(qty for _, qty in order_book[book_side][:5]) if len(order_book[book_side]) >= 5 else depth_3
        
        # Relative order size
        relative_size_1 = order_size / depth_1 if depth_1 > 0 else 10
        relative_size_3 = order_size / depth_3 if depth_3 > 0 else relative_size_1
        relative_size_5 = order_size / depth_5 if depth_5 > 0 else relative_size_3
        
        # Create feature vector
        features = np.array([
            spread_bps,
            imbalance,
            relative_size_1,
            relative_size_3,
            relative_size_5,
            1 if side.lower() == 'buy' else 0  # Side indicator
        ])
        
        return features
    
    def _initialize_ml_model(self):
        """
        Initialize the ML model for slippage prediction.
        
        In a real implementation, you would load a pre-trained model here.
        For now, this is just a placeholder.
        
        Returns:
            object: ML model instance
        """
        # Placeholder for a real ML model
        class DummyModel:
            def predict(self, features):
                # Simple polynomial function as a placeholder
                relative_size = features[2]  # Use relative_size_1 feature
                return 0.5 * (relative_size ** 1.5)
        
        return DummyModel()