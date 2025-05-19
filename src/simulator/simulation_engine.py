#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simulation Engine
---------------
Core engine for running real-time trading simulations with
strategy integration and performance tracking.
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import queue

from src.execution_engine import ExecutionEngine
from src.strategy.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class SimulationMode(Enum):
    """Simulation mode enumeration."""
    BACKTEST = 'backtest'
    REALTIME = 'realtime'

class PlaybackControl(Enum):
    """Playback control commands."""
    PLAY = 'play'
    PAUSE = 'pause'
    STEP = 'step'
    STOP = 'stop'
    RESET = 'reset'

class SimulationEngine:
    """
    Engine for running trading simulations with strategy integration.
    
    Supports both backtest mode (historical data) and real-time mode (live or simulated).
    """
    
    def __init__(self, execution_engine: Optional[ExecutionEngine] = None):
        """
        Initialize the simulation engine.
        
        Args:
            execution_engine: Execution engine instance (creates new one if None)
        """
        self.execution_engine = execution_engine or ExecutionEngine()
        
        # Simulation state
        self.mode = SimulationMode.BACKTEST
        self.is_running = False
        self.playback_speed = 1.0  # Speed multiplier (1.0 = real-time)
        self.playback_control = PlaybackControl.PAUSE
        
        # Data sources
        self.data_queue = queue.Queue()
        self.historical_data = []
        self.current_data_index = 0
        
        # Strategies
        self.strategies = {}  # name -> strategy instance
        
        # Simulation thread
        self.simulation_thread = None
        self.stop_event = threading.Event()
        
        # Performance tracking
        self.execution_reports = []
        
        logger.info("Simulation engine initialized")
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """
        Add a strategy to the simulation.
        
        Args:
            strategy: Strategy instance
        """
        self.strategies[strategy.name] = strategy
        logger.info(f"Added strategy: {strategy.name}")
    
    def remove_strategy(self, strategy_name: str) -> None:
        """
        Remove a strategy from the simulation.
        
        Args:
            strategy_name: Name of the strategy to remove
        """
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            logger.info(f"Removed strategy: {strategy_name}")
    
    def load_historical_data(self, data: List[Dict]) -> None:
        """
        Load historical data for backtest mode.
        
        Args:
            data: List of order book snapshots with timestamps
        """
        self.historical_data = sorted(data, key=lambda x: x.get('timestamp', 0))
        self.current_data_index = 0
        logger.info(f"Loaded {len(data)} historical data points")
    
    def set_mode(self, mode: SimulationMode) -> None:
        """
        Set the simulation mode.
        
        Args:
            mode: Simulation mode (backtest or realtime)
        """
        self.mode = mode
        logger.info(f"Set simulation mode to {mode.value}")
    
    def set_playback_speed(self, speed: float) -> None:
        """
        Set the playback speed for simulation.
        
        Args:
            speed: Speed multiplier (1.0 = real-time)
        """
        if speed <= 0:
            logger.warning(f"Invalid playback speed: {speed}")
            return
            
        self.playback_speed = speed
        logger.info(f"Set playback speed to {speed}x")
    
    def set_playback_control(self, control: PlaybackControl) -> None:
        """
        Set the playback control command.
        
        Args:
            control: Playback control command
        """
        self.playback_control = control
        
        if control == PlaybackControl.PLAY:
            if not self.is_running:
                self.start()
        elif control == PlaybackControl.PAUSE:
            # Simulation continues to run but doesn't process ticks
            pass
        elif control == PlaybackControl.STEP:
            # Process one tick then pause
            old_control = self.playback_control
            self.playback_control = PlaybackControl.PLAY
            # Will be set back to PAUSE after one tick
            self._step_requested = True
        elif control == PlaybackControl.STOP:
            self.stop()
        elif control == PlaybackControl.RESET:
            self.reset()
        
        logger.info(f"Set playback control to {control.value}")
    
    def add_realtime_data(self, data: Dict) -> None:
        """
        Add real-time data to the simulation queue.
        
        Args:
            data: Order book snapshot with timestamp
        """
        self.data_queue.put(data)
    
    def start(self) -> None:
        """Start the simulation."""
        if self.is_running:
            logger.warning("Simulation is already running")
            return
            
        self.is_running = True
        self.stop_event.clear()
        
        # Start all strategies
        for strategy in self.strategies.values():
            strategy.start()
        
        # Start simulation thread
        self.simulation_thread = threading.Thread(target=self._simulation_loop)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        
        logger.info("Simulation started")
    
    def stop(self) -> None:
        """Stop the simulation."""
        if not self.is_running:
            logger.warning("Simulation is not running")
            return
            
        self.is_running = False
        self.stop_event.set()
        
        # Stop all strategies
        for strategy in self.strategies.values():
            strategy.stop()
        
        # Wait for simulation thread to finish
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=5.0)
        
        logger.info("Simulation stopped")
    
    def reset(self) -> None:
        """Reset the simulation to initial state."""
        # Stop if running
        if self.is_running:
            self.stop()
        
        # Reset all strategies
        for strategy in self.strategies.values():
            strategy.reset()
        
        # Reset simulation state
        self.current_data_index = 0
        self.execution_reports = []
        self.data_queue = queue.Queue()
        
        logger.info("Simulation reset")
    
    def _simulation_loop(self) -> None:
        """Main simulation loop."""
        self._step_requested = False
        
        while self.is_running and not self.stop_event.is_set():
            # Check playback control
            if self.playback_control == PlaybackControl.PAUSE:
                time.sleep(0.1)
                continue
            
            # Get next data point
            data = self._get_next_data()
            
            if data is None:
                # End of data
                if self.mode == SimulationMode.BACKTEST:
                    logger.info("End of historical data reached")
                    self.stop()
                    break
                else:
                    # In real-time mode, wait for more data
                    time.sleep(0.1)
                    continue
            
            # Process the data point
            self._process_tick(data)
            
            # If step mode, pause after one tick
            if self._step_requested:
                self.playback_control = PlaybackControl.PAUSE
                self._step_requested = False
            
            # Control simulation speed
            if self.mode == SimulationMode.BACKTEST and self.playback_speed < 100:
                # In backtest mode, sleep to