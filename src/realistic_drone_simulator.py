"""
Realistic SAR Drone Simulator
Creates believable drone telemetry for testing CalTopo integration
"""

import json
import logging
import time
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import random


class RealisticDroneSimulator:
    """
    Simulates realistic SAR drone behavior with authentic telemetry data
    """
    
    def __init__(self, mission_area_center: Tuple[float, float] = (37.4419, -121.7680)):
        """
        Initialize simulator with mission area
        
        Args:
            mission_area_center: (latitude, longitude) of search area center
        """
        self.lat_center, self.lon_center = mission_area_center
        self.logger = logging.getLogger(__name__)
        
        # Active simulations
        self.active_drones = {}
        
        # Realistic SAR search patterns
        self.search_patterns = {
            'grid_search': self._generate_grid_pattern,
            'spiral_search': self._generate_spiral_pattern,
            'parallel_search': self._generate_parallel_pattern,
            'contour_search': self._generate_contour_pattern
        }
        
    def create_drone(self, drone_id: str, pattern: str = 'grid_search', 
                    start_position: Optional[Tuple[float, float]] = None) -> Dict:
        """
        Create a new simulated drone
        
        Args:
            drone_id: Unique identifier for drone
            pattern: Search pattern type
            start_position: Optional (lat, lon) starting position
            
        Returns:
            Initial drone telemetry data
        """
        if start_position:
            start_lat, start_lon = start_position
        else:
            # Random start position within 0.5km of mission center
            start_lat = self.lat_center + random.uniform(-0.005, 0.005)
            start_lon = self.lon_center + random.uniform(-0.005, 0.005)
            
        # Generate search waypoints
        if pattern in self.search_patterns:
            waypoints = self.search_patterns[pattern](start_lat, start_lon)
        else:
            waypoints = self._generate_grid_pattern(start_lat, start_lon)
            
        drone_data = {
            'drone_id': drone_id,
            'pattern': pattern,
            'current_position': 0,
            'waypoints': waypoints,
            'status': 'initializing',
            'battery_level': random.uniform(95, 100),  # Start with full battery
            'altitude': random.uniform(120, 180),  # SAR altitude range
            'speed': 0.0,
            'heading': 0.0,
            'mission_start_time': datetime.now(timezone.utc),
            'last_update': datetime.now(timezone.utc),
            # Realistic drone specs (based on common SAR drones)
            'drone_model': 'Skydio X10',
            'max_flight_time': 35,  # minutes
            'max_speed': 15.0,      # m/s
            'service_ceiling': 300,  # meters AGL
        }
        
        self.active_drones[drone_id] = drone_data
        self.logger.info(f"Created drone {drone_id} with {len(waypoints)} waypoints using {pattern} pattern")
        
        return self._generate_telemetry(drone_id)
    
    def update_drone(self, drone_id: str) -> Optional[Dict]:
        """
        Update drone position and return current telemetry
        
        Args:
            drone_id: Drone to update
            
        Returns:
            Current telemetry data or None if drone doesn't exist
        """
        if drone_id not in self.active_drones:
            return None
            
        drone = self.active_drones[drone_id]
        current_time = datetime.now(timezone.utc)
        
        # Calculate time since last update
        time_delta = (current_time - drone['last_update']).total_seconds()
        drone['last_update'] = current_time
        
        # Update battery (realistic drain rate)
        flight_time_minutes = (current_time - drone['mission_start_time']).total_seconds() / 60
        battery_drain_rate = 100 / drone['max_flight_time']  # Percent per minute
        drone['battery_level'] = max(100 - (flight_time_minutes * battery_drain_rate), 5)
        
        # Update position along waypoints
        if drone['current_position'] < len(drone['waypoints']) - 1:
            self._move_towards_waypoint(drone, time_delta)
        else:
            # Mission complete - return to home or loiter
            if drone['status'] != 'returning_home':
                drone['status'] = 'mission_complete'
                drone['speed'] = 0.0
                
        # Check for low battery
        if drone['battery_level'] < 20 and drone['status'] != 'returning_home':
            drone['status'] = 'low_battery_rtl'
            self.logger.warning(f"Drone {drone_id} initiating return-to-launch due to low battery")
            
        return self._generate_telemetry(drone_id)
    
    def _move_towards_waypoint(self, drone: Dict, time_delta: float):
        """Move drone towards current waypoint"""
        current_wp_idx = drone['current_position']
        waypoints = drone['waypoints']
        
        if current_wp_idx >= len(waypoints):
            return
            
        current_wp = waypoints[current_wp_idx]
        current_lat = current_wp[0]
        current_lon = current_wp[1]
        
        # Check if we've reached current waypoint
        if current_wp_idx + 1 < len(waypoints):
            next_wp = waypoints[current_wp_idx + 1]
            target_lat, target_lon = next_wp[0], next_wp[1]
            
            # Calculate distance to target
            distance = self._calculate_distance(current_lat, current_lon, target_lat, target_lon)
            
            # Realistic speed based on mission phase
            if drone['status'] == 'initializing':
                drone['speed'] = 3.0  # Slow takeoff
                drone['status'] = 'flying'
            elif distance < 0.0001:  # Very close to waypoint (~10 meters)
                drone['speed'] = 2.0  # Slow approach
            else:
                drone['speed'] = random.uniform(8.0, 12.0)  # Normal search speed
                
            # Move towards target
            if distance > 0.00001:  # Not at target yet
                # Calculate bearing
                drone['heading'] = self._calculate_bearing(current_lat, current_lon, target_lat, target_lon)
                
                # Move based on speed and time
                move_distance = (drone['speed'] * time_delta) / 111320  # Convert m/s to degrees
                
                if move_distance >= distance:
                    # Reached waypoint
                    waypoints[current_wp_idx] = [target_lat, target_lon]
                    drone['current_position'] += 1
                    self.logger.debug(f"Drone {drone['drone_id']} reached waypoint {current_wp_idx + 1}")
                else:
                    # Move towards waypoint
                    bearing_rad = math.radians(drone['heading'])
                    new_lat = current_lat + move_distance * math.cos(bearing_rad)
                    new_lon = current_lon + move_distance * math.sin(bearing_rad)
                    waypoints[current_wp_idx] = [new_lat, new_lon]
    
    def _generate_telemetry(self, drone_id: str) -> Dict:
        """Generate realistic telemetry data"""
        if drone_id not in self.active_drones:
            return None
            
        drone = self.active_drones[drone_id]
        current_wp = drone['waypoints'][drone['current_position']]
        
        # Add realistic sensor noise
        lat_noise = random.uniform(-0.000001, 0.000001)  # ~10cm accuracy
        lon_noise = random.uniform(-0.000001, 0.000001)
        alt_noise = random.uniform(-0.5, 0.5)  # 0.5m altitude accuracy
        
        telemetry = {
            # Core navigation data
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'drone_id': drone_id,
            'latitude': current_wp[0] + lat_noise,
            'longitude': current_wp[1] + lon_noise,
            'altitude': drone['altitude'] + alt_noise,
            'heading': drone['heading'] + random.uniform(-2, 2),  # Compass noise
            'speed': drone['speed'] + random.uniform(-0.2, 0.2),
            
            # Power and health
            'battery_level': round(drone['battery_level'], 1),
            'battery_voltage': round(22.2 * (drone['battery_level'] / 100), 2),  # 6S battery
            'battery_current': round(abs(drone['speed']) * 2 + 1, 1),  # Current draw
            
            # Flight status
            'flight_status': drone['status'],
            'flight_mode': 'AUTO' if drone['status'] == 'flying' else 'LOITER',
            'armed': True if drone['status'] in ['flying', 'hovering'] else False,
            
            # Mission progress
            'waypoint_current': drone['current_position'],
            'waypoint_total': len(drone['waypoints']),
            'mission_progress': round((drone['current_position'] / len(drone['waypoints'])) * 100, 1),
            
            # Environmental
            'wind_speed': random.uniform(0, 5),  # m/s
            'wind_direction': random.uniform(0, 360),
            'temperature': random.uniform(15, 25),  # Celsius
            
            # Communication
            'signal_strength': random.randint(85, 100),  # RSSI percentage
            'gps_satellites': random.randint(12, 18),
            'gps_hdop': round(random.uniform(0.8, 1.2), 1),
            
            # Metadata
            'drone_model': drone['drone_model'],
            'firmware_version': '1.2.3',
            'mission_start_time': drone['mission_start_time'].isoformat(),
            'total_flight_time': (datetime.now(timezone.utc) - drone['mission_start_time']).total_seconds(),
        }
        
        return telemetry
    
    def _generate_grid_pattern(self, start_lat: float, start_lon: float) -> List[List[float]]:
        """Generate systematic grid search pattern"""
        waypoints = []
        
        # Grid parameters
        grid_spacing = 0.001  # ~100m spacing
        grid_size = 8  # 8x8 grid
        
        for row in range(grid_size):
            row_waypoints = []
            for col in range(grid_size):
                lat = start_lat + (row * grid_spacing)
                lon = start_lon + (col * grid_spacing)
                row_waypoints.append([lat, lon])
                
            # Alternate direction each row (boustrophedon pattern)
            if row % 2 == 1:
                row_waypoints.reverse()
                
            waypoints.extend(row_waypoints)
            
        return waypoints
    
    def _generate_spiral_pattern(self, start_lat: float, start_lon: float) -> List[List[float]]:
        """Generate expanding spiral search pattern"""
        waypoints = [[start_lat, start_lon]]
        
        radius = 0.0005  # Start radius
        angle = 0
        
        for i in range(60):  # 60 waypoints in spiral
            angle += 30  # 30 degree increments
            radius += 0.0002  # Expanding spiral
            
            lat = start_lat + radius * math.cos(math.radians(angle))
            lon = start_lon + radius * math.sin(math.radians(angle))
            waypoints.append([lat, lon])
            
        return waypoints
    
    def _generate_parallel_pattern(self, start_lat: float, start_lon: float) -> List[List[float]]:
        """Generate parallel track search pattern"""
        waypoints = []
        
        track_length = 0.008  # ~800m tracks
        track_spacing = 0.001  # ~100m between tracks
        num_tracks = 6
        
        for track in range(num_tracks):
            # Start of track
            lat = start_lat + (track * track_spacing)
            lon_start = start_lon
            lon_end = start_lon + track_length
            
            if track % 2 == 0:
                # Even tracks: west to east
                waypoints.append([lat, lon_start])
                waypoints.append([lat, lon_end])
            else:
                # Odd tracks: east to west
                waypoints.append([lat, lon_end])
                waypoints.append([lat, lon_start])
                
        return waypoints
    
    def _generate_contour_pattern(self, start_lat: float, start_lon: float) -> List[List[float]]:
        """Generate contour-following search pattern"""
        waypoints = []
        
        # Simulate following terrain contours (circular-ish pattern)
        center_lat, center_lon = start_lat, start_lon
        
        for angle in range(0, 360, 15):  # 24 waypoints around contour
            radius = 0.003 + 0.001 * math.sin(math.radians(angle * 3))  # Varying radius
            
            lat = center_lat + radius * math.cos(math.radians(angle))
            lon = center_lon + radius * math.sin(math.radians(angle))
            waypoints.append([lat, lon])
            
        return waypoints
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in degrees"""
        return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2 in degrees"""
        return math.degrees(math.atan2(lon2 - lon1, lat2 - lat1))
    
    def get_drone_status(self, drone_id: str) -> Optional[Dict]:
        """Get current status of a drone"""
        if drone_id not in self.active_drones:
            return None
            
        drone = self.active_drones[drone_id]
        return {
            'drone_id': drone_id,
            'status': drone['status'],
            'battery_level': drone['battery_level'],
            'waypoint_progress': f"{drone['current_position']}/{len(drone['waypoints'])}",
            'mission_time': (datetime.now(timezone.utc) - drone['mission_start_time']).total_seconds() / 60,
            'pattern': drone['pattern']
        }
    
    def land_drone(self, drone_id: str):
        """Command drone to land"""
        if drone_id in self.active_drones:
            self.active_drones[drone_id]['status'] = 'landing'
            self.logger.info(f"Commanded drone {drone_id} to land")
    
    def remove_drone(self, drone_id: str):
        """Remove drone from simulation"""
        if drone_id in self.active_drones:
            del self.active_drones[drone_id]
            self.logger.info(f"Removed drone {drone_id} from simulation")
