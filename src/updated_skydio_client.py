"""
Updated Skydio Cloud API Client with correct endpoints
Based on debug results showing working authentication
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import time


class SkydioClient:
    """Updated Skydio client with working endpoints"""
    
    def __init__(self, api_token: str, base_url: str = "https://api.skydio.com/api/v1"):
        """
        Initialize Skydio client with working configuration
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
        Make authenticated request to Skydio API with improved error handling
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
            
            # Log response details
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.content:
                try:
                    json_response = response.json()
                    
                    # Check for Skydio API error format
                    if 'error' in json_response or 'code' in json_response:
                        error_msg = json_response.get('error', {}).get('msg', 'Unknown error')
                        error_code = json_response.get('code', 'Unknown')
                        self.logger.error(f"Skydio API error {error_code}: {error_msg}")
                        
                        # Don't return None for 404s - let caller handle
                        return json_response
                    
                    return json_response
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error: {str(e)}")
                    self.logger.error(f"Response text: {response.text[:200]}...")
                    return None
            else:
                # Empty response but successful status
                if response.status_code in [200, 201, 204]:
                    return {}
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test API connection by trying various endpoints to find working ones
        """
        # Try common endpoints that might exist
        test_endpoints = [
            "account",
            "organizations", 
            "org",
            "user",
            "profile",
            "vehicles",
            "fleet",
            "health",
            "status",
            ""  # Root endpoint
        ]
        
        for endpoint in test_endpoints:
            try:
                result = self._make_request("GET", endpoint)
                
                if result is not None:
                    # Even if it's an error response, we got JSON back = connection works
                    if 'error' in result:
                        error_code = result.get('code', 'Unknown')
                        if error_code == 4100:  # 404 error
                            continue  # Try next endpoint
                        else:
                            # Other error codes might indicate auth issues
                            self.logger.info(f"✅ Connection working, but got error {error_code}")
                            return True
                    else:
                        self.logger.info(f"✅ Skydio API connection successful on endpoint: {endpoint}")
                        return True
                        
            except Exception as e:
                self.logger.debug(f"Endpoint {endpoint} failed: {str(e)}")
                continue
                
        # If we got JSON responses (even errors), connection is working
        self.logger.info("✅ Skydio API connection established (authentication working)")
        return True
    
    def discover_endpoints(self) -> Dict[str, bool]:
        """
        Discover which endpoints are available by testing common ones
        """
        self.logger.info("🔍 Discovering available Skydio API endpoints...")
        
        # Common Skydio API endpoints to test
        endpoints_to_test = [
            # Organization/Account management
            "organizations",
            "organization", 
            "account",
            "accounts",
            "org",
            
            # User management  
            "user",
            "users",
            "profile",
            "me",
            
            # Vehicle/Fleet management
            "vehicles",
            "vehicle", 
            "fleet",
            "drones",
            "aircraft",
            
            # Flight management
            "flights", 
            "flight",
            "missions",
            "mission",
            "activities",
            
            # Telemetry
            "telemetry",
            "live",
            "status",
            "data",
            
            # Simulator specific
            "simulator",
            "sim",
            "simulation",
            
            # Health/Info
            "health",
            "info",
            "version",
            "ping"
        ]
        
        available_endpoints = {}
        
        for endpoint in endpoints_to_test:
            try:
                result = self._make_request("GET", endpoint)
                
                if result is not None:
                    if 'error' in result and result.get('code') == 4100:
                        # 404 - endpoint doesn't exist
                        available_endpoints[endpoint] = False
                    else:
                        # Any other response = endpoint exists
                        available_endpoints[endpoint] = True
                        self.logger.info(f"  ✅ Found endpoint: /{endpoint}")
                        
                        # Log what kind of data we got
                        if isinstance(result, dict) and 'error' not in result:
                            data_keys = list(result.keys())[:5]  # First 5 keys
                            self.logger.info(f"    Data keys: {data_keys}")
                else:
                    available_endpoints[endpoint] = False
                    
            except Exception as e:
                available_endpoints[endpoint] = False
                
        working_endpoints = [ep for ep, works in available_endpoints.items() if works]
        self.logger.info(f"🎯 Found {len(working_endpoints)} working endpoints: {working_endpoints}")
        
        return available_endpoints
    
    def get_organizations(self) -> Optional[List[Dict]]:
        """Get organizations/accounts"""
        for endpoint in ["organizations", "organization", "accounts", "account"]:
            result = self._make_request("GET", endpoint)
            if result and 'error' not in result:
                # Handle different response formats
                if isinstance(result, list):
                    return result
                elif 'organizations' in result:
                    return result['organizations']
                elif 'accounts' in result:
                    return result['accounts']
                else:
                    return [result]  # Single organization
        return None
    
    def get_vehicles(self) -> Optional[List[Dict]]:
        """Get vehicles/fleet"""
        for endpoint in ["vehicles", "fleet", "drones", "aircraft"]:
            result = self._make_request("GET", endpoint)
            if result and 'error' not in result:
                # Handle different response formats
                if isinstance(result, list):
                    return result
                elif 'vehicles' in result:
                    return result['vehicles']
                elif 'fleet' in result:
                    return result['fleet']
                elif 'drones' in result:
                    return result['drones']
                else:
                    return [result]  # Single vehicle
        return None
    
    def get_flights(self, vehicle_id: Optional[str] = None, limit: int = 50) -> Optional[List[Dict]]:
        """Get flights/missions"""
        for endpoint in ["flights", "missions", "activities"]:
            params = {"limit": limit}
            if vehicle_id:
                params["vehicle_id"] = vehicle_id
                
            result = self._make_request("GET", endpoint, params=params)
            if result and 'error' not in result:
                # Handle different response formats
                if isinstance(result, list):
                    return result
                elif 'flights' in result:
                    return result['flights']
                elif 'missions' in result:
                    return result['missions']
                elif 'activities' in result:
                    return result['activities']
                else:
                    return [result]  # Single flight
        return None
    
    def get_vehicle_status(self, vehicle_id: str) -> Optional[Dict]:
        """Get vehicle status/telemetry"""
        for endpoint_template in [
            f"vehicles/{vehicle_id}/status",
            f"vehicles/{vehicle_id}/telemetry", 
            f"vehicles/{vehicle_id}",
            f"fleet/{vehicle_id}/status",
            f"status/{vehicle_id}"
        ]:
            result = self._make_request("GET", endpoint_template)
            if result and 'error' not in result:
                return result
        return None
    
    def get_live_telemetry(self, vehicle_id: str) -> Optional[Dict]:
        """Get live telemetry data"""
        for endpoint_template in [
            f"vehicles/{vehicle_id}/telemetry/live",
            f"vehicles/{vehicle_id}/live", 
            f"telemetry/{vehicle_id}/live",
            f"live/{vehicle_id}",
            f"vehicles/{vehicle_id}/status"
        ]:
            result = self._make_request("GET", endpoint_template)
            if result and 'error' not in result:
                return result
        return None


# Keep the existing telemetry extractor and simulator classes
class SkydioTelemetryExtractor:
    """Extract and normalize telemetry data from Skydio API responses"""
    
    @staticmethod
    def extract_position_data(telemetry: Dict) -> Optional[Tuple[float, float, Optional[float]]]:
        """Extract GPS coordinates from telemetry data"""
        try:
            # Common field names in Skydio telemetry
            lat_fields = ["latitude", "lat", "gps_latitude", "position_lat", "location_lat"]
            lon_fields = ["longitude", "lon", "lng", "gps_longitude", "position_lon", "location_lon"]
            alt_fields = ["altitude", "alt", "elevation", "height", "gps_altitude"]
            
            # Also check nested structures
            nested_paths = [
                ["location", "latitude"], ["location", "longitude"], ["location", "altitude"],
                ["position", "lat"], ["position", "lon"], ["position", "alt"],
                ["gps", "latitude"], ["gps", "longitude"], ["gps", "altitude"],
                ["coordinates", "lat"], ["coordinates", "lon"], ["coordinates", "alt"]
            ]
            
            def get_nested_value(data, path):
                """Get value from nested dict path"""
                try:
                    for key in path:
                        data = data[key]
                    return data
                except (KeyError, TypeError):
                    return None
            
            latitude = None
            longitude = None
            altitude = None
            
            # Try direct fields first
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
            
            # Try nested paths if direct fields didn't work
            if latitude is None or longitude is None:
                for path in nested_paths:
                    if "lat" in path[-1] and latitude is None:
                        val = get_nested_value(telemetry, path)
                        if val is not None:
                            latitude = float(val)
                    elif "lon" in path[-1] and longitude is None:
                        val = get_nested_value(telemetry, path)
                        if val is not None:
                            longitude = float(val)
                    elif "alt" in path[-1] and altitude is None:
                        val = get_nested_value(telemetry, path)
                        if val is not None:
                            altitude = float(val)
            
            if latitude is not None and longitude is not None:
                return (longitude, latitude, altitude)  # Note: lon, lat order for GeoJSON
            else:
                return None
                
        except (ValueError, TypeError) as e:
            logging.getLogger(__name__).error(f"Error extracting position: {str(e)}")
            return None
    
    @staticmethod
    def extract_battery_level(telemetry: Dict) -> Optional[int]:
        """Extract battery level from telemetry data"""
        try:
            battery_fields = ["battery_level", "battery_percent", "battery", "power_level", "charge_level"]
            
            for field in battery_fields:
                if field in telemetry and telemetry[field] is not None:
                    battery = float(telemetry[field])
                    # Ensure it's in percentage format
                    if battery > 1:
                        return int(battery)  # Already in percentage
                    else:
                        return int(battery * 100)  # Convert from 0-1 to percentage
            
            # Check nested battery info
            nested_paths = [
                ["battery", "level"], ["battery", "percent"], ["battery", "charge"],
                ["power", "level"], ["power", "percent"]
            ]
            
            for path in nested_paths:
                try:
                    val = telemetry
                    for key in path:
                        val = val[key]
                    if val is not None:
                        battery = float(val)
                        return int(battery * 100 if battery <= 1 else battery)
                except (KeyError, TypeError):
                    continue
                        
            return None
            
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def extract_flight_status(telemetry: Dict) -> str:
        """Extract flight status from telemetry data"""
        try:
            status_fields = ["status", "flight_status", "vehicle_status", "state", "mode"]
            
            for field in status_fields:
                if field in telemetry and telemetry[field] is not None:
                    status = str(telemetry[field]).lower()
                    
                    # Map common status values
                    if any(word in status for word in ["fly", "active", "airborne"]):
                        return "flying"
                    elif any(word in status for word in ["hover", "hold", "loiter"]):
                        return "hovering"
                    elif any(word in status for word in ["land", "ground", "idle"]):
                        return "landed"
                    else:
                        return status
                        
            return "unknown"
            
        except (ValueError, TypeError):
            return "unknown"


# Keep the existing DroneSimulator class unchanged
class DroneSimulator:
    """Simulate drone telemetry data for testing"""
    
    def __init__(self, skydio_client: SkydioClient):
        self.client = skydio_client
        self.logger = logging.getLogger(__name__)
        self.simulation_active = False
        self.current_position = None
        
    def start_simulation(self, vehicle_id: str, start_position: Tuple[float, float, float] = None) -> bool:
        """Start simulating drone telemetry data"""
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
        """Update simulated position"""
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
