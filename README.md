# RejseplanenAPI

A comprehensive Python wrapper for the Danish Rejseplanen API with visualization capabilities.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/FPWRasmussen/RejseplanenAPI.git
cd RejseplanenAPI
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Requirements

- Python 3.8+
- requests >= 2.31.0
- matplotlib >= 3.7.0
- numpy >= 1.24.0

## Quick Start

```python
from main import RejseplanenAPI, LocationType

# Initialize the API
api = RejseplanenAPI()

# Search for locations
locations = api.location_search("Copenhagen Central", LocationType.ALL)
print(f"Found {len(locations)} locations")

# Plan a trip
origin = "Copenhagen Central Station"
destination = "Aarhus Central Station"
date = "2025-09-15"
time = "14:00"

trips = api.trip_search(origin, destination, date, time)
print(f"Found {len(trips)} possible trips")

# Visualize trips
from demo import plot_trips
plot_trips(trips, api.common_data, max_trips=2)
```

## Usage Examples

### Basic Trip Search
```python
from main import RejseplanenAPI

api = RejseplanenAPI()

# Simple trip search
trips = api.trip_search("Copenhagen H", "Aarhus H", "2025-09-15", "12:00")

for i, trip in enumerate(trips[:3]):
    print(f"Trip {i+1}: {trip.duration} minutes, {trip.changes} changes")
```

### Real-time Departures
```python
# Get departures from a station
departures = api.departure_board("Copenhagen Central", date="2025-09-15", time="14:00")

for dep in departures[:5]:
    print(f"{dep.name} to {dep.direction} at {dep.time}")
```

### Location Search
```python
from main import LocationType

# Search for addresses
addresses = api.location_search("Nyhavn 1", LocationType.ADDRESS)

# Search for stations
stations = api.location_search("Central", LocationType.STATION)
```

## Demo

Run the demo script to see visualization examples:
```bash
python demo.py
```

The demo includes:
- Trip visualization with walking routes
- Interactive plotting of transportation networks
- Comparison of multiple trip options

## API Documentation

- `location_search(query, type)` - Search for locations
- `trip_search(origin, destination, date, time)` - Plan trips
- `departure_board(station, date, time)` - Get real-time departures
- `arrival_board(station, date, time)` - Get real-time arrivals
- `journey_detail(journey_ref)` - Get detailed journey information

## Data Structures

- `Trip` - Complete trip information
- `Location` - Location data (stations, addresses, POIs)
- `Journey` - Individual journey segments
- `Section` - Trip sections (walking/transit)
- `ServiceDays` - Service schedule information

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

