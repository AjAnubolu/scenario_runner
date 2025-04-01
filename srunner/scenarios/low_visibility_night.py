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
import time

from srunner.scenariomanager.scenarioatomics.atomic_behaviors import Idle
from srunner.scenariomanager.scenarioatomics.atomic_criteria import CollisionTest
from srunner.scenarios.basic_scenario import BasicScenario
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider


class LatencyProfiler:
    """
    Simple profiler for tracking task latency within frames
    """
    def __init__(self):
        self.tasks = {}
        self.current_frame = 0
        self.frame_data = {}
        self.running_tasks = {}
        self.should_profile = False
        self.complete_report = []
        # Store current frame metrics for HUD display
        self.current_metrics = {}
        # Store recent history for moving average
        self.metrics_history = {}
        self.history_length = 30  # Number of frames to keep for moving average
        
        # Import numpy up front to avoid import inside the report generation
        try:
            import numpy as np
            self.np = np
        except ImportError:
            print("WARNING: NumPy not available. Statistical analysis will be limited.")
            self.np = None

    def start_profiling(self):
        """Enable profiling"""
        self.should_profile = True
        self.current_frame = 0
        self.frame_data = {}
        self.running_tasks = {}
        self.complete_report = []
        print("Latency profiling enabled")

    def stop_profiling(self):
        """Disable profiling and generate report"""
        self.should_profile = False
        return self.generate_report()

    def start_frame(self):
        """Start a new frame for profiling"""
        if not self.should_profile:
            return
        
        self.current_frame += 1
        self.frame_data[self.current_frame] = {}
        # Clear current metrics for the new frame
        self.current_metrics = {}

    def end_frame(self):
        """End the current frame and close any lingering tasks"""
        if not self.should_profile:
            return
            
        # Close any tasks still running at end of frame
        still_running = list(self.running_tasks.keys())
        for task in still_running:
            self.end_task(task)
            
        # Add frame data to complete report
        if self.current_frame in self.frame_data:
            self.complete_report.append({
                "frame": self.current_frame,
                "tasks": self.frame_data[self.current_frame]
            })

    def start_task(self, task_name):
        """Start timing a specific task"""
        if not self.should_profile:
            return
            
        if task_name not in self.tasks:
            self.tasks[task_name] = 0
            
        self.running_tasks[task_name] = time.time()

    def end_task(self, task_name):
        """End timing a specific task"""
        if not self.should_profile or task_name not in self.running_tasks:
            return
            
        elapsed = (time.time() - self.running_tasks[task_name]) * 1000  # Convert to ms
        
        if self.current_frame not in self.frame_data:
            self.frame_data[self.current_frame] = {}
            
        self.frame_data[self.current_frame][task_name] = elapsed
        
        # Update current metrics for HUD display
        self.current_metrics[task_name] = elapsed
        
        # Update metrics history for moving average
        if task_name not in self.metrics_history:
            self.metrics_history[task_name] = []
            
        self.metrics_history[task_name].append(elapsed)
        if len(self.metrics_history[task_name]) > self.history_length:
            self.metrics_history[task_name].pop(0)
            
        del self.running_tasks[task_name]

    def get_current_metrics(self):
        """Return current metrics with moving averages for HUD display"""
        if not self.should_profile:
            return {}
            
        result = {}
        for task_name, history in self.metrics_history.items():
            if history:
                avg = sum(history) / len(history)
                
                current = 0
                if task_name in self.current_metrics:
                    current = self.current_metrics[task_name]
                elif task_name in self.frame_data.get(self.current_frame, {}):
                    current = self.frame_data[self.current_frame][task_name]
                elif history:
                    current = history[-1]
                    
                result[task_name] = {
                    'current': current,
                    'average': avg
                }
        return result
        
    def generate_report(self):
        """Generate a text report of all profiling data with statistics"""
        if not self.complete_report:
            return "No profiling data available"
        
        # Collect all task durations by task name
        task_stats = {}
        for frame_data in self.complete_report:
            for task_name, duration in frame_data["tasks"].items():
                if task_name not in task_stats:
                    task_stats[task_name] = []
                task_stats[task_name].append(duration)
        
        # Generate report
        report = "Latency Profiling Report:\n"
        report += "========================\n\n"
        
        # Print individual frame data (show only last 5 frames for brevity)
        max_frames_to_show = 5
        frames_to_show = self.complete_report[-max_frames_to_show:] if len(self.complete_report) > max_frames_to_show else self.complete_report
        
        for frame_data in frames_to_show:
            frame_num = frame_data["frame"]
            report += f"Frame {frame_num}:\n"
            
            for task_name, duration in frame_data["tasks"].items():
                report += f"  {task_name}: {duration:.2f} ms\n"
            
            report += "\n"
        
        # Add statistical summary
        report += "Statistical Summary:\n"
        report += "====================\n\n"
        
        for task_name, durations in task_stats.items():
            if not durations:
                continue
                
            # Calculate statistics
            if self.np:
                # Use NumPy for accurate statistics
                mean = self.np.mean(durations)
                std_dev = self.np.std(durations)
                variance = self.np.var(durations)
                minimum = self.np.min(durations)
                maximum = self.np.max(durations)
            else:
                # Fallback to basic Python statistics if NumPy not available
                mean = sum(durations) / len(durations)
                variance = sum((x - mean) ** 2 for x in durations) / len(durations)
                std_dev = variance ** 0.5
                minimum = min(durations)
                maximum = max(durations)
            
            report += f"Task: {task_name}\n"
            report += f"  Count: {len(durations)}\n"
            report += f"  Mean: {mean:.2f} ms\n"
            report += f"  Std Dev: {std_dev:.2f} ms\n"
            report += f"  Variance: {variance:.2f} ms²\n"
            report += f"  Min: {minimum:.2f} ms\n"
            report += f"  Max: {maximum:.2f} ms\n"
            report += "\n"
            
        return report


# Global profiler instance
latency_profiler = LatencyProfiler()


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
        latency_profiler.start_task("weather")
        CarlaDataProvider.get_world().set_weather(self._weather)
        latency_profiler.end_task("weather")
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
        latency_profiler.start_task("weather")
        self._night_weather = carla.WeatherParameters(
            cloudiness=60.0,           # Further reduced cloudiness for more light
            precipitation=40.0,        # Less rain for better visibility
            precipitation_deposits=50.0,
            wind_intensity=25.0,
            sun_azimuth_angle=0.0, 
            sun_altitude_angle=-40.0,  # Much higher sun angle (early dusk)
            fog_density=30.0,          # Significantly reduced fog
            fog_distance=20.0,         # Greater fog distance for visibility
            wetness=40.0              # Less wetness
        )
        latency_profiler.end_task("weather")
        
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
        latency_profiler.start_task("scenario_setup")
        sequence = py_trees.composites.Sequence("Sequence Behavior")
        
        # Set up the weather - measure separately to ensure weather profiling
        latency_profiler.start_task("weather")
        weather_behavior = SetWeather(self._night_weather)
        latency_profiler.end_task("weather")
        sequence.add_child(weather_behavior)
        
        # Add other vehicles with headlights on
        self._add_other_vehicles()
        
        # Add idle behavior to keep scenario running
        sequence.add_child(Idle())
        
        latency_profiler.end_task("scenario_setup")
        return sequence
        
    def _add_other_vehicles(self):
        """
        Add other vehicles to the scenario with headlights on
        """
        latency_profiler.start_task("vehicles")
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
            latency_profiler.start_task(f"spawn_vehicle_{i}")
            vehicle = CarlaDataProvider.request_new_actor('vehicle.audi.a2', wp_ahead.transform)
            latency_profiler.end_task(f"spawn_vehicle_{i}")
            
            if vehicle:
                # Skip setting light state as it's causing API compatibility issues
                
                # Set autopilot
                latency_profiler.start_task("vehicles")
                vehicle.set_autopilot(True)
                latency_profiler.end_task("vehicles")
        
        latency_profiler.end_task("vehicles")

    def _create_test_criteria(self):
        """
        A list of all test criteria will be created that is later used
        in parallel behavior tree.
        """
        latency_profiler.start_task("scenario_setup")
        criteria = []

        for ego_vehicle in self.ego_vehicles:
            collision_criterion = CollisionTest(ego_vehicle)
            criteria.append(collision_criterion)

        latency_profiler.end_task("scenario_setup")
        return criteria

    def __del__(self):
        """
        Remove all actors upon deletion
        """
        self.remove_all_actors()