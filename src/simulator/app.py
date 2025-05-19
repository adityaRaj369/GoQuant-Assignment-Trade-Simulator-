#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trade Simulator GUI
-----------------
Tkinter-based GUI for the cryptocurrency trade simulator.
Provides real-time order book data visualization and trade simulation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import time
from typing import Dict, List, Tuple, Optional

from src.simulator.trade_simulator import TradeSimulator
from src.utils.logger import setup_logger

logger = logging.getLogger(__name__)

class SimulatorApp:
    """
    GUI application for the cryptocurrency trade simulator.
    Provides a user interface for simulating trades with real-time
    order book data from OKX.
    """
    
    def __init__(self, websocket_client):
        """
        Initialize the simulator application.
        
        Args:
            websocket_client: WebSocket client for OKX order book data
        """
        self.websocket_client = websocket_client
        self.trade_simulator = TradeSimulator()
        self.root = None
        self.order_book = {'bids': [], 'asks': []}
        self.last_update_time = 0
        
        # UI elements
        self.side_var = None
        self.quantity_var = None
        self.result_labels = {}
        self.bid_ask_labels = {}
        self.depth_canvas = None
        
        # Theme settings
        self.theme = "light"
        self.colors = {
            "light": {
                "bg": "#f0f0f0",
                "fg": "#333333",
                "bid": "#4CAF50",
                "ask": "#F44336",
                "highlight": "#2196F3"
            },
            "dark": {
                "bg": "#333333",
                "fg": "#f0f0f0",
                "bid": "#81C784",
                "ask": "#E57373",
                "highlight": "#64B5F6"
            }
        }
        
        logger.info("SimulatorApp initialized")
        
    def setup_ui(self):
        """Set up the user interface."""
        self.root = tk.Tk()
        self.root.title("Cryptocurrency Trade Simulator")
        self.root.geometry("1200x800")
        self.root.configure(bg=self.colors[self.theme]["bg"])
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create top frame for order book visualization
        top_frame = ttk.LabelFrame(main_frame, text="Order Book", padding="10")
        top_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        
        # Create bid/ask price display
        bid_ask_frame = ttk.Frame(top_frame)
        bid_ask_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        
        ttk.Label(bid_ask_frame, text="Best Bid:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.bid_ask_labels["bid"] = ttk.Label(bid_ask_frame, text="0.00")
        self.bid_ask_labels["bid"].grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(bid_ask_frame, text="Best Ask:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.bid_ask_labels["ask"] = ttk.Label(bid_ask_frame, text="0.00")
        self.bid_ask_labels["ask"].grid(row=0, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(bid_ask_frame, text="Spread:").grid(row=0, column=4, sticky=tk.W, padx=5)
        self.bid_ask_labels["spread"] = ttk.Label(bid_ask_frame, text="0.00")
        self.bid_ask_labels["spread"].grid(row=0, column=5, sticky=tk.W, padx=5)
        
        ttk.Label(bid_ask_frame, text="Last Update:").grid(row=0, column=6, sticky=tk.W, padx=5)
        self.bid_ask_labels["update_time"] = ttk.Label(bid_ask_frame, text="Never")
        self.bid_ask_labels["update_time"].grid(row=0, column=7, sticky=tk.W, padx=5)
        
        # Create order book depth visualization
        self.depth_canvas = tk.Canvas(top_frame, height=150, bg=self.colors[self.theme]["bg"])
        self.depth_canvas.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Create bottom frame with two columns
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create left panel (input parameters)
        left_frame = ttk.LabelFrame(bottom_frame, text="Trade Parameters", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create right panel (output values)
        right_frame = ttk.LabelFrame(bottom_frame, text="Simulation Results", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add input fields
        self.side_var = tk.StringVar(value="buy")
        ttk.Label(left_frame, text="Order Side:").grid(row=0, column=0, sticky=tk.W, pady=5)
        side_frame = ttk.Frame(left_frame)
        side_frame.grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(side_frame, text="Buy", variable=self.side_var, value="buy").pack(side=tk.LEFT)
        ttk.Radiobutton(side_frame, text="Sell", variable=self.side_var, value="sell").pack(side=tk.LEFT)
        
        self.quantity_var = tk.StringVar()
        ttk.Label(left_frame, text="Quantity (BTC):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(left_frame, textvariable=self.quantity_var).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Add simulate button
        simulate_button = ttk.Button(left_frame, text="Simulate Trade", command=self.on_simulate)
        simulate_button.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Add theme toggle button
        theme_button = ttk.Button(left_frame, text="Toggle Theme", command=self.toggle_theme)
        theme_button.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Add output fields
        result_fields = [
            ("Base Price:", "base_price"),
            ("Executed Price:", "executed_price"),
            ("Slippage:", "slippage_pct", "%"),
            ("Market Impact:", "impact_bps", " bps"),
            ("Fee:", "fee_pct", "%"),
            ("Net Price:", "net_price"),
            ("Total Cost:", "total_cost")
        ]
        
        for i, field_info in enumerate(result_fields):
            if len(field_info) == 2:
                label_text, key = field_info
                suffix = ""
            else:
                label_text, key, suffix = field_info
                
            ttk.Label(right_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, pady=5)
            self.result_labels[key] = ttk.Label(right_frame, text="0.00")
            self.result_labels[key].grid(row=i, column=1, sticky=tk.W, pady=5)
            
            if suffix:
                ttk.Label(right_frame, text=suffix).grid(row=i, column=2, sticky=tk.W, pady=5)
        
        logger.info("UI setup complete")
        
    def start(self):
        """Start the application."""
        self.setup_ui()
        
        # Start WebSocket connection in a separate thread
        ws_thread = threading.Thread(target=self.websocket_client.connect)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Start order book update thread
        update_thread = threading.Thread(target=self.update_order_book_loop)
        update_thread.daemon = True
        update_thread.start()
        
        logger.info("Starting UI main loop")
        self.root.mainloop()
        
    def update_order_book_loop(self):
        """Continuously update the order book display."""
        while True:
            try:
                # Get latest order book data from WebSocket client
                if hasattr(self.websocket_client, 'get_current_order_book'):
                    self.order_book = self.websocket_client.get_current_order_book()
                    self.last_update_time = time.time()
                    self.update_order_book_display()
                
                # Sleep to avoid excessive updates
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error updating order book: {str(e)}")
                time.sleep(1)
                
    def update_order_book_display(self):
        """Update the order book display with latest data."""
        if not self.order_book or 'bids' not in self.order_book or 'asks' not in self.order_book:
            return
            
        # Update bid/ask labels
        if self.order_book['bids']:
            best_bid = self.order_book['bids'][0][0]
            self.bid_ask_labels["bid"].config(text=f"{best_bid:.2f}")
        
        if self.order_book['asks']:
            best_ask = self.order_book['asks'][0][0]
            self.bid_ask_labels["ask"].config(text=f"{best_ask:.2f}")
            
        # Calculate and update spread
        if self.order_book['bids'] and self.order_book['asks']:
            best_bid = self.order_book['bids'][0][0]
            best_ask = self.order_book['asks'][0][0]
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100
            self.bid_ask_labels["spread"].config(text=f"{spread:.2f} ({spread_pct:.3f}%)")
            
        # Update last update time
        elapsed = time.time() - self.last_update_time
        self.bid_ask_labels["update_time"].config(text=f"{elapsed:.1f}s ago")
        
        # Update order book depth visualization
        self.update_depth_visualization()
        
    def update_depth_visualization(self):
        """Update the order book depth visualization."""
        if not self.depth_canvas:
            return
            
        # Clear canvas
        self.depth_canvas.delete("all")
        
        # Get canvas dimensions
        width = self.depth_canvas.winfo_width()
        height = self.depth_canvas.winfo_height()
        
        if width <= 1:  # Not yet properly initialized
            return
            
        # Draw midpoint line
        mid_x = width // 2
        self.depth_canvas.create_line(mid_x, 0, mid_x, height, fill="#999999")
        
        # Get bid and ask data (limit to 10 levels for visualization)
        bids = self.order_book['bids'][:10] if self.order_book['bids'] else []
        asks = self.order_book['asks'][:10] if self.order_book['asks'] else []
        
        if not bids or not asks:
            return
            
        # Calculate price range
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2
        
        # Find max quantity for scaling
        max_qty = max(
            max([qty for _, qty in bids], default=0),
            max([qty for _, qty in asks], default=0)
        )
        
        if max_qty == 0:
            return
            
        # Draw bids (left side)
        bid_color = self.colors[self.theme]["bid"]
        for i, (price, qty) in enumerate(bids):
            # Calculate bar height based on quantity
            bar_height = min(int((qty / max_qty) * height * 0.8), height - 10)
            
            # Calculate x position based on price difference from mid
            price_diff_pct = abs(price - mid_price) / mid_price
            x_offset = int(min(price_diff_pct * 5000, mid_x * 0.9))
            
            # Draw bar
            self.depth_canvas.create_rectangle(
                mid_x - x_offset, height - 5 - bar_height,
                mid_x, height - 5,
                fill=bid_color, outline=""
            )
            
            # Draw price label
            if i % 2 == 0:  # Show every other price to avoid crowding
                self.depth_canvas.create_text(
                    mid_x - x_offset // 2, height - 15,
                    text=f"{price:.1f}", fill=self.colors[self.theme]["fg"], font=("Arial", 8)
                )
        
        # Draw asks (right side)
        ask_color = self.colors[self.theme]["ask"]
        for i, (price, qty) in enumerate(asks):
            # Calculate bar height based on quantity
            bar_height = min(int((qty / max_qty) * height * 0.8), height - 10)
            
            # Calculate x position based on price difference from mid
            price_diff_pct = abs(price - mid_price) / mid_price
            x_offset = int(min(price_diff_pct * 5000, mid_x * 0.9))
            
            # Draw bar
            self.depth_canvas.create_rectangle(
                mid_x, height - 5 - bar_height,
                mid_x + x_offset, height - 5,
                fill=ask_color, outline=""
            )
            
            # Draw price label
            if i % 2 == 0:  # Show every other price to avoid crowding
                self.depth_canvas.create_text(
                    mid_x + x_offset // 2, height - 15,
                    text=f"{price:.1f}", fill=self.colors[self.theme]["fg"], font=("Arial", 8)
                )
        
    def on_simulate(self):
        """Handle the simulate button click event."""
        try:
            # Get input values
            side = self.side_var.get()
            quantity_str = self.quantity_var.get()
            
            # Validate inputs
            if not quantity_str:
                messagebox.showerror("Input Error", "Please enter a quantity")
                return
                
            try:
                quantity = float(quantity_str)
                if quantity <= 0:
                    messagebox.showerror("Input Error", "Quantity must be positive")
                    return
            except ValueError:
                messagebox.showerror("Input Error", "Quantity must be a number")
                return
                
            # Check if we have order book data
            if not self.order_book or 'bids' not in self.order_book or 'asks' not in self.order_book:
                messagebox.showerror("Data Error", "No order book data available")
                return
                
            if not self.order_book['bids'] or not self.order_book['asks']:
                messagebox.showerror("Data Error", "Order book is empty")
                return
                
            # Simulate the trade
            results = self.trade_simulator.simulate_trade(quantity, side, self.order_book)
            
            # Update result labels
            for key, label in self.result_labels.items():
                if key in results:
                    label.config(text=f"{results[key]}")
                    
            logger.info(f"Simulated {side} trade for {quantity} BTC")
            
        except Exception as e:
            logger.error(f"Error simulating trade: {str(e)}")
            messagebox.showerror("Simulation Error", f"An error occurred: {str(e)}")
            
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.theme = "dark" if self.theme == "light" else "light"
        
        # Update root background
        self.root.configure(bg=self.colors[self.theme]["bg"])
        
        # Update depth canvas
        self.depth_canvas.configure(bg=self.colors[self.theme]["bg"])
        
        # Redraw order book visualization
        self.update_depth_visualization()
        
        logger.info(f"Switched to {self.theme} theme")