# Discus-2cT Lift Calculator

Interactive aerodynamic analysis application for the Discus-2cT glider featuring:
- CL vs AoA plot with realistic stall model and smooth transition
- Classic speed polar (sink rate vs airspeed)  
- Drag polar (CD vs CL) visualization
- Real-time performance summary and calculations

## Version 1 Features
- Comprehensive aerodynamic force modeling (CL/CD calculations)
- Interactive GUI built with PySide6 + Matplotlib/Seaborn
- Realistic stall behavior with smooth exponential decay
- Dynamic range limiting to avoid erratic post-stall behavior
- Multi-configuration support (15m/18m wings, flap settings, ballast)

## Version 2 Roadmap
- Weather API integration (utilizing `program/environment.py` and `program/weather.py`)
- Async agent architecture for:
  - Non-blocking weather data fetching
  - Smooth UI updates without freezing
  - Real-time atmospheric condition monitoring
  - Enhanced performance calculations with live weather data

## Installation & Usage
```bash
pip install -r assets/requirements.txt
python program/main.py
```

## Technical Details
- Built on advanced aerodynamic models with configurable parameters
- Supports various flight conditions: altitude, bank angle, atmospheric conditions
- Real-time wing loading calculations affecting stall characteristics
- Smooth stall modeling with pre-stall buffeting and post-stall exponential decay