CREATE INDEX casualty_fk ON fact_casualty(collision_index);

CREATE INDEX collision_date ON fact_collision(date_key);

CREATE UNIQUE INDEX collision_pk ON fact_collision(collision_index);

CREATE INDEX vehicle_fk ON fact_vehicle(collision_index);

CREATE TABLE "agg_day" (
"date" TIMESTAMP,
  "collisions" INTEGER,
  "severe" INTEGER,
  "casualties" INTEGER
);

CREATE TABLE "agg_hour" (
"hour" INTEGER,
  "collisions" INTEGER,
  "severe" INTEGER,
  "casualties" INTEGER
);

CREATE TABLE "agg_road" (
"road" TEXT,
  "collisions" INTEGER,
  "severe" INTEGER,
  "casualties" INTEGER
);

CREATE TABLE "agg_weather" (
"weather" TEXT,
  "collisions" INTEGER,
  "severe" INTEGER,
  "casualties" INTEGER
);

CREATE TABLE "agg_weekday_number" (
"weekday_number" INTEGER,
  "collisions" INTEGER,
  "severe" INTEGER,
  "casualties" INTEGER
);

CREATE TABLE "dim_date" (
"date_key" INTEGER,
  "date" TIMESTAMP,
  "month" INTEGER,
  "weekday" TEXT,
  "weekday_number" INTEGER,
  "collision_year" INTEGER
);

CREATE TABLE "dim_location" (
"local_authority_ons_district" TEXT,
  "local_authority_highway" TEXT,
  "area" TEXT
);

CREATE TABLE "dim_road" (
"road_type" INTEGER,
  "road" TEXT
);

CREATE TABLE "dim_severity" (
"collision_severity" INTEGER,
  "severity" TEXT
);

CREATE TABLE "dim_weather" (
"weather_conditions" REAL,
  "weather" TEXT
);

CREATE TABLE "fact_casualty" (
"collision_index" TEXT,
  "collision_year" INTEGER,
  "collision_ref_no" TEXT,
  "vehicle_reference" INTEGER,
  "casualty_reference" INTEGER,
  "casualty_class" INTEGER,
  "sex_of_casualty" REAL,
  "age_of_casualty" REAL,
  "age_band_of_casualty" REAL,
  "casualty_severity" INTEGER,
  "pedestrian_location" REAL,
  "pedestrian_movement" REAL,
  "car_passenger" REAL,
  "bus_or_coach_passenger" REAL,
  "pedestrian_road_maintenance_worker" REAL,
  "casualty_type" REAL,
  "casualty_imd_decile" REAL,
  "lsoa_of_casualty" TEXT,
  "enhanced_casualty_severity" REAL,
  "casualty_injury_based" INTEGER,
  "casualty_adjusted_severity_serious" REAL,
  "casualty_adjusted_severity_slight" REAL,
  "casualty_distance_banding" REAL,
  "escooter_flag" INTEGER
);

CREATE TABLE "fact_collision" (
"collision_index" TEXT,
  "collision_year" INTEGER,
  "collision_ref_no" TEXT,
  "location_easting_osgr" REAL,
  "location_northing_osgr" REAL,
  "longitude" REAL,
  "latitude" REAL,
  "police_force" INTEGER,
  "collision_severity" INTEGER,
  "number_of_vehicles" INTEGER,
  "number_of_casualties" INTEGER,
  "date" TIMESTAMP,
  "day_of_week" INTEGER,
  "time" TEXT,
  "local_authority_district" INTEGER,
  "local_authority_ons_district" TEXT,
  "local_authority_highway" TEXT,
  "local_authority_highway_current" TEXT,
  "first_road_class" REAL,
  "first_road_number" INTEGER,
  "road_type" INTEGER,
  "speed_limit" REAL,
  "junction_detail_historic" INTEGER,
  "junction_detail" INTEGER,
  "junction_control" INTEGER,
  "second_road_class" INTEGER,
  "second_road_number" INTEGER,
  "pedestrian_crossing_human_control_historic" INTEGER,
  "pedestrian_crossing_physical_facilities_historic" INTEGER,
  "pedestrian_crossing" INTEGER,
  "light_conditions" REAL,
  "weather_conditions" REAL,
  "road_surface_conditions" REAL,
  "special_conditions_at_site" INTEGER,
  "carriageway_hazards_historic" INTEGER,
  "carriageway_hazards" INTEGER,
  "urban_or_rural_area" INTEGER,
  "did_police_officer_attend_scene_of_accident" INTEGER,
  "trunk_road_flag" INTEGER,
  "lsoa_of_accident_location" TEXT,
  "enhanced_severity_collision" INTEGER,
  "collision_injury_based" INTEGER,
  "collision_adjusted_severity_serious" REAL,
  "collision_adjusted_severity_slight" REAL,
  "timestamp_local" TIMESTAMP,
  "hour" INTEGER,
  "month" INTEGER,
  "weekday_number" INTEGER,
  "weekday" TEXT,
  "date_key" INTEGER,
  "severity" TEXT,
  "road" TEXT,
  "weather" TEXT,
  "lighting" TEXT,
  "surface" TEXT,
  "area" TEXT,
  "is_severe" INTEGER,
  "observed_vehicle_count" INTEGER,
  "mean_driver_age" REAL,
  "mean_vehicle_age" REAL,
  "observed_casualty_count" INTEGER,
  "fatal_casualties" INTEGER,
  "mean_casualty_age" REAL,
  "external_temperature_c" REAL,
  "external_weather_status" TEXT
);

CREATE TABLE "fact_vehicle" (
"collision_index" TEXT,
  "collision_year" INTEGER,
  "collision_ref_no" TEXT,
  "vehicle_reference" INTEGER,
  "vehicle_type" REAL,
  "towing_and_articulation" REAL,
  "vehicle_manoeuvre_historic" REAL,
  "vehicle_manoeuvre" REAL,
  "vehicle_direction_from" REAL,
  "vehicle_direction_to" REAL,
  "vehicle_location_restricted_lane_historic" REAL,
  "vehicle_location_restricted_lane" REAL,
  "junction_location" REAL,
  "skidding_and_overturning" REAL,
  "hit_object_in_carriageway" REAL,
  "vehicle_leaving_carriageway" REAL,
  "hit_object_off_carriageway" REAL,
  "first_point_of_impact" REAL,
  "vehicle_left_hand_drive" REAL,
  "journey_purpose_of_driver_historic" REAL,
  "journey_purpose_of_driver" REAL,
  "sex_of_driver" REAL,
  "age_of_driver" REAL,
  "age_band_of_driver" REAL,
  "engine_capacity_cc" REAL,
  "propulsion_code" REAL,
  "age_of_vehicle" REAL,
  "generic_make_model" TEXT,
  "driver_imd_decile" REAL,
  "lsoa_of_driver" TEXT,
  "escooter_flag" INTEGER,
  "driver_distance_banding" REAL
);
