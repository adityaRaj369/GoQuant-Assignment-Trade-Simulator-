#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WebSocket Handler Module
------------------------
Handles the WebSocket connection to the OKX L2 order book feed.
Processes incoming data and maintains the order book state.

"""

import json
import threading
import time
import logging
import websocket as ws
from collections import deque

class WebSocketHandler:
    """Handles WebSocket connection and data processing for L2 order book."""
    
    def __init__(self, url):
        """
        Initialize the WebSocket handler.
        
        Args:
            url (str): WebSocket endpoint URL
        """
        self.url = url
        self.ws = None
        self.connected = False
        self.order_book = {"bids": {}, "asks": {}}
        self.data_buffer = deque(maxlen=1000)  # Store recent updates
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        self.latest_data = {'bids': [], 'asks': []}
        
    def connect(self):
        """Establish WebSocket connection."""
        self.logger.info(f"Connecting to WebSocket: {self.url}")
        
        # Create a WebSocket connection
        # Note: Using the correct API for websocket-client library
        self.ws = ws.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Start the WebSocket connection in a separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for connection to establish or timeout
        timeout = 10  # seconds
        start_time = time.time()
        while not self.connected and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if not self.connected:
            self.logger.warning(f"Failed to connect to WebSocket within {timeout} seconds")
            
            # For simulation purposes, let's add some mock data
            self._add_mock_data()
        
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        self.logger.info(f"Received message: {message}")
        try:
            # Parse the JSON message
            data = json.loads(message)
            # Process the order book data
            with self.lock:
                # Store the raw message in the buffer
                self.data_buffer.append(data)
                
                # Update the order book
                # Check if this is an order book update message
                if 'asks' in data and 'bids' in data:
                    # Process bids
                    self.logger.info(f"Processing {len(data['bids'])} bids")
                    for price, size in data['bids']:
                        price = float(price)
                        size = float(size)
                        
                        if size > 0:
                            self.order_book['bids'][price] = size
                        else:
                            # Remove price level if size is 0
                            if price in self.order_book['bids']:
                                del self.order_book['bids'][price]
                
                    # Process asks
                    self.logger.info(f"Processing {len(data['asks'])} asks")
                    for price, size in data['asks']:
                        price = float(price)
                        size = float(size)
                        
                        if size > 0:
                            self.order_book['asks'][price] = size
                        else:
                            # Remove price level if size is 0
                            if price in self.order_book['asks']:
                                del self.order_book['asks'][price]
            
            self.logger.debug(f"Processed order book update: {len(self.order_book['bids'])} bids, {len(self.order_book['asks'])} asks")
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
        
    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        self.logger.error(f"WebSocket error: {str(error)}")
        
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close."""
        self.logger.info("WebSocket connection closed")
        self.connected = False
        
    def on_open(self, ws):
        """Handle WebSocket connection open."""
        self.logger.info("WebSocket connection established")
        self.connected = True
        
        # Send subscription message for L2 order book
        subscription_msg = json.dumps({
            "op": "subscribe",
            "args": [{
                "channel": "books",
                "instId": "BTC-USDT-SWAP"
            }]
        })
        self.ws.send(subscription_msg)
        self.logger.info(f"Sent subscription message: {subscription_msg}")
    
    # Add this method as an alias
    def get_order_book(self):
        """Alias for get_current_order_book for compatibility with simulator app."""
        return self.get_current_order_book()
        
    def get_current_order_book(self):
        """
        Get the current state of the order book.
        
        Returns:
            dict: Current order book with bids and asks
        """
        with self.lock:
            # Convert dictionary format to list format expected by the simulator
            sorted_bids = sorted(self.order_book['bids'].items(), key=lambda x: x[0], reverse=True)
            sorted_asks = sorted(self.order_book['asks'].items(), key=lambda x: x[0])
            
            return {
                'bids': sorted_bids,
                'asks': sorted_asks
            }
        
    def close(self):
        """Close the WebSocket connection."""
        if self.ws and self.connected:
            self.ws.close()
            self.logger.info("WebSocket connection closed")
            
    def _add_mock_data(self):
        """Add mock data for simulation when WebSocket connection fails."""
        self.logger.info("Adding mock order book data for simulation")
        
        with self.lock:
            # Add some mock bid levels
            self.order_book['bids'] = {
                65000.0: 2.5,
                64900.0: 3.2,
                64800.0: 5.1,
                64700.0: 7.8,
                64600.0: 10.5,
                64500.0: 15.3,
                64400.0: 20.1,
                64300.0: 25.8,
                64200.0: 30.2,
                64100.0: 35.7
            }
            
            # Add some mock ask levels
            self.order_book['asks'] = {
                65100.0: 2.3,
                65200.0: 3.5,
                65300.0: 4.8,
                65400.0: 6.7,
                65500.0: 9.2,
                65600.0: 12.5,
                65700.0: 18.3,
                65800.0: 22.7,
                65900.0: 28.4,
                66000.0: 33.9
            }
            # Update latest_data after adding mock data
            self.latest_data = self.get_current_order_book()