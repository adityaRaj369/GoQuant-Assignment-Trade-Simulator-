#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cryptocurrency Trade Simulator
------------------------------
A high-performance trade simulator that connects to OKX's L2 order book
WebSocket feed to estimate transaction costs, market impact, and latency
when placing market orders.
"""

import logging
import sys
import os
from src.utils.logger import setup_logger
from src.websocket_handler import WebSocketHandler
from src.simulator.app import SimulatorApp

# Setup logging
logger = setup_logger()

def main():
    """Main entry point for the application."""
    logger.info("Starting Cryptocurrency Trade Simulator")
    
    try:
        # Initialize WebSocket handler
        ws_handler = WebSocketHandler(
            url="wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"
        )
        
        # Initialize and start the simulator app
        app = SimulatorApp(ws_handler)
        app.start()
        
    except Exception as e:
        logger.error(f"Error in main application: {str(e)}")
        sys.exit(1)
    
    logger.info("Application terminated successfully")

if __name__ == "__main__":
    main()