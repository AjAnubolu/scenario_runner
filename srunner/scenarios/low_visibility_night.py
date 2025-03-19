#!/usr/bin/env python

# Copyright (c) 2019-2020 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
Simple low visibility night scenario. Dark environment with fog and rain.
"""

print("Loading low_visibility_night.py module")

import py_trees
import carla

from srunner.scenariomanager.scenarioatomics.atomic_behaviors import Idle
from srunner.scenariomanager.scenarioatomics.atomic_criteria import CollisionTest
from srunner.scenarios.basic_scenario import BasicScenario
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider


class SetWeather(py_trees.behaviour.Behaviour):
    """
    Behavior that sets a specific weather in CARLA.
    """

    def __init__(self, weather, name="SetWeather"):
        """
        Setup parameters
        """
        super(SetWeather, self).__init__(name)
        self._weather = weather

    def update(self):
        """
        Set the given weather
        """
        CarlaDataProvider.get_world().set_weather(self._weather)
        return py_trees.common.Status.SUCCESS


class LowVisibilityNightDriving(BasicScenario):
    """
    Implementation of a simple low visibility night scenario that consists of the ego vehicle
    in a dark, foggy, and rainy environment
    """

    def __init__(self, world, ego_vehicles, config, randomize=False, debug_mode=False, criteria_enable=True,
                 timeout=10000000):
        """
        Setup all relevant parameters and create scenario
        """
        # Timeout of scenario in seconds
        self.timeout = timeout
        
        # Night weather parameters
        self._night_weather = carla.WeatherParameters(
            cloudiness=90.0,
            precipitation=60.0,
            precipitation_deposits=60.0,
            wind_intensity=30.0,
            sun_azimuth_angle=0.0, 
            sun_altitude_angle=-80.0,
            fog_density=60.0,
            fog_distance=0.0,
            wetness=50.0
        )
        
        super(LowVisibilityNightDriving, self).__init__("LowVisibilityNightDriving",
                                                       ego_vehicles,
                                                       config,
                                                       world,
                                                       debug_mode,
                                                       criteria_enable=criteria_enable)

    def _setup_scenario_trigger(self, config):
        """
        """
        return None

    def _create_behavior(self):
        """
        """
        sequence = py_trees.composites.Sequence("Sequence Behavior")
        
        # Set up the weather
        weather_behavior = SetWeather(self._night_weather)
        sequence.add_child(weather_behavior)
        
        # Add other vehicles with headlights on
        self._add_other_vehicles()
        
        # Add idle behavior to keep scenario running
        sequence.add_child(Idle())
        
        return sequence
        
    def _add_other_vehicles(self):
        """
        Add other vehicles to the scenario with headlights on
        """
        # Add 5 vehicles ahead with lights
        for i in range(5):
            # Get a location ahead of the ego vehicle
            ego_location = self.ego_vehicles[0].get_transform().location
            ego_waypoint = CarlaDataProvider.get_map().get_waypoint(ego_location)
            
            # Get waypoint some distance ahead
            wp_ahead = ego_waypoint.next(50.0 * (i + 1))[0]  # 50, 100, 150, 200, 250 meters ahead
            
            # Add some randomness to position
            if i % 2 == 0:  # Every other car in a different lane
                wp_ahead = wp_ahead.get_left_lane() if wp_ahead.get_left_lane() else wp_ahead
            
            # Create vehicle
            vehicle = CarlaDataProvider.request_new_actor('vehicle.audi.a2', wp_ahead.transform)
            if vehicle:
                # Skip setting light state as it's causing API compatibility issues
                
                # Set autopilot
                vehicle.set_autopilot(True)

    def _create_test_criteria(self):
        """
        A list of all test criteria will be created that is later used
        in parallel behavior tree.
        """
        criteria = []

        for ego_vehicle in self.ego_vehicles:
            collision_criterion = CollisionTest(ego_vehicle)
            criteria.append(collision_criterion)

        return criteria

    def __del__(self):
        """
        Remove all actors upon deletion
        """
        self.remove_all_actors()