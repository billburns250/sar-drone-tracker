"""
CalTopo API Client for SAR Drone Tracker
Handles authentication and track management
"""

import base64
import hmac
import json
import time
import urllib.error
import urllib.request
import logging
from urllib.parse import urlencode
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class CalTopoClient:
    """Client for interacting with CalTopo API"""
    
    def __init__(self, credential_id: str, credential_secret: str, 
                 team_id: str, base_url: str = "https://caltopo.com"):
        self.credential_id = credential_id
        self.credential_secret = credential_secret
        self.team_id = team_id
        self.base_url = base_url
        self.default_timeout_ms = 2 * 60 * 1000  # 2 minutes
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def _sign_request(self, method: str, url: str, expires: int, 
                     payload_string: str) -> str:
        """
        Generate HMAC signature for API request authentication
        """
        message = f"{method} {url}\n{expires}\n{payload_string}"
        secret = base64.b64decode(self.credential_secret)
        signature = hmac.new(secret, message.encode(), "sha256").digest()
        return base64.b64encode(signature).decode()
    
    def _make_request(self, method: str, endpoint: str, 
                     payload: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated request to CalTopo API
        """
        try:
            payload_string = json.dumps(payload) if payload else ""
            expires = int(time.time() * 1000) + self.default_timeout_ms
            
            signature = self._sign_request(method, endpoint, expires, payload_string)
            
            parameters = {
                "id": self.credential_id,
                "expires": expires,
                "signature": signature,
            }
            
            if method.upper() == "POST" and payload is not None:
                parameters["json"] = payload_string
                query_string = ""
                body = urlencode(parameters).encode()
            else:
                query_string = f"?{urlencode(parameters)}"
                body = None
            
            url = f"{self.base_url}{endpoint}{query_string}"
            
            request = urllib.request.Request(url, data=body, method=method.upper())
            request.add_header("Content-Type", "application/x-www-form-urlencoded")
            
            if body is not None:
                request.add_header("Content-Length", str(len(body)))
            
            with urllib.request.urlopen(request) as response:
                response_data = response.read().decode("utf-8")
                if response_data:
                    result = json.loads(response_data)
                    return result.get("result")
                    
        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP Error {e.code}: {e.reason}")
            return None
        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None
    
    def get_team_maps(self, since_timestamp: int = 0) -> Optional[Dict]:
        """
        Get all maps accessible to the team
        """
        endpoint = f"/api/v1/acct/{self.team_id}/since/{since_timestamp}"
        return self._make_request("GET", endpoint)
    
    def get_map_data(self, map_id: str, since_timestamp: int = 0) -> Optional[Dict]:
        """
        Get map data and features
        """
        endpoint = f"/api/v1/map/{map_id}/since/{since_timestamp}"
        return self._make_request("GET", endpoint)
    
    def create_track_line(self, map_id: str, coordinates: List[List[float]], 
                         track_name: str, description: str = "") -> Optional[Dict]:
        """
        Create a new track line on the specified map
        
        Args:
            map_id: CalTopo map ID
            coordinates: List of [longitude, latitude] pairs
            track_name: Name for the track
            description: Optional description
            
        Returns:
            Response from CalTopo API or None if failed
        """
        line_data = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties": {
                "title": track_name,
                "description": description,
                "stroke": "#FF0000",  # Red color
                "stroke-width": 3,
                "stroke-opacity": 0.8,
                "class": "Shape"
            }
        }
        
        endpoint = f"/api/v1/map/{map_id}/Shape"
        return self._make_request("POST", endpoint, line_data)
    
    def update_track_line(self, map_id: str, line_id: str, 
                         coordinates: List[List[float]], 
                         track_name: str, description: str = "") -> Optional[Dict]:
        """
        Update an existing track line
        """
        line_data = {
            "type": "Feature",
            "geometry": {
                "type": "LineString", 
                "coordinates": coordinates
            },
            "properties": {
                "title": track_name,
                "description": description,
                "stroke": "#FF0000",
                "stroke-width": 3,
                "stroke-opacity": 0.8,
                "class": "Shape"
            }
        }
        
        endpoint = f"/api/v1/map/{map_id}/Shape/{line_id}"
        return self._make_request("POST", endpoint, line_data)
    
    def add_drone_marker(self, map_id: str, longitude: float, latitude: float,
                        drone_name: str, timestamp: str, 
                        battery_level: Optional[int] = None) -> Optional[Dict]:
        """
        Add a drone position marker to the map
        
        Args:
            map_id: CalTopo map ID
            longitude: Drone longitude
            latitude: Drone latitude
            drone_name: Name/ID of the drone
            timestamp: Current timestamp string
            battery_level: Optional battery percentage
            
        Returns:
            Response from CalTopo API or None if failed
        """
        description = f"Last seen: {timestamp}"
        if battery_level is not None:
            description += f"\nBattery: {battery_level}%"
            
        marker_data = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude]
            },
            "properties": {
                "title": f"{drone_name} Current Position",
                "description": description,
                "marker-symbol": "airport",  # Drone-like symbol
                "marker-color": "#FF0000",   # Red color
                "marker-size": "medium",
                "class": "Marker"
            }
        }
        
        endpoint = f"/api/v1/map/{map_id}/Marker"
        return self._make_request("POST", endpoint, marker_data)
    
    def delete_old_markers(self, map_id: str, marker_prefix: str) -> None:
        """
        Delete old drone markers to avoid clutter
        """
        try:
            map_data = self.get_map_data(map_id)
            if not map_data:
                return
                
            features = map_data.get("features", [])
            for feature in features:
                if (feature.get("properties", {}).get("class") == "Marker" and
                    feature.get("properties", {}).get("title", "").startswith(marker_prefix)):
                    
                    marker_id = feature.get("id")
                    if marker_id:
                        endpoint = f"/api/v1/map/{map_id}/Marker/{marker_id}"
                        self._make_request("DELETE", endpoint)
                        
        except Exception as e:
            self.logger.error(f"Error deleting old markers: {str(e)}")


class DroneTracker:
    """
    High-level drone tracking functionality using CalTopo
    """
    
    def __init__(self, caltopo_client: CalTopoClient, map_id: str):
        self.client = caltopo_client
        self.map_id = map_id
        self.active_tracks = {}  # drone_id -> track_info
        self.logger = logging.getLogger(__name__)
        
    def start_drone_track(self, drone_id: str, initial_position: Tuple[float, float]) -> bool:
        """
        Start tracking a new drone
        
        Args:
            drone_id: Unique identifier for the drone
            initial_position: (longitude, latitude) tuple
            
        Returns:
            True if successful, False otherwise
        """
        try:
            longitude, latitude = initial_position
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Create initial track with one point
            track_name = f"SAR-Drone-{drone_id}"
            coordinates = [[longitude, latitude]]
            
            result = self.client.create_track_line(
                self.map_id, coordinates, track_name, 
                f"Started: {timestamp}"
            )
            
            if result:
                # Store track information
                self.active_tracks[drone_id] = {
                    "track_id": result.get("id"),
                    "coordinates": coordinates,
                    "track_name": track_name,
                    "start_time": timestamp
                }
                
                # Add current position marker
                self.client.add_drone_marker(
                    self.map_id, longitude, latitude, 
                    f"Drone-{drone_id}", timestamp
                )
                
                self.logger.info(f"Started tracking drone {drone_id}")
                return True
            else:
                self.logger.error(f"Failed to create track for drone {drone_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting drone track: {str(e)}")
            return False
    
    def update_drone_position(self, drone_id: str, 
                            position: Tuple[float, float],
                            battery_level: Optional[int] = None) -> bool:
        """
        Update drone position on the track
        
        Args:
            drone_id: Unique identifier for the drone
            position: (longitude, latitude) tuple
            battery_level: Optional battery percentage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if drone_id not in self.active_tracks:
                # Start new track if drone not being tracked
                return self.start_drone_track(drone_id, position)
            
            longitude, latitude = position
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            track_info = self.active_tracks[drone_id]
            
            # Add new point to coordinates
            track_info["coordinates"].append([longitude, latitude])
            
            # Limit track length to prevent performance issues
            max_points = 1000
            if len(track_info["coordinates"]) > max_points:
                track_info["coordinates"] = track_info["coordinates"][-max_points:]
            
            # Update the track line
            result = self.client.update_track_line(
                self.map_id,
                track_info["track_id"],
                track_info["coordinates"],
                track_info["track_name"],
                f"Updated: {timestamp}"
            )
            
            if result:
                # Delete old marker and add new one
                self.client.delete_old_markers(self.map_id, f"Drone-{drone_id}")
                self.client.add_drone_marker(
                    self.map_id, longitude, latitude,
                    f"Drone-{drone_id}", timestamp, battery_level
                )
                
                self.logger.debug(f"Updated position for drone {drone_id}")
                return True
            else:
                self.logger.error(f"Failed to update track for drone {drone_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating drone position: {str(e)}")
            return False
    
    def stop_drone_track(self, drone_id: str) -> bool:
        """
        Stop tracking a drone (but keep the track visible)
        """
        try:
            if drone_id in self.active_tracks:
                # Remove current position marker
                self.client.delete_old_markers(self.map_id, f"Drone-{drone_id}")
                
                # Remove from active tracking
                del self.active_tracks[drone_id]
                
                self.logger.info(f"Stopped tracking drone {drone_id}")
                return True
            else:
                self.logger.warning(f"Drone {drone_id} was not being tracked")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping drone track: {str(e)}")
            return False
