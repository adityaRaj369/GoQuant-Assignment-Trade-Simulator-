
# Cryptocurrency Trade Simulator

A comprehensive Python-based trading simulator that mimics real-world cryptocurrency markets using real-time Level-2 (L2) order book data. This project provides a robust framework for simulating and backtesting trading strategies with realistic execution, slippage, market impact, and fee modeling.

---

## 📌 Features Overview

- **Real-Time L2 Order Book Feed** from OKX via WebSocket
- **Realistic Execution Engine** (market/limit orders, latency, partial fills)
- **Slippage and Market Impact Modeling**
- **Maker/Taker Fee Structure** with dynamic VIP profile support
- **Custom Trading Strategy Framework** (Momentum, Mean Reversion)
- **Backtesting and Real-Time Simulation Modes**
- **Interactive GUI built with Tkinter**
- **Advanced Performance Metrics and Risk Management**

---

## 🧠 Project Architecture

### Phase 1: WebSocket Integration & Order Book Handling
- Connected to OKX's WebSocket to fetch L2 order book data
- Parsed and updated local order book snapshots in real-time
- Displayed top-of-book data for bid/ask via Tkinter UI

### Phase 2: Order Management System
- Created a limit/market order system
- Supported marketable limit orders
- Added partial fill logic and order queuing
- Implemented order book walking for market order simulation

### Phase 3: Latency and Trade Classification
- Modeled network latency and execution delay
- Classified orders as **maker** or **taker**
- Developed partial fill and order expiration logic

### Phase 4: Execution Models
- Implemented:
  - ✅ `ExecutionEngine` (realistic fills)
  - ✅ `SlippageModel` (depth-based and ML-based)
  - ✅ `MarketImpactModel` (Almgren–Chriss model)
  - ✅ `MakerTakerFeeModel` (tiered, volume-based fees)
- Supported user profiles (retail, institutional, market maker)

### Phase 5: Strategy & Simulation Framework
- Designed an abstract `BaseStrategy` class
- Implemented:
  - `MomentumStrategy` (price breakout + volume)
  - `MeanReversionStrategy` (deviation from MA)
- Created `SimulationEngine` for managing simulation states (play, pause, step)
- Integrated execution engine, models, and GUI into a full simulator

### Phase 6 (Optional): ML Models
- Placeholder added for AI/ML integration for strategy learning (optional & experimental)

---

## 🎯 Strategy Features

- Momentum & Mean Reversion logic with customizable parameters
- Backtesting historical scenarios or using live L2 order book data
- Strategy evaluation with:
  - 📈 Sharpe Ratio
  - 📊 Profit Factor
  - ❌ Max Drawdown
  - 💰 Total PnL
  - 📉 Equity Curve

---

## 🧪 Risk Management

- Max position size limits
- Capital allocation rules
- Stop-loss and take-profit support
- Max drawdown triggers

---

## 🖥️ GUI Features (Tkinter)

- Real-time order book visualization
- Parameter controls for strategies
- Trade execution visualization
- Simulation controls: play, pause, step
- Theme toggle (light/dark mode)

---

## 🚀 How to Run

1. **Install dependencies:**

```bash
pip install -r requirements.txt
````

2. **Run the simulator:**

```bash
python app.py
```

3. **Adjust Parameters** via the UI or edit strategy files as needed.

---

## 📁 Project Structure

```
.
├── strategies/
│   ├── base_strategy.py
│   ├── momentum_strategy.py
│   └── mean_reversion_strategy.py
├── models/
│   ├── execution_engine.py
│   ├── slippage_model.py
│   ├── market_impact_model.py
│   ├── fee_model.py
├── websocket/
│   └── okx_l2_feed.py
├── simulator/
│   ├── simulation_engine.py
│   ├── performance_metrics.py
├── ui/
│   └── simulator_app.py
├── app.py
└── README.md
```

---

## 📌 Requirements

* Python 3.8+
* `websockets`, `numpy`, `pandas`, `tkinter`, `sklearn`, `matplotlib`, etc.

---

## 📚 Future Scope

* Add more AI/ML-based strategy generation
* Support for other exchanges (Binance, Coinbase)
* Historical data replay and import
* Multi-strategy portfolio backtesting

---

## 🏁 Final Note

This simulator is designed for educational and research purposes and is an excellent base for further development in algorithmic trading, market microstructure modeling, and AI-based trading strategy research.
