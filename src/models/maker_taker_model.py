#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Maker/Taker Model
----------------
Estimates the probability of an order being filled as maker or taker
using logistic regression.

"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
import logging

class MakerTakerModel:
    """Model for estimating maker/taker probability."""
    
    def __init__(self):
        """Initialize the maker/taker model."""
        self.model = None
        self.logger = logging.getLogger(__name__)
        
    def train(self, features, labels):
        """
        Train the maker/taker model.
        
        Args:
            features (array-like): Features for prediction (e.g., order size, market volatility)
            labels (array-like): Binary labels (1 for taker, 0 for maker)
        """
        X = np.array(features)
        y = np.array(labels)
        
        self.model = LogisticRegression(random_state=42)
        self.model.fit(X, y)
        self.logger.info("Trained maker/taker model")
        
    def predict_probability(self, features):
        """
        Predict the probability of an order being filled as taker.
        
        Args:
            features (array-like): Features for prediction
            
        Returns:
            float: Probability of being filled as taker (0-1)
        """
        if self.model is None:
            self.logger.warning("Model not trained yet, returning default probability")
            return 0.5  # Default 50% probability
            
        X = np.array([features])
        return float(self.model.predict_proba(X)[0][1])
        
    def calculate_expected_fee(self, order_size, price, maker_fee, taker_fee):
        """
        Calculate expected fee based on maker/taker probability.
        
        Args:
            order_size (float): Size of the order
            price (float): Price of the asset
            maker_fee (float): Maker fee rate
            taker_fee (float): Taker fee rate
            
        Returns:
            float: Expected fee
        """
        # Use default probability if model not trained
        taker_prob = self.predict_probability([order_size, price]) if self.model else 0.5
        maker_prob = 1 - taker_prob
        
        expected_fee = (maker_prob * maker_fee + taker_prob * taker_fee) * order_size * price
        self.logger.info(f"Calculated expected fee: {expected_fee}")
        return expected_fee