# Data dictionary and validation rules

| Table / field | Grain, meaning or units | Validation / use |
|---|---|---|
| `fact_collision` / `collision_mart.parquet` | One reported injury collision | Unique nonempty collision ID |
| `collision_index` | Source collision identifier, string | Preserved as string; parent key |
| `collision_year` | Reporting year | Must equal parsed date year |
| `date`, `date_key` | Local calendar date; YYYYMMDD key | DD/MM/YYYY input; invalid dates rejected |
| `timestamp_local` | GB local event date/time | Missing/invalid time retained as NaT |
| `hour`, `month`, `weekday_number` | 0–23, 1–12, Mon=0…Sun=6 | Missing hour omitted from hourly charts |
| `latitude`, `longitude` | Decimal degrees | GB bounding box 49–61 N, -9–2.5 E; screening is not a country polygon check |
| `collision_severity`, `severity` | 1 Fatal, 2 Serious, 3 Slight | Other target codes rejected |
| `is_severe` | Fatal or serious collision indicator | Used for descriptive shares |
| `number_of_vehicles`, `number_of_casualties` | Recorded collision totals | Minimum 1; outcomes excluded from model |
| `road_type`, `road` | DfT road type and readable label | -1 becomes missing; unmapped labels Unknown |
| `speed_limit` | mph | Only recognized speeds retained; others become missing |
| `first_road_class` | DfT road classification | Categorical model feature |
| `weather_conditions`, `weather` | Recorded weather code and label | DfT record, not API weather |
| `road_surface_conditions`, `surface` | Surface condition code and label | -1 becomes missing |
| `light_conditions`, `lighting` | Daylight/darkness code and label | -1 becomes missing |
| `urban_or_rural_area`, `area` | Urban/rural/unallocated | Categorical model feature |
| `external_temperature_c` | Hourly station temperature in Celsius | Only within 25 km AND matching UTC hour |
| `external_weather_status` | matched / unmatched_location / unmatched_time | Current Berlin input produces 0 matches |
| `observed_vehicle_count`, `observed_casualty_count` | Count of cleaned child rows | Reconciled with reported totals; mismatch flagged |
| `mean_driver_age`, `mean_vehicle_age`, `mean_casualty_age` | Years; cleaned child-group means | Descriptive only; unknown -1 excluded |
| `fatal_casualties` | Fatal casualty count from linked children | Outcome; excluded from model |
| `fact_vehicle` / `vehicle.parquet` | One involved vehicle | Unique collision+vehicle reference; no orphan parent |
| `fact_casualty` / `casualty.parquet` | One casualty | Unique collision+casualty reference; no orphan parent |
| `casualty_class` | 1 driver/rider, 2 passenger, 3 pedestrian | Used in people dashboard |
| `casualty_severity` | Fatal / serious / slight casualty outcome | Separate from collision severity |
| `weather_external.parquet` | One Berlin station UTC-hour temperature | Nulls and duplicate timestamps rejected |
| `dim_date` | One valid collision calendar date | Key `date_key` |
| `dim_road`, `dim_weather`, `dim_severity` | Unique source code lookup | Joining on code preserves fact grain |
| `dim_location` | Unique district/highway/area tuple | Lookup; coordinates remain in collision fact |
| `agg_hour`, `agg_day`, `agg_weekday_number`, `agg_road`, `agg_weather` | Counts and severe/casualty totals per group | Calendar-day aggregate plus weekday aggregate; null hour has own group |
| `model_ready.parquet` | Collision ID, date, target, approved predictors | No outcome-derived predictors |

Additional source columns retain their source names. Consult the official DfT data guide for complete code lists; unknown new categories are preserved numerically and labeled Unknown when unmapped. Numeric child-field -1 sentinels are converted to missing, while reference keys remain untouched. Rejected rows preserve their original collision/child values with a reason column. Child count mismatches are reported rather than silently changing collision totals.
