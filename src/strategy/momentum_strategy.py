#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Momentum Breakout Strategy
-------------------------
A strategy that trades based on momentum breakouts using volume surges and price highs.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any
from collections import deque

from src.strategy.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class MomentumStrategy(BaseStrategy):
    """
    Momentum breakout strategy that trades when price breaks through recent highs
    with increased volume.
    """
    
    def __init__(self, name: str, symbol: str, initial_capital: float = 100000.0,
                 price_window: int = 20, volume_window: int = 10,
                 breakout_threshold: float = 0.02, volume_threshold: float = 1.5,
                 position_size: float = 0.2):
        """
        Initialize the momentum breakout strategy.
        
        Args:
            name: Strategy name
            symbol: Trading symbol (e.g., 'BTC-USDT')
            initial_capital: Initial capital in quote currency
            price_window: Window for tracking price highs/lows
            volume_window: Window for tracking volume
            breakout_threshold: Threshold for price breakout (as a percentage)
            volume_threshold: Threshold for volume surge (as a multiple of average)
            position_size: Size of each position as a fraction of capital
        """
        super().__init__(name, symbol, initial_capital)
        
        self.price_window = price_window
        self.volume_window = volume_window
        self.breakout_threshold = breakout_threshold
        self.volume_threshold = volume_threshold
        self.position_size = position_size
        
        # Price and volume history
        self.price_history = deque(maxlen=price_window)
        self.volume_history = deque(maxlen=volume_window)
        
        # Strategy state
        self.highest_high = 0
        self.lowest_low = float('inf')
        self.avg_volume = 0
        self.last_signal = None
        
        logger.info(f"Initialized momentum strategy with price_window={price_window}, "
                   f"volume_window={volume_window}, breakout_threshold={breakout_threshold}")
    
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
        
        # Extract data from order book
        best_bid = order_book_snapshot['bids'][0][0] if order_book_snapshot['bids'] else 0
        best_ask = order_book_snapshot['asks'][0][0] if order_book_snapshot['asks'] else 0
        
        if best_bid <= 0 or best_ask <= 0:
            logger.warning("Invalid bid/ask prices in order book")
            return []
        
        mid_price = (best_bid + best_ask) / 2
        
        # Estimate volume from order book (sum of top N levels)
        bid_volume = sum(qty for _, qty in order_book_snapshot['bids'][:5])
        ask_volume = sum(qty for _, qty in order_book_snapshot['asks'][:5])
        total_volume = bid_volume + ask_volume
        
        # Update price and volume history
        self.price_history.append(mid_price)
        self.volume_history.append(total_volume)
        
        # Wait until we have enough data
        if len(self.price_history) < self.price_window or len(self.volume_history) < self.volume_window:
            return []
        
        # Calculate metrics
        self.highest_high = max(self.price_history)
        self.lowest_low = min(self.price_history)
        self.avg_volume = sum(self.volume_history) / len(self.volume_history)
        
        # Check for breakout conditions
        is_price_breakout_up = mid_price > self.highest_high * (1 - self.breakout_threshold)
        is_price_breakout_down = mid_price < self.lowest_low * (1 + self.breakout_threshold)
        is_volume_surge = total_volume > self.avg_volume * self.volume_threshold
        
        # Generate trading signals
        orders = []
        
        # Upward breakout with volume surge - go long
        if is_price_breakout_up and is_volume_surge and self.position <= 0:
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
            logger.info(f"Generated BUY signal: breakout={is_price_breakout_up}, "
                       f"volume_surge={is_volume_surge}, price={mid_price:.2f}")
        
        # Downward breakout with volume surge - go short
        elif is_price_breakout_down and is_volume_surge and self.position >= 0:
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
            logger.info(f"Generated SELL signal: breakout={is_price_breakout_down}, "
                       f"volume_surge={is_volume_surge}, price={mid_price:.2f}")
        
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