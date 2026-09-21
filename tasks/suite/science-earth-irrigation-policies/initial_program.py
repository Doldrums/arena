"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def irrigate(observed_weather_history, soil_state, crop_stage, remaining_water):
    from autoresearch_suite.science_earth_expansion import irrigation_baseline
    return irrigation_baseline(observed_weather_history, soil_state, crop_stage, remaining_water)
# EVOLVE-BLOCK-END
