#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mean Reversion Strategy
----------------------
A strategy that trades based on short-term price deviations from a moving average.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any
from collections import deque

from src.strategy.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy that trades when price deviates significantly
    from its short-term moving average.
    """
    
    def __init__(self, name: str, symbol: str, initial_capital: float = 100000.0,
                 window_size: int = 20, deviation_threshold: float = 0.01,
                 position_size: float = 0.1):
        """
        Initialize the mean reversion strategy.
        
        Args:
            name: Strategy name
            symbol: Trading symbol (e.g., 'BTC-USDT')
            initial_capital: Initial capital in quote currency
            window_size: Size of the moving average window
            deviation_threshold: Threshold for trading (as a percentage)
            position_size: Size of each position as a fraction of capital
        """
        super().__init__(name, symbol, initial_capital)
        
        self.window_size = window_size
        self.deviation_threshold = deviation_threshold
        self.position_size = position_size
        
        # Price history
        self.price_history = deque(maxlen=window_size)
        
        # Strategy state
        self.moving_average = None
        self.last_signal = None
        
        logger.info(f"Initialized mean reversion strategy with window={window_size}, "
                   f"threshold={deviation_threshold}, position_size={position_size}")
    
    def on_tick(self, order_book_snapshot: Dict, timestamp: int) -> List[Dict]:
        """
        Process a new order book snapshot and generate trading signals.
        
        Args:
            order_book_snapshot: Current state of the order book
            timestamp: Current timestamp
            
        Returns:
            List[Dict]: List of order instructions to be executed
        """
        if not self.is_active:
            return []
        
        self.last_tick_time = timestamp
        
        # Extract mid price from order book
        best_bid = order_book_snapshot['bids'][0][0] if order_book_snapshot['bids'] else 0
        best_ask = order_book_snapshot['asks'][0][0] if order_book_snapshot['asks'] else 0
        
        if best_bid <= 0 or best_ask <= 0:
            logger.warning("Invalid bid/ask prices in order book")
            return []
        
        mid_price = (best_bid + best_ask) / 2
        
        # Update price history
        self.price_history.append(mid_price)
        
        # Wait until we have enough data
        if len(self.price_history) < self.window_size:
            return []
        
        # Calculate moving average
        self.moving_average = sum(self.price_history) / len(self.price_history)
        
        # Calculate deviation from moving average
        deviation = (mid_price - self.moving_average) / self.moving_average
        
        # Generate trading signals
        orders = []
        
        # If price is significantly above MA, sell (mean reversion expects price to fall)
        if deviation > self.deviation_threshold and self.position >= 0:
            # Calculate position size based on capital
            order_size_quote = self.current_capital * self.position_size
            order_size_base = order_size_quote / mid_price
            
            # Create sell order
            order = {
                'side': 'sell',
                'order_type': 'limit',
                'quantity': order_size_base,
                'price': best_bid,  # Sell at bid for immediate execution
                'symbol': self.symbol,
                'timestamp': timestamp,
                'strategy_id': self.name
            }
            
            orders.append(order)
            self.last_signal = 'sell'
            logger.info(f"Generated SELL signal: deviation={deviation:.4f}, MA={self.moving_average:.2f}, price={mid_price:.2f}")
        
        # If price is significantly below MA, buy (mean reversion expects price to rise)
        elif deviation < -self.deviation_threshold and self.position <= 0:
            # Calculate position size based on capital
            order_size_quote = self.current_capital * self.position_size
            order_size_base = order_size_quote / mid_price
            
            # Create buy order
            order = {
                'side': 'buy',
                'order_type': 'limit',
                'quantity': order_size_base,
                'price': best_ask,  # Buy at ask for immediate execution
                'symbol': self.symbol,
                'timestamp': timestamp,
                'strategy_id': self.name
            }
            
            orders.append(order)
            self.last_signal = 'buy'
            logger.info(f"Generated BUY signal: deviation={deviation:.4f}, MA={self.moving_average:.2f}, price={mid_price:.2f}")
        
        # Update equity curve
        self.update_equity(timestamp, mid_price)
        
        return orders
    
    def on_fill(self, order_execution_report: Dict) -> None:
        """
        Process an order execution report.
        
        Args:
            order_execution_report: Details of the executed order
        """
        if order_execution_report['strategy_id'] != self.name:
            return
        
        side = order_execution_report['side']
        executed_quantity = order_execution_report['executed_quantity_base']
        executed_price = order_execution_report['average_price']
        executed_value = executed_quantity * executed_price
        
        # Update capital
        if side.lower() == 'buy':
            self.current_capital -= executed_value
        else:  # sell
            self.current_capital += executed_value
        
        # Update position
        old_position = self.position
        self.update_position(executed_quantity, executed_price, side)
        
        # Record trade
        realized_pnl = 0
        if (old_position > 0 and side.lower() == 'sell') or (old_position < 0 and side.lower() == 'buy'):
            # Closing or reducing position, calculate realized PnL
            realized_pnl = executed_quantity * (executed_price - self.avg_entry_price) if side.lower() == 'sell' else \
                           executed_quantity * (self.avg_entry_price - executed_price)
        
        trade = {
            'timestamp': order_execution_report.get('timestamp', self.last_tick_time),
            'side': side,
            'quantity': executed_quantity,
            'price': executed_price,
            'value': executed_value,
            'realized_pnl': realized_pnl,
            'execution_type': order_execution_report.get('execution_type', 'unknown')
        }
        
        self.trades.append(trade)
        self.pnl_history.append(realized_pnl)
        
        logger.info(f"Processed fill: {side} {executed_quantity} @ {executed_price}, PnL: {realized_pnl:.2f}")