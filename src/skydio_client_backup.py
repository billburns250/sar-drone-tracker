"""
Skydio Cloud API Client for SAR Drone Tracker
Handles authentication and telemetry data retrieval from Skydio Flight Simulator
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import time


class SkydioClient:
    """Client for interacting with Skydio Cloud API"""
    
    def __init__(self, api_token: str, base_url: str = "https://cloud.skydio.com/api/v1"):
        """
        Initialize Skydio client
        
        Args:
            api_token: Your Skydio API token
            base_url: Base URL for Skydio Cloud API
        """
        self.api_token = api_token
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def _make_request(self, method: str, endpoint: str, 
                     params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated request to Skydio API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            data: Request body data
            
        Returns:
            JSON response or None if failed
        """
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            self.logger.debug(f"Making {method} request to {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            else:
                return {}
                
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test API connection and authentication
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get user profile or organization info
            result = self._make_request("GET", "/user/profile")
            if result is not None:
                self.logger.info("✅ Skydio API connection successful")
                return True
            else:
                self.logger.error("❌ Skydio API connection failed")
                return False
        except Exception as e:
            self.logger.error(f"❌ Connection test failed: {str(e)}")
            return False
    
    def get_vehicles(self) -> Optional[List[Dict]]:
        """
        Get list of vehicles in the fleet
        
        Returns:
            List of vehicle dictionaries or None if failed
        """
        result = self._make_request("GET", "/vehicles")
        if result:
            return result.get("vehicles", [])
        return None
    
    def get_vehicle_info(self, vehicle_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific vehicle
        
        Args:
            vehicle_id: Skydio vehicle ID or serial number
            
        Returns:
            Vehicle information dictionary or None if failed
        """
        return self._make_request("GET", f"/vehicles/{vehicle_id}")
    
    def get_vehicle_status(self, vehicle_id: str) -> Optional[Dict]:
        """
        Get current status of a vehicle (if online)
        
        Args:
            vehicle_id: Skydio vehicle ID
            
        Returns:
            Vehicle status dictionary or None if failed
        """
        return self._make_request("GET", f"/vehicles/{vehicle_id}/status")
    
    def get_flights(self, vehicle_id: Optional[str] = None, 
                   limit: int = 50, offset: int = 0) -> Optional[List[Dict]]:
        """
        Get list of flights
        
        Args:
            vehicle_id: Optional vehicle ID to filter flights
            limit: Maximum number of flights to return
            offset: Number of flights to skip
            
        Returns:
            List of flight dictionaries or None if failed
        """
        params = {"limit": limit, "offset": offset}
        if vehicle_id:
            params["vehicle_id"] = vehicle_id
            
        result = self._make_request("GET", "/flights", params=params)
        if result:
            return result.get("flights", [])
        return None
    
    def get_flight_details(self, flight_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific flight
        
        Args:
            flight_id: Flight ID
            
        Returns:
            Flight details dictionary or None if failed
        """
        return self._make_request("GET", f"/flights/{flight_id}")
    
    def get_flight_telemetry(self, flight_id: str) -> Optional[List[Dict]]:
        """
        Get telemetry data for a specific flight
        
        Args:
            flight_id: Flight ID
            
        Returns:
            List of telemetry points or None if failed
        """
        result = self._make_request("GET", f"/flights/{flight_id}/telemetry")
        if result:
            return result.get("telemetry", [])
        return None
    
    def get_live_telemetry(self, vehicle_id: str) -> Optional[Dict]:
        """
        Get current live telemetry for an active flight
        
        Args:
            vehicle_id: Vehicle ID
            
        Returns:
            Current telemetry data or None if not available
        """
        # This endpoint might vary - common patterns include:
        endpoints_to_try = [
            f"/vehicles/{vehicle_id}/telemetry/current",
            f"/vehicles/{vehicle_id}/live",
            f"/vehicles/{vehicle_id}/status/telemetry"
        ]
        
        for endpoint in endpoints_to_try:
            result = self._make_request("GET", endpoint)
            if result:
                return result
                
        # If no specific live endpoint, try to get the latest from recent flights
        flights = self.get_flights(vehicle_id=vehicle_id, limit=1)
        if flights and len(flights) > 0:
            latest_flight = flights[0]
            # Check if flight is currently active
            if latest_flight.get("status") == "active" or latest_flight.get("in_progress"):
                telemetry = self.get_flight_telemetry(latest_flight["id"])
                if telemetry:
                    # Return the most recent telemetry point
                    return telemetry[-1] if telemetry else None
                    
        return None


class DroneSimulator:
    """
    Simulate drone telemetry data for testing when using Skydio Flight Simulator
    """
    
    def __init__(self, skydio_client: SkydioClient):
        self.client = skydio_client
        self.logger = logging.getLogger(__name__)
        self.simulation_active = False
        self.current_position = None
        
    def start_simulation(self, vehicle_id: str, start_position: Tuple[float, float, float] = None) -> bool:
        """
        Start simulating drone telemetry data
        
        Args:
            vehicle_id: Vehicle to simulate
            start_position: (latitude, longitude, altitude) starting position
            
        Returns:
            True if simulation started successfully
        """
        try:
            if start_position:
                lat, lon, alt = start_position
            else:
                # Default to a location (you can change this to your area)
                lat, lon, alt = 37.4419, -121.7680, 100.0  # Example SAR area
                
            self.current_position = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "vehicle_id": vehicle_id,
                "latitude": lat,
                "longitude": lon,
                "altitude": alt,
                "battery_level": 100,
                "speed": 0.0,
                "heading": 0.0,
                "status": "hovering"
            }
            
            self.simulation_active = True
            self.logger.info(f"Started simulation for vehicle {vehicle_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start simulation: {str(e)}")
            return False
    
    def update_simulation(self, lat_delta: float = 0.0001, lon_delta: float = 0.0001) -> Optional[Dict]:
        """
        Update simulated position (for testing movement)
        
        Args:
            lat_delta: Change in latitude
            lon_delta: Change in longitude
            
        Returns:
            Updated telemetry data or None if simulation not active
        """
        if not self.simulation_active or not self.current_position:
            return None
            
        try:
            # Update position
            self.current_position["latitude"] += lat_delta
            self.current_position["longitude"] += lon_delta
            self.current_position["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Simulate battery drain
            self.current_position["battery_level"] = max(
                self.current_position["battery_level"] - 0.1, 10
            )
            
            # Simulate speed based on movement
            if lat_delta != 0 or lon_delta != 0:
                self.current_position["speed"] = 5.0  # m/s
                self.current_position["status"] = "flying"
            else:
                self.current_position["speed"] = 0.0
                self.current_position["status"] = "hovering"
                
            return self.current_position.copy()
            
        except Exception as e:
            self.logger.error(f"Simulation update failed: {str(e)}")
            return None
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.simulation_active = False
        self.current_position = None
        self.logger.info("Simulation stopped")


class SkydioTelemetryExtractor:
    """
    Extract and normalize telemetry data from Skydio API responses
    """
    
    @staticmethod
    def extract_position_data(telemetry: Dict) -> Optional[Tuple[float, float, Optional[float]]]:
        """
        Extract GPS coordinates from telemetry data
        
        Args:
            telemetry: Raw telemetry dictionary from Skydio API
            
        Returns:
            (longitude, latitude, altitude) tuple or None if not available
        """
        try:
            # Common field names in Skydio telemetry
            lat_fields = ["latitude", "lat", "gps_latitude", "position_lat"]
            lon_fields = ["longitude", "lon", "lng", "gps_longitude", "position_lon"]
            alt_fields = ["altitude", "alt", "elevation", "height", "gps_altitude"]
            
            latitude = None
            longitude = None
            altitude = None
            
            # Try to find latitude
            for field in lat_fields:
                if field in telemetry and telemetry[field] is not None:
                    latitude = float(telemetry[field])
                    break
                    
            # Try to find longitude
            for field in lon_fields:
                if field in telemetry and telemetry[field] is not None:
                    longitude = float(telemetry[field])
                    break
                    
            # Try to find altitude (optional)
            for field in alt_fields:
                if field in telemetry and telemetry[field] is not None:
                    altitude = float(telemetry[field])
                    break
            
            if latitude is not None and longitude is not None:
                return (longitude, latitude, altitude)  # Note: lon, lat order for GeoJSON
            else:
                return None
                
        except (ValueError, TypeError) as e:
            logging.getLogger(__name__).error(f"Error extracting position: {str(e)}")
            return None
    
    @staticmethod
    def extract_battery_level(telemetry: Dict) -> Optional[int]:
        """
        Extract battery level from telemetry data
        
        Args:
            telemetry: Raw telemetry dictionary
            
        Returns:
            Battery percentage (0-100) or None if not available
        """
        try:
            battery_fields = ["battery_level", "battery_percent", "battery", "power_level"]
            
            for field in battery_fields:
                if field in telemetry and telemetry[field] is not None:
                    battery = float(telemetry[field])
                    # Ensure it's in percentage format
                    if battery > 1:
                        return int(battery)  # Already in percentage
                    else:
                        return int(battery * 100)  # Convert from 0-1 to percentage
                        
            return None
            
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def extract_flight_status(telemetry: Dict) -> str:
        """
        Extract flight status from telemetry data
        
        Args:
            telemetry: Raw telemetry dictionary
            
        Returns:
            Flight status string ("flying", "hovering", "landed", "unknown")
        """
        try:
            status_fields = ["status", "flight_status", "vehicle_status", "state"]
            
            for field in status_fields:
                if field in telemetry and telemetry[field] is not None:
                    status = str(telemetry[field]).lower()
                    
                    # Map common status values
                    if "fly" in status or "active" in status:
                        return "flying"
                    elif "hover" in status or "hold" in status:
                        return "hovering"
                    elif "land" in status or "ground" in status:
                        return "landed"
                    else:
                        return status
                        
            return "unknown"
            
        except (ValueError, TypeError):
            return "unknown"
