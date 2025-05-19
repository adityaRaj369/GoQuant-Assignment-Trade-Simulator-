#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Maker/Taker Fee Model
--------------------
Model for estimating trading fees based on execution type and user profile.

This model provides functionality to:
1. Calculate fees for executed trades
2. Estimate expected fees for potential trades
3. Predict whether an order will execute as maker or taker
4. Apply fee tiers based on user profiles and trading volume
"""

import logging
import math
from typing import Dict, List, Tuple, Optional, Union, Any

logger = logging.getLogger(__name__)

class MakerTakerFeeModel:
    """
    Model for estimating trading fees based on execution type and user profile.
    
    Uses a logistic regression model to estimate the probability of an order being
    executed as a taker order, and calculates the expected fee accordingly.
    """
    
    def __init__(self, use_ml: bool = False, w1: float = 0.3, w2: float = 8.0, bias: float = -2.5):
        """
        Initialize the maker/taker fee model.
        
        Args:
            use_ml: Whether to use ML-based model instead of rule-based
            w1: Weight for log(order_size) in logistic regression
            w2: Weight for spread in logistic regression
            bias: Bias term in logistic regression
        """
        self.use_ml = use_ml
        self.w1 = w1
        self.w2 = w2
        self.bias = bias
        
        # Default fee rates (can be overridden by user profiles)
        self.default_maker_fee = 0.06  # 0.06%
        self.default_taker_fee = 0.08  # 0.08%
        
        # Fee tiers based on 30-day trading volume
        self.fee_tiers = [
            {"volume": 0, "maker": 0.06, "taker": 0.08},         # Default tier
            {"volume": 10000, "maker": 0.05, "taker": 0.07},     # $10K+
            {"volume": 100000, "maker": 0.04, "taker": 0.06},    # $100K+
            {"volume": 1000000, "maker": 0.03, "taker": 0.05},   # $1M+
            {"volume": 10000000, "maker": 0.02, "taker": 0.04},  # $10M+
            {"volume": 100000000, "maker": 0.01, "taker": 0.03}, # $100M+
        ]
        
        # VIP profiles with custom fee rates
        self.vip_profiles = {
            "institutional": {"maker": 0.01, "taker": 0.03},
            "market_maker": {"maker": -0.01, "taker": 0.02},  # Negative maker fee = rebate
            "retail": {"maker": 0.06, "taker": 0.08},
        }
        
        logger.info(f"Fee model initialized (ML: {use_ml})")
    
    def calculate_fee(self, order_amount: float, fee_rate: float, execution_type: str) -> float:
        """
        Calculate fee for an executed order.
        
        Args:
            order_amount: Amount of the order in quote currency
            fee_rate: Fee rate as a percentage (e.g., 0.08 for 0.08%)
            execution_type: Type of execution ('maker', 'taker', or 'partial')
            
        Returns:
            float: Fee amount in quote currency
        """
        if order_amount <= 0 or fee_rate < 0:
            logger.warning(f"Invalid inputs: amount={order_amount}, fee_rate={fee_rate}")
            return 0.0
        
        # For partial fills, we need to determine which fee to apply
        # Default to taker fee for partial fills
        if execution_type.lower() == 'partial':
            logger.debug(f"Partial fill treated as taker for fee calculation")
            
        # Calculate fee amount
        fee_amount = order_amount * (fee_rate / 100)
        
        logger.debug(f"Calculated fee: {fee_amount:.4f} for {execution_type} order of {order_amount}")
        return fee_amount
    
    def estimate(self, order_size: float, side: str, order_book: Dict, 
                order_type: str = 'limit', user_profile: Optional[Dict] = None) -> float:
        """
        Estimate fee percentage for a given order.
        
        Args:
            order_size: Size of the order in quote currency
            side: Order side ('buy' or 'sell')
            order_book: Dictionary containing 'bids' and 'asks' as lists of [price, quantity] tuples
            order_type: Order type ('market' or 'limit')
            user_profile: User's fee profile with trading volume and/or VIP status
            
        Returns:
            float: Estimated fee percentage
        """
        if self.use_ml:
            return self._estimate_ml(order_size, side, order_book, order_type, user_profile)
        else:
            return self._estimate_rule_based(order_size, side, order_book, order_type, user_profile)
    
    def _estimate_rule_based(self, order_size: float, side: str, order_book: Dict,
                           order_type: str, user_profile: Optional[Dict]) -> float:
        """
        Estimate fee using rule-based approach.
        
        Args:
            order_size: Size of the order in quote currency
            side: Order side ('buy' or 'sell')
            order_book: Dictionary containing 'bids' and 'asks' as lists of [price, quantity] tuples
            order_type: Order type ('market' or 'limit')
            user_profile: User's fee profile with trading volume and/or VIP status
            
        Returns:
            float: Estimated fee percentage
        """
        # Determine if this would be a maker or taker order
        is_taker = True
        
        # Market orders are always taker
        if order_type.lower() == 'market':
            is_taker = True
        else:
            # For limit orders, it depends on whether the order crosses the spread
            # Get best bid and ask
            best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
            best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
            
            # Simplified assumption for limit orders
            if side.lower() == 'buy':
                # For buy orders, if the price is below best ask, it's a maker
                is_taker = False  # Assume limit order at best bid
            else:  # sell
                # For sell orders, if the price is above best bid, it's a maker
                is_taker = False  # Assume limit order at best ask
        
        # Get fee rates based on user profile
        maker_fee, taker_fee = self._get_fee_rates(user_profile)
        
        # Apply size-based fee tier if no specific user profile
        if not user_profile:
            tier_multiplier = self._get_tier_multiplier(order_size)
            maker_fee *= tier_multiplier
            taker_fee *= tier_multiplier
        
        # Calculate fee
        fee_pct = taker_fee if is_taker else maker_fee
        
        logger.debug(f"Estimated fee for {order_size} {side} {order_type}: {fee_pct:.4f}%")
        return fee_pct
    
    def _estimate_ml(self, order_size: float, side: str, order_book: Dict,
                   order_type: str, user_profile: Optional[Dict]) -> float:
        """
        Estimate fee using ML-based approach.
        
        Args:
            order_size: Size of the order in quote currency
            side: Order side ('buy' or 'sell')
            order_book: Dictionary containing 'bids' and 'asks' as lists of [price, quantity] tuples
            order_type: Order type ('market' or 'limit')
            user_profile: User's fee profile with trading volume and/or VIP status
            
        Returns:
            float: Estimated fee percentage
        """
        # Market orders are always taker
        if order_type.lower() == 'market':
            prob_taker = 1.0
        else:
            # Calculate spread from order book
            if not order_book or 'bids' not in order_book or 'asks' not in order_book:
                logger.warning("Invalid order book data provided")
                prob_taker = 0.5  # Default to 50% probability
            else:
                best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
                best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
                
                if best_bid <= 0 or best_ask <= 0:
                    logger.warning("Invalid bid/ask prices in order book")
                    prob_taker = 0.5  # Default to 50% probability
                else:
                    spread = best_ask - best_bid
                    
                    # Calculate probability of being a taker order using logistic regression
                    try:
                        log_order_size = math.log(max(1.0, order_size))
                    except ValueError:
                        log_order_size = 0
                        logger.warning(f"Could not calculate log of order size: {order_size}")
                        
                    logit = self.w1 * log_order_size + self.w2 * spread + self.bias
                    prob_taker = self._sigmoid(logit)
        
        # Get fee rates based on user profile
        maker_fee, taker_fee = self._get_fee_rates(user_profile)
        
        # Calculate expected fee
        expected_fee = prob_taker * taker_fee + (1 - prob_taker) * maker_fee
        
        logger.debug(f"ML-estimated fee for {order_size} {side}: {expected_fee:.4f}% (prob_taker={prob_taker:.2f})")
        return round(expected_fee, 4)
    
    def _sigmoid(self, x: float) -> float:
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
    
    def _get_tier_multiplier(self, order_size: float) -> float:
        """
        Get fee tier multiplier based on order size.
        
        Args:
            order_size: Size of the order in quote currency
            
        Returns:
            float: Fee tier multiplier
        """
        # Simplified tier structure - larger orders get discounts
        if order_size > 1000000:  # $1M+
            return 0.7  # 30% discount
        elif order_size > 100000:  # $100K+
            return 0.8  # 20% discount
        elif order_size > 10000:   # $10K+
            return 0.9  # 10% discount
        else:
            return 1.0  # No discount
    
    def _get_fee_rates(self, user_profile: Optional[Dict]) -> Tuple[float, float]:
        """
        Get maker and taker fee rates based on user profile.
        
        Args:
            user_profile: User's fee profile with trading volume and/or VIP status
            
        Returns:
            Tuple[float, float]: Maker and taker fee rates
        """
        if not user_profile:
            return self.default_maker_fee, self.default_taker_fee
        
        # Check if user has a VIP profile
        if 'vip_tier' in user_profile and user_profile['vip_tier'] in self.vip_profiles:
            vip_profile = self.vip_profiles[user_profile['vip_tier']]
            return vip_profile['maker'], vip_profile['taker']
        
        # Check if user has a 30-day trading volume
        if 'trading_volume' in user_profile:
            volume = user_profile['trading_volume']
            
            # Find the appropriate fee tier
            applicable_tier = self.fee_tiers[0]  # Default tier
            for tier in self.fee_tiers:
                if volume >= tier['volume']:
                    applicable_tier = tier
                else:
                    break
            
            return applicable_tier['maker'], applicable_tier['taker']
        
        # Default rates if no specific profile information
        return self.default_maker_fee, self.default_taker_fee
    
    def predict_execution_type(self, side: str, order_type: str, order_price: Optional[float], 
                             order_book: Dict) -> str:
        """
        Predict whether an order will execute as maker or taker.
        
        Args:
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market' or 'limit')
            order_price: Price for limit orders (None for market orders)
            order_book: Dictionary containing 'bids' and 'asks' as lists of [price, quantity] tuples
            
        Returns:
            str: Predicted execution type ('maker' or 'taker')
        """
        # Market orders are always taker
        if order_type.lower() == 'market':
            return 'taker'
        
        # For limit orders, check if they cross the spread
        if not order_book['bids'] or not order_book['asks']:
            return 'maker'  # Default to maker if book is empty
            
        best_bid = order_book['bids'][0][0]
        best_ask = order_book['asks'][0][0]
        
        if side.lower() == 'buy':
            # Buy limit orders are taker if price >= best ask
            if order_price >= best_ask:
                return 'taker'
            else:
                return 'maker'
        else:  # sell
            # Sell limit orders are taker if price <= best bid
            if order_price <= best_bid:
                return 'taker'
            else:
                return 'maker'