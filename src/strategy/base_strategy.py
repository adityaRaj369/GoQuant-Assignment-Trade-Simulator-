#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Base Strategy Interface
----------------------
Defines the interface for all trading strategies to implement.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import time
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    All strategies must implement:
    - on_tick: Called on each new order book update
    - on_fill: Called when an order is filled
    """
    
    def __init__(self, name: str, symbol: str, initial_capital: float = 100000.0):
        """
        Initialize the strategy.
        
        Args:
            name: Strategy name
            symbol: Trading symbol (e.g., 'BTC-USDT')
            initial_capital: Initial capital in quote currency
        """
        self.name = name
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Position tracking
        self.position = 0.0  # Current position in base currency
        self.avg_entry_price = 0.0  # Average entry price
        
        # Order tracking
        self.active_orders = []  # List of active orders
        self.filled_orders = []  # List of filled orders
        
        # Performance metrics
        self.trades = []  # List of completed trades
        self.pnl_history = []  # History of PnL
        self.equity_curve = [(0, initial_capital)]  # (timestamp, equity)
        
        # Strategy state
        self.is_active = False
        self.last_tick_time = 0
        
        # Risk management
        self.max_position_size = float('inf')  # Maximum allowed position size
        self.max_drawdown_pct = 0.25  # Maximum allowed drawdown (25%)
        self.stop_loss_pct = 0.05  # Default stop loss percentage (5%)
        self.take_profit_pct = 0.10  # Default take profit percentage (10%)
        
        # Performance tracking
        self.start_time = None
        self.end_time = None
        self.max_equity = initial_capital
        self.min_equity = initial_capital
        self.max_drawdown = 0.0
        
        logger.info(f"Initialized strategy: {name} for {symbol} with {initial_capital} capital")
    
    @abstractmethod
    def on_tick(self, order_book_snapshot: Dict, timestamp: int) -> List[Dict]:
        """
        Process a new order book snapshot and generate trading signals.
        
        Args:
            order_book_snapshot: Current state of the order book
            timestamp: Current timestamp
            
        Returns:
            List[Dict]: List of order instructions to be executed
        """
        pass
    
    @abstractmethod
    def on_fill(self, order_execution_report: Dict) -> None:
        """
        Process an order execution report.
        
        Args:
            order_execution_report: Details of the executed order
        """
        pass
    
    def start(self) -> None:
        """Activate the strategy."""
        self.is_active = True
        self.start_time = time.time()
        logger.info(f"Strategy {self.name} started")
    
    def stop(self) -> None:
        """Deactivate the strategy."""
        self.is_active = False
        self.end_time = time.time()
        logger.info(f"Strategy {self.name} stopped")
    
    def reset(self) -> None:
        """Reset the strategy to its initial state."""
        self.current_capital = self.initial_capital
        self.position = 0.0
        self.avg_entry_price = 0.0
        self.active_orders = []
        self.filled_orders = []
        self.trades = []
        self.pnl_history = []
        self.equity_curve = [(0, self.initial_capital)]
        self.max_equity = self.initial_capital
        self.min_equity = self.initial_capital
        self.max_drawdown = 0.0
        self.start_time = None
        self.end_time = None
        logger.info(f"Strategy {self.name} reset to initial state")
    
    def update_position(self, quantity: float, price: float, side: str) -> None:
        """
        Update the current position after a fill.
        
        Args:
            quantity: Quantity in base currency
            price: Execution price
            side: 'buy' or 'sell'
        """
        if side.lower() == 'buy':
            # Calculate new average entry price if adding to position
            if self.position >= 0:
                # Adding to long position
                total_cost = (self.position * self.avg_entry_price) + (quantity * price)
                self.position += quantity
                self.avg_entry_price = total_cost / self.position if self.position > 0 else 0
            else:
                # Reducing short position
                self.position += quantity
                # If position flips to long, reset average price
                if self.position > 0:
                    self.avg_entry_price = price
        else:  # sell
            if self.position <= 0:
                # Adding to short position
                total_cost = (abs(self.position) * self.avg_entry_price) + (quantity * price)
                self.position -= quantity
                self.avg_entry_price = total_cost / abs(self.position) if self.position < 0 else 0
            else:
                # Reducing long position
                self.position -= quantity
                # If position flips to short, reset average price
                if self.position < 0:
                    self.avg_entry_price = price
        
        logger.debug(f"Updated position: {self.position} @ {self.avg_entry_price}")
    
    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """
        Calculate unrealized PnL based on current market price.
        
        Args:
            current_price: Current market price
            
        Returns:
            float: Unrealized PnL
        """
        if self.position == 0:
            return 0.0
            
        if self.position > 0:
            # Long position
            return self.position * (current_price - self.avg_entry_price)
        else:
            # Short position
            return abs(self.position) * (self.avg_entry_price - current_price)
    
    def calculate_realized_pnl(self) -> float:
        """
        Calculate total realized PnL from completed trades.
        
        Returns:
            float: Total realized PnL
        """
        return sum(trade['realized_pnl'] for trade in self.trades)
    
    def update_equity(self, timestamp: int, current_price: float) -> None:
        """
        Update the equity curve with current value.
        
        Args:
            timestamp: Current timestamp
            current_price: Current market price
        """
        unrealized_pnl = self.calculate_unrealized_pnl(current_price)
        current_equity = self.current_capital + unrealized_pnl
        self.equity_curve.append((timestamp, current_equity))
        
        # Update max and min equity for drawdown calculation
        self.max_equity = max(self.max_equity, current_equity)
        self.min_equity = min(self.min_equity, current_equity)
        
        # Calculate current drawdown
        if self.max_equity > 0:
            current_drawdown = (self.max_equity - current_equity) / self.max_equity
            self.max_drawdown = max(self.max_drawdown, current_drawdown)
            
            # Check if max drawdown exceeded
            if current_drawdown >= self.max_drawdown_pct and self.is_active:
                logger.warning(f"Max drawdown exceeded: {current_drawdown:.2%}. Stopping strategy.")
                self.stop()
    
    def check_risk_limits(self, order_size: float, side: str, current_price: float) -> bool:
        """
        Check if an order would violate risk management limits.
        
        Args:
            order_size: Size of the order in base currency
            side: Order side ('buy' or 'sell')
            current_price: Current market price
            
        Returns:
            bool: True if order is within risk limits, False otherwise
        """
        # Check position size limit
        new_position = self.position
        if side.lower() == 'buy':
            new_position += order_size
        else:  # sell
            new_position -= order_size
            
        if abs(new_position) > self.max_position_size:
            logger.warning(f"Order would exceed max position size: {abs(new_position)} > {self.max_position_size}")
            return False
            
        # Check if we have enough capital
        order_value = order_size * current_price
        if side.lower() == 'buy' and order_value > self.current_capital:
            logger.warning(f"Insufficient capital for order: {order_value} > {self.current_capital}")
            return False
            
        return True
    
    def set_stop_loss(self, stop_loss_pct: float) -> None:
        """
        Set the stop loss percentage for the strategy.
        
        Args:
            stop_loss_pct: Stop loss percentage (e.g., 0.05 for 5%)
        """
        if stop_loss_pct <= 0 or stop_loss_pct >= 1:
            logger.warning(f"Invalid stop loss percentage: {stop_loss_pct}")
            return
            
        self.stop_loss_pct = stop_loss_pct
        logger.info(f"Set stop loss to {stop_loss_pct:.2%}")
    
    def set_take_profit(self, take_profit_pct: float) -> None:
        """
        Set the take profit percentage for the strategy.
        
        Args:
            take_profit_pct: Take profit percentage (e.g., 0.10 for 10%)
        """
        if take_profit_pct <= 0 or take_profit_pct >= 1:
            logger.warning(f"Invalid take profit percentage: {take_profit_pct}")
            return
            
        self.take_profit_pct = take_profit_pct
        logger.info(f"Set take profit to {take_profit_pct:.2%}")
    
    def check_stop_loss_take_profit(self, current_price: float) -> List[Dict]:
        """
        Check if stop loss or take profit levels have been reached.
        
        Args:
            current_price: Current market price
            
        Returns:
            List[Dict]: List of order instructions if SL/TP triggered
        """
        if self.position == 0:
            return []
            
        orders = []
        
        # For long positions
        if self.position > 0:
            # Check stop loss
            stop_price = self.avg_entry_price * (1 - self.stop_loss_pct)
            if current_price <= stop_price:
                # Create sell order to close position
                order = {
                    'side': 'sell',
                    'order_type': 'market',
                    'quantity': self.position,
                    'price': None,  # Market order
                    'symbol': self.symbol,
                    'timestamp': int(time.time() * 1000),
                    'strategy_id': self.name,
                    'reason': 'stop_loss'
                }
                orders.append(order)
                logger.info(f"Stop loss triggered: {current_price:.2f} <= {stop_price:.2f}")
                
            # Check take profit
            take_profit_price = self.avg_entry_price * (1 + self.take_profit_pct)
            if current_price >= take_profit_price:
                # Create sell order to close position
                order = {
                    'side': 'sell',
                    'order_type': 'market',
                    'quantity': self.position,
                    'price': None,  # Market order
                    'symbol': self.symbol,
                    'timestamp': int(time.time() * 1000),
                    'strategy_id': self.name,
                    'reason': 'take_profit'
                }
                orders.append(order)
                logger.info(f"Take profit triggered: {current_price:.2f} >= {take_profit_price:.2f}")
                
        # For short positions
        elif self.position < 0:
            # Check stop loss
            stop_price = self.avg_entry_price * (1 + self.stop_loss_pct)
            if current_price >= stop_price:
                # Create buy order to close position
                order = {
                    'side': 'buy',
                    'order_type': 'market',
                    'quantity': abs(self.position),
                    'price': None,  # Market order
                    'symbol': self.symbol,
                    'timestamp': int(time.time() * 1000),
                    'strategy_id': self.name,
                    'reason': 'stop_loss'
                }
                orders.append(order)
                logger.info(f"Stop loss triggered: {current_price:.2f} >= {stop_price:.2f}")
                
            # Check take profit
            take_profit_price = self.avg_entry_price * (1 - self.take_profit_pct)
            if current_price <= take_profit_price:
                # Create buy order to close position
                order = {
                    'side': 'buy',
                    'order_type': 'market',
                    'quantity': abs(self.position),
                    'price': None,  # Market order
                    'symbol': self.symbol,
                    'timestamp': int(time.time() * 1000),
                    'strategy_id': self.name,
                    'reason': 'take_profit'
                }
                orders.append(order)
                logger.info(f"Take profit triggered: {current_price:.2f} <= {take_profit_price:.2f}")
                
        return orders
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics for the strategy.
        
        Returns:
            Dict: Dictionary of performance metrics
        """
        total_trades = len(self.trades)
        if total_trades == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'total_pnl': 0.0,
                'return_pct': 0.0
            }
            
        # Calculate win rate
        winning_trades = sum(1 for trade in self.trades if trade['realized_pnl'] > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate profit factor
        gross_profit = sum(trade['realized_pnl'] for trade in self.trades if trade['realized_pnl'] > 0)
        gross_loss = abs(sum(trade['realized_pnl'] for trade in self.trades if trade['realized_pnl'] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate total PnL
        total_pnl = sum(trade['realized_pnl'] for trade in self.trades)
        
        # Calculate return percentage
        return_pct = (self.current_capital - self.initial_capital) / self.initial_capital
        
        # Calculate Sharpe ratio (simplified)
        if len(self.pnl_history) > 1:
            returns = self.pnl_history
            avg_return = sum(returns) / len(returns)
            std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0
        else:
            sharpe_ratio = 0
            
        # Calculate duration
        duration = 0
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
        elif self.start_time:
            duration = time.time() - self.start_time
            
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'duration': duration
        }
    
    def save_results(self, filepath: str = None) -> None:
        """
        Save strategy results to a JSON file.
        
        Args:
            filepath: Path to save the results (default: results_{strategy_name}_{timestamp}.json)
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"results_{self.name}_{timestamp}.json"
            
        # Prepare results
        results = {
            'strategy_name': self.name,
            'symbol': self.symbol,
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'position': self.position,
            'avg_entry_price': self.avg_entry_price,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'performance': self.calculate_performance_metrics()
        }
        
        # Save to file
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=4)
            logger.info(f"Strategy results saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")