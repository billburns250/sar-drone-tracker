"""
Corrected Skydio Cloud API Client
Based on official Skydio GitHub examples
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import base64
import hashlib
import hmac
import time


class SkydioClient:
    """
    Corrected Skydio client based on official examples
    Requires both API_TOKEN and API_TOKEN_ID
    """
    
    def __init__(self, api_token: str, api_token_id: str, base_url: str = "https://api.skydio.com"):
        """
        Initialize Skydio client with correct credentials
        
        Args:
            api_token: Your Skydio API token (secret)
            api_token_id: Your Skydio API token ID (public identifier)
            base_url: Base URL for Skydio Cloud API
        """
        self.api_token = api_token
        self.api_token_id = api_token_id
        self.base_url = base_url.rstrip('/')
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Create session with correct headers
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _create_auth_headers(self, method: str, path: str, body: str = '') -> Dict[str, str]:
        """
        Create authentication headers using Skydio's signing method
        Based on official examples pattern
        """
        timestamp = str(int(time.time()))
        
        # Create signature string
        string_to_sign = f"{method}\n{path}\n{timestamp}\n{body}"
        
        # Create HMAC signature
        signature = hmac.new(
            self.api_token.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Encode signature
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return {
            'Authorization': f'Skydio {self.api_token_id}:{signature_b64}',
            'X-Skydio-Timestamp': timestamp
        }
    
    def _make_request(self, method: str, endpoint: str, 
                     params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated request to Skydio API
        """
        try:
            # Build full URL
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            path = f"/{endpoint.lstrip('/')}"
            
            # Prepare body
            body = json.dumps(data) if data else ''
            
            # Create authentication headers
            auth_headers = self._create_auth_headers(method.upper(), path, body)
            
            # Combine headers
            headers = {**self.session.headers, **auth_headers}
            
            self.logger.debug(f"Making {method} request to {url}")
            
            # Make request
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=body if body else None,
                timeout=30
            )
            
            self.logger.debug(f"Response status: {response.status_code}")
            
            # Handle response
            if response.status_code == 200:
                if response.content:
                    return response.json()
                return {}
            elif response.status_code == 401:
                self.logger.error("Authentication failed - check API token and token ID")
                return None
            elif response.status_code == 404:
                self.logger.error(f"Endpoint not found: {endpoint}")
                return None
            else:
                self.logger.error(f"Request failed with status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            # Try a simple endpoint that should work
            result = self._make_request("GET", "api/v0/vehicles")
            
            if result is not None:
                self.logger.info("Skydio API connection successful")
                return True
            else:
                # Try alternative endpoints
                for endpoint in ["api/v1/vehicles", "vehicles", "api/v0/user"]:
                    result = self._make_request("GET", endpoint)
                    if result is not None:
                        self.logger.info(f"Skydio API connection successful via {endpoint}")
                        return True
                        
                self.logger.error("Skydio API connection failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_vehicles(self) -> Optional[List[Dict]]:
        """Get list of vehicles"""
        # Try different possible endpoints
        endpoints = ["api/v0/vehicles", "api/v1/vehicles", "vehicles"]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result is not None:
                # Handle different response formats
                if isinstance(result, list):
                    return result
                elif 'vehicles' in result:
                    return result['vehicles']
                elif 'data' in result:
                    return result['data']
                else:
                    return [result]
                    
        return None
    
    def get_vehicle_details(self, vehicle_id: str) -> Optional[Dict]:
        """Get detailed information about a specific vehicle"""
        endpoints = [
            f"api/v0/vehicles/{vehicle_id}",
            f"api/v1/vehicles/{vehicle_id}",
            f"vehicles/{vehicle_id}"
        ]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result is not None:
                return result
                
        return None
    
    def get_flights(self, vehicle_id: Optional[str] = None, limit: int = 50) -> Optional[List[Dict]]:
        """Get list of flights"""
        params = {"limit": limit}
        if vehicle_id:
            params["vehicle_id"] = vehicle_id
            
        endpoints = ["api/v0/flights", "api/v1/flights", "flights"]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint, params=params)
            if result is not None:
                if isinstance(result, list):
                    return result
                elif 'flights' in result:
                    return result['flights']
                elif 'data' in result:
                    return result['data']
                    
        return None
    
    def get_flight_telemetry(self, flight_id: str) -> Optional[List[Dict]]:
        """Get telemetry data for a flight"""
        endpoints = [
            f"api/v0/flights/{flight_id}/telemetry",
            f"api/v1/flights/{flight_id}/telemetry",
            f"flights/{flight_id}/telemetry"
        ]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result is not None:
                if isinstance(result, list):
                    return result
                elif 'telemetry' in result:
                    return result['telemetry']
                elif 'data' in result:
                    return result['data']
                    
        return None
    
    def get_live_telemetry(self, vehicle_id: str) -> Optional[Dict]:
        """Get live telemetry for a vehicle"""
        endpoints = [
            f"api/v0/vehicles/{vehicle_id}/telemetry",
            f"api/v1/vehicles/{vehicle_id}/telemetry",
            f"vehicles/{vehicle_id}/telemetry",
            f"api/v0/vehicles/{vehicle_id}/status",
            f"vehicles/{vehicle_id}/status"
        ]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result is not None:
                return result
                
        return None


# Keep existing telemetry extractor
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
            
            def get_nested_value(data, paths):
                """Get value from nested dict using multiple possible paths"""
                for path in paths:
                    try:
                        if isinstance(path, str):
                            if path in data and data[path] is not None:
                                return float(data[path])
                        else:  # List of keys for nested access
                            val = data
                            for key in path:
                                val = val[key]
                            if val is not None:
                                return float(val)
                    except (KeyError, TypeError, ValueError):
                        continue
                return None
            
            # Try to extract coordinates
            latitude = get_nested_value(telemetry, lat_fields + [["location", "latitude"], ["position", "lat"], ["gps", "latitude"]])
            longitude = get_nested_value(telemetry, lon_fields + [["location", "longitude"], ["position", "lon"], ["gps", "longitude"]])
            altitude = get_nested_value(telemetry, alt_fields + [["location", "altitude"], ["position", "alt"], ["gps", "altitude"]])
            
            if latitude is not None and longitude is not None:
                return (longitude, latitude, altitude)  # Note: lon, lat order for GeoJSON
            else:
                return None
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Error extracting position: {str(e)}")
            return None
    
    @staticmethod
    def extract_battery_level(telemetry: Dict) -> Optional[int]:
        """Extract battery level from telemetry data"""
        try:
            battery_fields = ["battery_level", "battery_percent", "battery", "power_level", "charge_level"]
            
            def get_nested_value(data, paths):
                for path in paths:
                    try:
                        if isinstance(path, str):
                            if path in data and data[path] is not None:
                                return data[path]
                        else:
                            val = data
                            for key in path:
                                val = val[key]
                            return val
                    except (KeyError, TypeError):
                        continue
                return None
            
            battery_value = get_nested_value(telemetry, battery_fields + [["battery", "level"], ["battery", "percent"], ["power", "level"]])
            
            if battery_value is not None:
                battery = float(battery_value)
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
            
            # Check nested structures
            nested_paths = [["flight", "status"], ["vehicle", "status"], ["state", "flight"]]
            for path in nested_paths:
                try:
                    val = telemetry
                    for key in path:
                        val = val[key]
                    if val is not None:
                        return str(val).lower()
                except (KeyError, TypeError):
                    continue
                        
            return "unknown"
            
        except (ValueError, TypeError):
            return "unknown"
