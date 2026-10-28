import pandas as pd
from src.pipeline import clean_collisions, clean_children


def collision_frame():
    return pd.DataFrame({'collision_index':['a','b','a','d'], 'collision_year':[2024]*4, 'date':['01/02/2024']*4, 'time':['12:30','bad','12:30','12:30'], 'latitude':[51,52,51,0], 'longitude':[-1,-2,-1,0], 'collision_severity':[1,3,1,2], 'number_of_vehicles':[1]*4, 'number_of_casualties':[1]*4, 'speed_limit':[30]*4, 'road_type':[6]*4, 'first_road_class':[3]*4, 'light_conditions':[1]*4, 'weather_conditions':[1]*4, 'road_surface_conditions':[1]*4, 'urban_or_rural_area':[1]*4})


def test_cleaning_dedup_coordinates_and_unknown_time():
    clean, rejected = clean_collisions(collision_frame())
    assert list(clean.collision_index) == ['a','b']
    assert clean.loc[0,'date'] == pd.Timestamp('2024-02-01')
    assert pd.isna(clean.loc[1,'hour'])
    assert len(clean) + len(rejected) == 4
    assert rejected.rejection_reason.str.contains('duplicate_collision_id').sum() == 1
    assert rejected.rejection_reason.str.contains('invalid_gb_coordinates').sum() == 1


def test_children_reject_orphans_and_duplicate_keys():
    children = pd.DataFrame({'collision_index':['a','a','x'], 'vehicle_reference':[1,1,1], 'age_of_driver':[-1,20,30]})
    clean, rejected = clean_children(children, ['a'], ['collision_index','vehicle_reference'])
    assert len(clean) == 1
    assert pd.isna(clean.age_of_driver.iloc[0])
    assert len(rejected) == 2
