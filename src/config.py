from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
PROCESSED = DATA / 'processed'
MODELS = ROOT / 'models'
SEVERITY = {1: 'Fatal', 2: 'Serious', 3: 'Slight'}
ROAD = {1: 'Roundabout', 2: 'One way street', 3: 'Dual carriageway', 6: 'Single carriageway', 7: 'Slip road', 9: 'Unknown', 12: 'One way/slip road'}
WEATHER = {1: 'Fine', 2: 'Rain', 3: 'Snow', 4: 'Fine + high winds', 5: 'Rain + high winds', 6: 'Snow + high winds', 7: 'Fog or mist', 8: 'Other', 9: 'Unknown'}
LIGHT = {1: 'Daylight', 4: 'Dark: lights lit', 5: 'Dark: lights unlit', 6: 'Dark: no lighting', 7: 'Dark: lighting unknown'}
SURFACE = {1: 'Dry', 2: 'Wet or damp', 3: 'Snow', 4: 'Frost or ice', 5: 'Flood', 6: 'Oil or diesel', 7: 'Mud'}
AREA = {1: 'Urban', 2: 'Rural', 3: 'Unallocated'}
FEATURES = ['hour', 'month', 'weekday_number', 'speed_limit', 'road_type', 'first_road_class', 'light_conditions', 'weather_conditions', 'road_surface_conditions', 'urban_or_rural_area', 'latitude', 'longitude']
CATEGORICAL = ['road_type', 'first_road_class', 'light_conditions', 'weather_conditions', 'road_surface_conditions', 'urban_or_rural_area']
FILENAMES = {name: f'dft-road-casualty-statistics-{name}-last-5-years.csv' for name in ['collision', 'vehicle', 'casualty']}
FILENAMES['weather'] = 'open-meteo-52.55N13.41E38m.csv'
