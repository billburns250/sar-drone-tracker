"""
Simple Skydio Client matching official examples
Uses only API_TOKEN with Bearer authentication
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone


class SkydioClient:
    """
    Simple Skydio client matching official examples
    Uses only API_TOKEN (not API_TOKEN_ID)
    """
    
    def __init__(self, api_token: str, base_url: str = "https://api.skydio.com"):
        """
        Initialize Skydio client with simple authentication
        
        Args:
            api_token: Your Skydio API token
            base_url: Base URL for Skydio Cloud API
        """
        self.api_token = api_token
        self.base_url = base_url.rstrip('/')
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Create session with correct headers (matching official examples)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, 
                     params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated request to Skydio API
        """
        try:
            # Build full URL - try the endpoint exactly as provided first
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            self.logger.debug(f"Making {method} request to {url}")
            
            # Make request
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,  # Use json parameter instead of data
                timeout=30
            )
            
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Handle response
            if response.status_code == 200:
                if response.content:
                    return response.json()
                return {}
            elif response.status_code == 401:
                self.logger.error("Authentication failed - check API token")
                if response.content:
                    try:
                        error_data = response.json()
                        self.logger.error(f"Auth error details: {error_data}")
                    except:
                        self.logger.error(f"Auth error response: {response.text}")
                return None
            elif response.status_code == 404:
                self.logger.debug(f"Endpoint not found: {endpoint}")
                return None
            else:
                self.logger.error(f"Request failed with status {response.status_code}")
                if response.content:
                    try:
                        error_data = response.json()
                        self.logger.error(f"Error details: {error_data}")
                    except:
                        self.logger.error(f"Error response: {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Test API connection by trying different common endpoints"""
        
        # Based on typical REST API patterns, try these endpoints
        test_endpoints = [
            # Most likely endpoints for Skydio
            "api/v1/vehicles",
            "api/v0/vehicles", 
            "vehicles",
            
            # User/account info
            "api/v1/user",
            "api/v0/user",
            "user",
            "me",
            
            # Organization/account
            "api/v1/organizations",
            "api/v0/organizations",
            "organizations",
            
            # Simple health check
            "api/v1/health",
            "health",
            "status",
            
            # Root API
            "api/v1",
            "api/v0",
        ]
        
        for endpoint in test_endpoints:
            try:
                self.logger.debug(f"Testing endpoint: {endpoint}")
                result = self._make_request("GET", endpoint)
                
                if result is not None:
                    self.logger.info(f"✅ Skydio API connection successful via {endpoint}")
                    self.logger.debug(f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'List response'}")
                    return True
                    
            except Exception as e:
                self.logger.debug(f"Endpoint {endpoint} failed: {str(e)}")
                continue
                
        self.logger.error("❌ All test endpoints failed")
        return False
    
    def discover_working_endpoints(self) -> List[str]:
        """Discover which endpoints actually work"""
        
        working_endpoints = []
        
        test_endpoints = [
            "api/v1/vehicles", "api/v0/vehicles", "vehicles",
            "api/v1/flights", "api/v0/flights", "flights", 
            "api/v1/user", "api/v0/user", "user", "me",
            "api/v1/organizations", "api/v0/organizations", "organizations",
            "api/v1/telemetry", "api/v0/telemetry", "telemetry",
            "api/v1/health", "health", "status"
        ]
        
        for endpoint in test_endpoints:
            try:
                result = self._make_request("GET", endpoint)
                if result is not None:
                    working_endpoints.append(endpoint)
                    self.logger.info(f"✅ Working endpoint: {endpoint}")
                    
            except Exception:
                continue
                
        return working_endpoints
    
    def get_vehicles(self) -> Optional[List[Dict]]:
        """Get list of vehicles - try multiple endpoint variations"""
        
        endpoints = ["api/v1/vehicles", "api/v0/vehicles", "vehicles"]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result is not None:
                self.logger.info(f"Got vehicles from endpoint: {endpoint}")
                
                # Handle different response formats
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict):
                    # Try common response wrapper formats
                    for key in ['vehicles', 'data', 'results', 'items']:
                        if key in result and isinstance(result[key], list):
                            return result[key]
                    # If it's a single vehicle wrapped in dict
                    return [result]
                    
        return None
    
    def get_flights(self, vehicle_id: Optional[str] = None, limit: int = 10) -> Optional[List[Dict]]:
        """Get list of flights"""
        
        params = {"limit": limit}
        if vehicle_id:
            params["vehicle_id"] = vehicle_id
            
        endpoints = ["api/v1/flights", "api/v0/flights", "flights"]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint, params=params)
            if result is not None:
                self.logger.info(f"Got flights from endpoint: {endpoint}")
                
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict):
                    for key in ['flights', 'data', 'results', 'items']:
                        if key in result and isinstance(result[key], list):
                            return result[key]
                    return [result]
                    
        return None
    
    def get_vehicle_details(self, vehicle_id: str) -> Optional[Dict]:
        """Get details for a specific vehicle"""
        
        endpoints = [
            f"api/v1/vehicles/{vehicle_id}",
            f"api/v0/vehicles/{vehicle_id}",
            f"vehicles/{vehicle_id}"
        ]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result is not None:
                return result
                
        return None
    
    def get_flight_telemetry(self, flight_id: str) -> Optional[List[Dict]]:
        """Get telemetry for a specific flight"""
        
        endpoints = [
            f"api/v1/flights/{flight_id}/telemetry",
            f"api/v0/flights/{flight_id}/telemetry",
            f"flights/{flight_id}/telemetry"
        ]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result is not None:
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict) and 'telemetry' in result:
                    return result['telemetry']
                elif isinstance(result, dict) and 'data' in result:
                    return result['data']
                    
        return None
    
    def get_live_telemetry(self, vehicle_id: str) -> Optional[Dict]:
        """Get current live telemetry for a vehicle"""
        
        endpoints = [
            f"api/v1/vehicles/{vehicle_id}/telemetry",
            f"api/v0/vehicles/{vehicle_id}/telemetry", 
            f"vehicles/{vehicle_id}/telemetry",
            f"api/v1/vehicles/{vehicle_id}/status",
            f"vehicles/{vehicle_id}/status"
        ]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result is not None:
                return result
                
        return None


# Keep the existing telemetry extractor unchanged
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
            battery_fields = ["battery_level", "battery_percent", "battery", "power_level"]
            
            for field in battery_fields:
                if field in telemetry and telemetry[field] is not None:
                    battery = float(telemetry[field])
                    if battery > 1:
                        return int(battery)  # Already percentage
                    else:
                        return int(battery * 100)  # Convert to percentage
            
            # Check nested
            if "battery" in telemetry and isinstance(telemetry["battery"], dict):
                for subfield in ["level", "percent", "charge"]:
                    if subfield in telemetry["battery"]:
                        val = float(telemetry["battery"][subfield])
                        return int(val * 100 if val <= 1 else val)
                        
            return None
            
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def extract_flight_status(telemetry: Dict) -> str:
        """Extract flight status from telemetry data"""
        try:
            status_fields = ["status", "flight_status", "vehicle_status", "state"]
            
            for field in status_fields:
                if field in telemetry and telemetry[field] is not None:
                    status = str(telemetry[field]).lower()
                    
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
