"""
Final Corrected Skydio Client
Based on actual official example code showing:
- Base URL: https://api.skydio.com/api
- Auth: Authorization: ApiToken {token}
- Version: /v0/
- Response format: {"status_code": 200, "data": {...}}
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import os


class SkydioClient:
    """
    Skydio client based on official example code patterns
    """
    
    def __init__(self, api_token: str, base_url: str = "https://api.skydio.com/api"):
        """
        Initialize Skydio client with correct authentication
        
        Args:
            api_token: Your Skydio API token
            base_url: Base URL for Skydio API
        """
        self.api_token = api_token
        self.base_url = base_url.rstrip('/')
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests - matches official example"""
        if not self.api_token:
            raise EnvironmentError("API_TOKEN is not set.")
        return {
            "Accept": "application/json", 
            "Authorization": f"ApiToken {self.api_token}"
        }
    
    def _make_request(self, method: str, endpoint: str, 
                     params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated request to Skydio API
        """
        try:
            # Build URL with correct base
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            self.logger.debug(f"Making {method} request to {url}")
            
            # Make request with correct headers
            response = requests.request(
                method=method,
                url=url,
                headers=self.get_headers(),
                params=params,
                json=data,
                timeout=30
            )
            
            self.logger.debug(f"Response status: {response.status_code}")
            
            # Parse response
            if response.content:
                response_data = response.json()
                
                # Check Skydio API response format
                status_code = response_data.get("status_code")
                if status_code == 200:
                    return response_data
                else:
                    error_msg = response_data.get("error_message", "Unknown error")
                    self.logger.error(f"API error {status_code}: {error_msg}")
                    return None
            else:
                # Empty response
                if response.status_code == 200:
                    return {"status_code": 200, "data": {}}
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Test API connection using known working endpoint"""
        try:
            # Try the batteries endpoint from the example (known to work)
            result = self._make_request("GET", "v0/batteries")
            
            if result and result.get("status_code") == 200:
                self.logger.info("Skydio API connection successful")
                return True
            else:
                # Try vehicles endpoint
                result = self._make_request("GET", "v0/vehicles")
                if result and result.get("status_code") == 200:
                    self.logger.info("Skydio API connection successful")
                    return True
                    
                self.logger.error("Skydio API connection failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_vehicles(self) -> Optional[List[Dict]]:
        """Get list of vehicles"""
        result = self._make_request("GET", "v0/vehicles")
        
        if result and result.get("status_code") == 200:
            data = result.get("data", {})
            vehicles = data.get("vehicles", [])
            return vehicles
        
        return None
    
    def get_vehicle_details(self, vehicle_id: str) -> Optional[Dict]:
        """Get details for a specific vehicle"""
        result = self._make_request("GET", f"v0/vehicles/{vehicle_id}")
        
        if result and result.get("status_code") == 200:
            return result.get("data", {})
            
        return None
    
    def get_flights(self, vehicle_id: Optional[str] = None, limit: int = 50) -> Optional[List[Dict]]:
        """Get list of flights"""
        params = {"limit": limit}
        if vehicle_id:
            params["vehicle_id"] = vehicle_id
            
        result = self._make_request("GET", "v0/flights", params=params)
        
        if result and result.get("status_code") == 200:
            data = result.get("data", {})
            flights = data.get("flights", [])
            return flights
            
        return None
    
    def get_flight_details(self, flight_id: str) -> Optional[Dict]:
        """Get details for a specific flight"""
        result = self._make_request("GET", f"v0/flights/{flight_id}")
        
        if result and result.get("status_code") == 200:
            return result.get("data", {})
            
        return None
    
    def get_flight_telemetry(self, flight_id: str) -> Optional[List[Dict]]:
        """Get telemetry data for a flight"""
        result = self._make_request("GET", f"v0/flights/{flight_id}/telemetry")
        
        if result and result.get("status_code") == 200:
            data = result.get("data", {})
            telemetry = data.get("telemetry", [])
            return telemetry
            
        return None
    
    def get_live_telemetry(self, vehicle_id: str) -> Optional[Dict]:
        """Get live telemetry for a vehicle"""
        # Try different possible endpoints for live data
        endpoints = [
            f"v0/vehicles/{vehicle_id}/telemetry",
            f"v0/vehicles/{vehicle_id}/status",
            f"v0/vehicles/{vehicle_id}/live"
        ]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result and result.get("status_code") == 200:
                return result.get("data", {})
                
        return None
    
    def get_batteries(self) -> Optional[List[Dict]]:
        """Get all batteries (from the official example)"""
        result = self._make_request("GET", "v0/batteries")
        
        if result and result.get("status_code") == 200:
            data = result.get("data", {})
            batteries = data.get("batteries", [])
            return batteries
            
        return None


# Keep existing telemetry extractor with enhanced Skydio-specific extraction
class SkydioTelemetryExtractor:
    """Extract and normalize telemetry data from Skydio API responses"""
    
    @staticmethod
    def extract_position_data(telemetry: Dict) -> Optional[Tuple[float, float, Optional[float]]]:
        """Extract GPS coordinates from Skydio telemetry data"""
        try:
            # Skydio-specific field patterns
            lat_fields = ["latitude", "lat", "gps_lat", "position_lat"]
            lon_fields = ["longitude", "lon", "lng", "gps_lon", "position_lon"] 
            alt_fields = ["altitude", "alt", "gps_alt", "position_alt", "height"]
            
            latitude = None
            longitude = None
            altitude = None
            
            # Direct field extraction
            for field in lat_fields:
                if field in telemetry and telemetry[field] is not None:
                    latitude = float(telemetry[field])
                    break
                    
            for field in lon_fields:
                if field in telemetry and telemetry[field] is not None:
                    longitude = float(telemetry[field])
                    break
                    
            for field in alt_fields:
                if field in telemetry and telemetry[field] is not None:
                    altitude = float(telemetry[field])
                    break
            
            # Try nested structures common in drone telemetry
            if latitude is None or longitude is None:
                nested_paths = [
                    ["position"], ["location"], ["gps"], ["coordinates"]
                ]
                
                for path_key in nested_paths:
                    if path_key[0] in telemetry and isinstance(telemetry[path_key[0]], dict):
                        nested_data = telemetry[path_key[0]]
                        
                        if latitude is None:
                            for lat_field in lat_fields:
                                if lat_field in nested_data:
                                    latitude = float(nested_data[lat_field])
                                    break
                                    
                        if longitude is None:
                            for lon_field in lon_fields:
                                if lon_field in nested_data:
                                    longitude = float(nested_data[lon_field])
                                    break
                                    
                        if altitude is None:
                            for alt_field in alt_fields:
                                if alt_field in nested_data:
                                    altitude = float(nested_data[alt_field])
                                    break
            
            if latitude is not None and longitude is not None:
                return (longitude, latitude, altitude)  # GeoJSON order: lon, lat
            else:
                return None
                
        except (ValueError, TypeError) as e:
            logging.getLogger(__name__).error(f"Error extracting position: {str(e)}")
            return None
    
    @staticmethod
    def extract_battery_level(telemetry: Dict) -> Optional[int]:
        """Extract battery level from Skydio telemetry"""
        try:
            # Skydio battery field patterns
            battery_fields = [
                "battery_level", "battery_percent", "battery", "battery_charge",
                "power_level", "charge_level", "soc"  # State of charge
            ]
            
            for field in battery_fields:
                if field in telemetry and telemetry[field] is not None:
                    battery = float(telemetry[field])
                    # Convert to percentage if needed
                    if battery <= 1.0:
                        return int(battery * 100)
                    else:
                        return int(battery)
            
            # Check nested battery info
            if "battery" in telemetry and isinstance(telemetry["battery"], dict):
                battery_data = telemetry["battery"]
                for subfield in ["level", "percent", "charge", "soc"]:
                    if subfield in battery_data and battery_data[subfield] is not None:
                        battery = float(battery_data[subfield])
                        if battery <= 1.0:
                            return int(battery * 100)
                        else:
                            return int(battery)
                            
            return None
            
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def extract_flight_status(telemetry: Dict) -> str:
        """Extract flight status from Skydio telemetry"""
        try:
            status_fields = [
                "status", "flight_status", "vehicle_status", "state", 
                "flight_mode", "mode", "flight_state"
            ]
            
            for field in status_fields:
                if field in telemetry and telemetry[field] is not None:
                    status = str(telemetry[field]).lower()
                    
                    # Map Skydio-specific statuses
                    if any(word in status for word in ["flying", "airborne", "active", "auto"]):
                        return "flying"
                    elif any(word in status for word in ["hover", "hovering", "hold", "loiter"]):
                        return "hovering"
                    elif any(word in status for word in ["landed", "ground", "idle", "disarmed"]):
                        return "landed"
                    elif any(word in status for word in ["takeoff", "launching"]):
                        return "taking_off"
                    elif any(word in status for word in ["landing", "descending"]):
                        return "landing"
                    elif any(word in status for word in ["return", "rtl", "rth"]):
                        return "returning_home"
                    else:
                        return status
                        
            return "unknown"
            
        except (ValueError, TypeError):
            return "unknown"
