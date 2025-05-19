#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Application UI
-------------
User interface for the cryptocurrency trade simulator.

"""

import tkinter as tk
from tkinter import ttk
import logging
import threading
import time

class ApplicationUI:
    """User interface for the cryptocurrency trade simulator."""
    
    def __init__(self, ws_handler):
        """
        Initialize the application UI.

        Args:
            ws_handler: WebSocket handler instance
        """
        self.ws_handler = ws_handler
        self.root = None
        self.logger = logging.getLogger(__name__)
        self.output_labels = {}  # Add this line
        
    def setup_ui(self):
        """Set up the user interface components."""
        self.root = tk.Tk()
        self.root.title("Cryptocurrency Trade Simulator")
        self.root.geometry("1200x800")
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create left panel (input parameters)
        left_frame = ttk.LabelFrame(main_frame, text="Input Parameters", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create right panel (output values)
        right_frame = ttk.LabelFrame(main_frame, text="Output Values", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create top panel (order book)
        orderbook_frame = ttk.LabelFrame(main_frame, text="Order Book", padding="10")
        orderbook_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add order book summary labels
        ttk.Label(orderbook_frame, text="Best Bid:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.output_labels["best_bid"] = ttk.Label(orderbook_frame, text="0.00")
        self.output_labels["best_bid"].grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(orderbook_frame, text="Best Ask:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.output_labels["best_ask"] = ttk.Label(orderbook_frame, text="0.00")
        self.output_labels["best_ask"].grid(row=0, column=3, sticky=tk.W, pady=2)

        ttk.Label(orderbook_frame, text="Spread:").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.output_labels["spread"] = ttk.Label(orderbook_frame, text="0.00")
        self.output_labels["spread"].grid(row=0, column=5, sticky=tk.W, pady=2)

        # Add Treeview for order book
        columns = ("Type", "Price", "Quantity")
        self.orderbook_tree = ttk.Treeview(orderbook_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.orderbook_tree.heading(col, text=col)
            self.orderbook_tree.column(col, width=100)
        self.orderbook_tree.grid(row=1, column=0, columnspan=6, sticky="nsew", pady=5)
        orderbook_frame.grid_rowconfigure(1, weight=1)
        orderbook_frame.grid_columnconfigure(0, weight=1)

        # Add input fields (placeholders)
        ttk.Label(left_frame, text="Asset:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(left_frame).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(left_frame, text="Order Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(left_frame, values=["Market", "Limit"]).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(left_frame, text="Quantity:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(left_frame).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(left_frame, text="Fee Tier:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(left_frame, values=["VIP 0", "VIP 1", "VIP 2"]).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Add output fields (placeholders)
        ttk.Label(right_frame, text="Slippage:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.output_labels["slippage"] = ttk.Label(right_frame, text="0.00")
        self.output_labels["slippage"].grid(row=0, column=1, sticky=tk.W, pady=5)

        ttk.Label(right_frame, text="Fees:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_labels["fees"] = ttk.Label(right_frame, text="0.00")
        self.output_labels["fees"].grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(right_frame, text="Market Impact:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.output_labels["market_impact"] = ttk.Label(right_frame, text="0.00")
        self.output_labels["market_impact"].grid(row=2, column=1, sticky=tk.W, pady=5)

        ttk.Label(right_frame, text="Latency (ms):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.output_labels["latency"] = ttk.Label(right_frame, text="0")
        self.output_labels["latency"].grid(row=3, column=1, sticky=tk.W, pady=5)

        ttk.Label(right_frame, text="Net Cost:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.output_labels["net_cost"] = ttk.Label(right_frame, text="0.00")
        self.output_labels["net_cost"].grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Add simulate button
        ttk.Button(main_frame, text="Simulate Trade").pack(pady=10)
        
        self.logger.info("UI setup complete")

    def update_orderbook_tree(self, bids, asks):
        """Update the order book Treeview with bids and asks."""
        self.orderbook_tree.delete(*self.orderbook_tree.get_children())
        # Show top 5 bids and asks
        for price, qty in bids[:5]:
            self.orderbook_tree.insert("", "end", values=("Bid", f"{float(price):.2f}", f"{float(qty):.4f}"))
        for price, qty in asks[:5]:
            self.orderbook_tree.insert("", "end", values=("Ask", f"{float(price):.2f}", f"{float(qty):.4f}"))

    def update_simulation_results(self, results):
        """Update the simulation results section with new data."""
        for key in ["slippage", "fees", "market_impact", "latency", "net_cost"]:
            if key in results and key in self.output_labels:
                self.output_labels[key].config(text=f"{results[key]:.2f}")

    def update_ui(self):
        """Update UI with latest data from WebSocket and simulation."""
        if hasattr(self.ws_handler, 'latest_data') and self.ws_handler.latest_data:
            data = self.ws_handler.latest_data

            # Update order book display
            if 'bids' in data and data['bids'] and 'asks' in data and data['asks']:
                best_bid = float(data['bids'][0][0])
                best_ask = float(data['asks'][0][0])
                spread = best_ask - best_bid

                self.output_labels["best_bid"].config(text=f"{best_bid:.2f}")
                self.output_labels["best_ask"].config(text=f"{best_ask:.2f}")
                self.output_labels["spread"].config(text=f"{spread:.2f}")
                self.update_orderbook_tree(data['bids'], data['asks'])

            # If simulation results are available, update them
            if hasattr(self.ws_handler, 'simulation_results') and self.ws_handler.simulation_results:
                self.update_simulation_results(self.ws_handler.simulation_results)

        # Schedule the next update
        self.root.after(1000, self.update_ui)
        
    def run(self):
        """Run the application."""
        self.setup_ui()

        # Start WebSocket connection in a separate thread
        ws_thread = threading.Thread(target=self.ws_handler.connect)
        ws_thread.daemon = True
        ws_thread.start()

        # Start UI update loop
        self.update_ui()  # Add this line

        self.logger.info("Starting UI main loop")
        self.root.mainloop()