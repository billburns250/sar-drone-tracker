"""
Simple SAR Drone Tracker - Direct approach without complex async structure
 v1.0 - inital release
"""

import os
import asyncio
import websockets
import json
import requests
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class SimpleDroneTracker:
    def __init__(self):
        self.api_token = os.getenv('API_TOKEN')
        self.caltopo_connect_key = os.getenv('CALTOPO_CONNECT_KEY')
        self.drone_serials = [s.strip() for s in os.getenv('DRONE_SERIALS', '').split(',') if s.strip()]
        self.debug_enabled = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes', 'on')
        self.poll_interval = int(os.getenv('POLL_INTERVAL_SECONDS', '10'))
        
        # Set up logging
        self._setup_logging()
        
        if not all([self.api_token, self.caltopo_connect_key, self.drone_serials]):
            raise ValueError("Missing required environment variables")
    
    def _setup_logging(self):
        """Set up file and console logging"""
        # Create logs directory if it doesn't exist
        os.makedirs('./logs', exist_ok=True)
        
        # Create timestamp for log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'./logs/sar_tracker_{timestamp}.log'
        
        # Set logging level based on debug setting
        log_level = logging.DEBUG if self.debug_enabled else logging.INFO
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()  # Still show on console
            ]
        )
        
        self.logger = logging.getLogger('SARTracker')
        self.logger.info(f"Logging to: {log_file}")
    
    def _debug_print(self, message):
        """Print debug message only if debug is enabled"""
        if self.debug_enabled:
            print(message)
            self.logger.debug(message)
    
    def _log_info(self, message):
        """Log and print info message"""
        print(message)
        self.logger.info(message)
    
    def _generate_device_id(self, serial: str) -> str:
        """Generate CalTopo device ID from drone serial number"""
        last_four = serial[-4:] if len(serial) >= 4 else serial
        return f"{self.caltopo_connect_key}-{last_four}"
    
    def _update_caltopo_position(self, device_id: str, latitude: float, longitude: float, altitude=None) -> bool:
        """Update position in CalTopo Connect tracking - CORRECT FORMAT"""
        try:
            # Extract just the device identifier (last 4 digits) from full device_id
            device_identifier = device_id.split('-')[-1]  # "sccssar_uas-ocd7" -> "ocd7"
            
            params = {
                "id": device_identifier,  # Just "ocd7", not "sccssar_uas-ocd7"
                "lat": latitude,
                "lng": longitude
            }
            
            if altitude is not None:
                params["alt"] = altitude
                
            # Connect key in URL path, device ID in query parameter
            url = f"https://caltopo.com/api/v1/position/report/{self.caltopo_connect_key}"
            
            self._debug_print(f"CalTopo: {url}?{requests.compat.urlencode(params)}")
            
            response = requests.get(url, params=params, timeout=10)
            
            self._debug_print(f"   Status: {response.status_code} | Response: {response.text[:100]}")
            self.logger.debug(f"CalTopo update: {response.status_code} for {device_id}")
            
            if response.status_code == 200:
                return True
            else:
                self._debug_print(f"   CalTopo failed: HTTP {response.status_code}")
                self.logger.warning(f"CalTopo update failed: HTTP {response.status_code} for {device_id}")
                return False
                
        except Exception as e:
            self._debug_print(f"   CalTopo error: {e}")
            self.logger.error(f"CalTopo error for {device_id}: {e}")
            return False
    
    def _check_drone_status(self, serial: str):
        """Check current status of a drone"""
        try:
            headers = {"Accept": "application/json", "Authorization": f"ApiToken {self.api_token}"}
            response = requests.get("https://api.skydio.com/api/v0/vehicles", headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status_code") == 200:
                    vehicles = data.get("data", {}).get("vehicles", [])
                    for vehicle in vehicles:
                        if vehicle.get("vehicle_serial") == serial:
                            return vehicle
            return None
        except Exception as e:
            self.logger.error(f"Error checking drone status for {serial}: {e}")
            return None

async def track_single_drone(tracker, serial):
    """Track a single drone using the proven working pattern"""
    
    device_id = tracker._generate_device_id(serial)
    url = f"wss://stream.skydio.com/data/{serial}"
    
    tracker._log_info(f"Starting tracking for Drone ID [{serial}] -> CalTopo Object [{device_id}]")
    
    # Check drone status first
    status = tracker._check_drone_status(serial)
    if status:
        name = status.get('name', 'Unknown')
        flight_status = status.get('flight_status', 'Unknown')
        is_online = status.get('is_online', False)
        
        # Extract battery percentage
        battery_info = status.get('battery_status', {})
        battery_pct = battery_info.get('percentage', 0) * 100 if battery_info.get('percentage') else 0
        
        # Extract attachments/sensor packages
        attachments = []
        if 'sensor_package' in status:
            sensor_pkg = status['sensor_package']
            pkg_type = sensor_pkg.get('sensor_package_type', 'Unknown')
            attachments.append(pkg_type)
        
        # Check for other attachment types that might be in the vehicle data
        for key in status.keys():
            if 'attachment' in key.lower() and key != 'sensor_package':
                attachments.append(str(status[key]))
        
        attachments_str = ', '.join(attachments) if attachments else 'None'
        
        tracker._log_info(f"Found {serial}: {name} | Flight: {flight_status} | Battery: {battery_pct:.1f}% | Attachments: {attachments_str} | Online: {is_online}")
    else:
        tracker._log_info(f"Could not find drone {serial}")
        return
    
    # Connect to WebSocket using exact pattern from working test
    headers = {"Authorization": f"ApiToken {tracker.api_token}"}
    
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            tracker._log_info(f"Connecting to {url}...")
            
            async with websockets.connect(url, additional_headers=headers) as websocket:
                tracker._log_info(f"Connected to {serial}")
                
                message_count = 0
                start_time = time.time()
                first_position_logged = False
                last_update_time = 0
                
                # Use exact same message receiving pattern as working test
                async for message in websocket:
                    try:
                        message_count += 1
                        current_time = time.time()
                        
                        # Parse telemetry
                        data = json.loads(message)
                        msg_type = data.get('type', 'unknown')
                        
                        # Extract GPS
                        lat = data.get('lat')
                        lon = data.get('lon')
                        
                        if lat is not None and lon is not None:
                            # Rate limiting: only update CalTopo every poll_interval seconds
                            if current_time - last_update_time >= tracker.poll_interval:
                                latitude = float(lat)
                                longitude = float(lon)
                                alt_msl = data.get('alt_msl')
                                altitude = float(alt_msl) if alt_msl else None
                                
                                # Show first CalTopo URL for reference
                                if not first_position_logged:
                                    device_identifier = device_id.split('-')[-1]
                                    params = {"id": device_identifier, "lat": latitude, "lng": longitude}
                                    if altitude:
                                        params["alt"] = altitude
                                    example_url = f"https://caltopo.com/api/v1/position/report/{tracker.caltopo_connect_key}?{requests.compat.urlencode(params)}"
                                    tracker._log_info(f"Posting CalTopo Updates As: {example_url}")
                                    first_position_logged = True
                                
                                # Update CalTopo
                                success = tracker._update_caltopo_position(device_id, latitude, longitude, altitude)
                                
                                # Display update
                                battery = data.get('battery', 0)
                                if battery and battery <= 1.0:
                                    battery *= 100
                                speed = data.get('speed', 0)
                                sats = data.get('gps_satellites_used', 0)
                                
                                status_icon = "📍" if success else "❌"
                                alt_str = f", alt={altitude:.1f}m" if altitude else ""
                                
                                update_msg = f"{status_icon} {device_id}: {latitude:.6f}, {longitude:.6f}{alt_str} | Batt: {battery:.1f}% | Speed: {speed:.1f}m/s | Sats: {sats}"
                                tracker._log_info(update_msg)
                                
                                if not success:
                                    tracker._log_info(f"   CalTopo update failed")
                                
                                last_update_time = current_time
                            else:
                                # Log telemetry received but not processed (debug only)
                                tracker._debug_print(f"Telemetry received (waiting for poll interval): {message_count}")
                        else:
                            tracker._debug_print(f"{device_id}: {msg_type} message #{message_count} (no GPS)")
                            
                    except json.JSONDecodeError:
                        tracker._debug_print(f"Invalid JSON from {serial}")
                        tracker.logger.warning(f"Invalid JSON received from {serial}")
                    except Exception as e:
                        tracker._debug_print(f"Error processing message: {e}")
                        tracker.logger.error(f"Error processing message from {serial}: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            tracker._log_info(f"Connection closed for {serial}")
            retry_count += 1
        except Exception as e:
            tracker._log_info(f"Connection error for {serial}: {e}")
            retry_count += 1
            
        if retry_count < max_retries:
            wait_time = 2 ** retry_count
            tracker._log_info(f"Retrying {serial} in {wait_time}s...")
            await asyncio.sleep(wait_time)
    
    tracker._log_info(f"Max retries exceeded for {serial}")

async def main():
    """Main tracking function"""
    
    try:
        tracker = SimpleDroneTracker()
        
        tracker._log_info("SAR Drone Tracker")
        tracker._log_info(f"Tracking: {tracker.drone_serials}")
        tracker._log_info(f"Call Signs: {[tracker._generate_device_id(s) for s in tracker.drone_serials]}")
        tracker._log_info(f"Poll Interval: {tracker.poll_interval} seconds")
        tracker._log_info(f"Debug Mode: {'Enabled' if tracker.debug_enabled else 'Disabled'}")
        tracker._log_info("=" * 60)
        
        # Create tasks for each drone
        tasks = []
        for serial in tracker.drone_serials:
            task = asyncio.create_task(track_single_drone(tracker, serial))
            tasks.append(task)
        
        # Run all drone tracking tasks
        await asyncio.gather(*tasks, return_exceptions=True)
        
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("\nRequired environment variables:")
        print("  API_TOKEN=your_skydio_api_token")
        print("  CALTOPO_CONNECT_KEY=your_caltopo_connect_key") 
        print("  DRONE_SERIALS=serial1,serial2,serial3")
        print("Optional:")
        print("  DEBUG=true  # Enable debug logging")
        print("  POLL_INTERVAL_SECONDS=10  # How often to update CalTopo")
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
