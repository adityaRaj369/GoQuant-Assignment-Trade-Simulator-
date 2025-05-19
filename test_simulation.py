#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Simulation
-------------
Unit tests for the trade execution engine and associated models.
"""

import unittest
import logging
from typing import Dict, List, Tuple

from src.execution_engine import ExecutionEngine
from src.slippage_model import SlippageModel
from src.impact_model import MarketImpactModel
from src.fee_model import MakerTakerFeeModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestTradeExecution(unittest.TestCase):
    """Test cases for trade execution engine and models."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.execution_engine = ExecutionEngine()
        self.slippage_model = SlippageModel()
        self.impact_model = MarketImpactModel()
        self.fee_model = MakerTakerFeeModel()
        
        # Create a mock order book
        self.mock_order_book = {
            'bids': [
                [27350.5, 1.5],  # price, quantity
                [27345.0, 2.0],
                [27340.0, 3.0],
                [27335.0, 4.0],
                [27330.0, 5.0],
            ],
            'asks': [
                [27355.0, 1.0],
                [27360.0, 2.0],
                [27365.0, 3.0],
                [27370.0, 4.0],
                [27375.0, 5.0],
            ]
        }
        
    def test_market_buy_order(self):
        """Test a market buy order."""
        result = self.execution_engine.simulate_order_execution(
            side="buy",
            order_type="market",
            order_price=None,
            order_quantity=300,