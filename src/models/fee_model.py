#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Maker/Taker Fee Model
--------------------
Estimates trading fees based on order characteristics and market conditions.
"""

import logging
import math
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class MakerTakerModel:
    """
    Estimates trading fees based on order characteristics and market conditions.
    
    Uses a logistic regression model to estimate the probability of an order being
    executed as a taker order, and calculates the expected fee accordingly.
    """
    
    def __init__(self, w1: float = 0.3, w2: float = 8.0, bias: float = -2.5,
                 taker_fee: float = 0.05, maker_fee: float = -0.01):
        """
        Initialize the maker/taker fee model.
        
        Args:
            w1: Weight for log(order_size) in logistic regression
            w2: Weight for spread in logistic regression
            bias: Bias term in logistic regression
            taker_fee: Taker fee percentage (e.g., 0.05 for 0.05%)
            maker_fee: Maker fee percentage (e.g., -0.01 for -0.01% rebate)
        """
        self.w1 = w1
        self.w2 = w2
        self.bias = bias
        self.taker_fee = taker_fee
        self.maker_fee = maker_fee
        logger.info(f"Initializing MakerTakerModel with w1={w1}, w2={w2}, bias={bias}")
    
    def sigmoid(self, x: float) -> float:
        """
        Sigmoid activation function.
        
        Args:
            x: Input value
            
        Returns:
            float: Sigmoid output (between 0 and 1)
        """
        try:
            return 1 / (1 + math.exp(-x))
        except OverflowError:
            return 0 if x < 0 else 1
    
    def estimate(self, order_size: float, side: str, order_book: dict) -> float:
        """
        Estimate trading fee for a given order.
        
        Args:
            order_size: Size of the order in base currency (e.g., BTC)
            side: Order side ('buy' or 'sell')
            order_book: Dictionary containing 'bids' and 'asks' as lists of (price, quantity) tuples
            
        Returns:
            float: Estimated fee as a percentage (e.g., 0.04 for 0.04%)
        """
        if order_size <= 0:
            logger.warning(f"Invalid order size: {order_size}")
            return self.taker_fee  # Default to taker fee for invalid inputs
            
        # Calculate spread from order book
        if not order_book or 'bids' not in order_book or 'asks' not in order_book:
            logger.warning("Invalid order book data provided")
            return self.taker_fee
            
        best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
        best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
        
        if best_bid == 0 or best_ask == 0:
            logger.warning("Invalid bid/ask prices in order book")
            return self.taker_fee
            
        spread = best_ask - best_bid
        
        # Calculate probability of being a taker order using logistic regression
        try:
            log_order_size = math.log(order_size)
        except ValueError:
            log_order_size = 0
            logger.warning(f"Could not calculate log of order size: {order_size}")
            
        logit = self.w1 * log_order_size + self.w2 * spread + self.bias
        prob_taker = self.sigmoid(logit)
        
        # Calculate expected fee
        expected_fee = prob_taker * self.taker_fee + (1 - prob_taker) * self.maker_fee
        
        logger.debug(f"Estimated fee for {order_size} {side}: {expected_fee}% (prob_taker={prob_taker:.2f})")
        return round(expected_fee, 4)