"""
SAR Drone Tracker - Clean version with proper logging separation
(c) 2025 SaferFuturesByDesign - Bill Burns
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
        
        # Get logging levels from environment
        self.console_log_level = self._parse_log_level(os.getenv('CONSOLE_LOG_LEVEL', 'INFO'))
        self.file_log_level = self._parse_log_level(os.getenv('FILE_LOG_LEVEL', 'INFO'))
        
        # Set up logging
        self._setup_logging()
        
        if not all([self.api_token, self.caltopo_connect_key, self.drone_serials]):
            raise ValueError("Missing required environment variables")
    
    def _parse_log_level(self, level_str):
        """Parse log level string to logging constant"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(level_str.upper(), logging.INFO)
    
    def _setup_logging(self):
        """Set up CLEAN logging with no duplicates"""
        # Create logs directory
        os.makedirs('./logs', exist_ok=True)
        
        # Create timestamp for log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'./logs/sar_tracker_{timestamp}.log'
        
        # Completely disable all existing loggers
        logging.getLogger().handlers = []
        logging.getLogger().setLevel(logging.CRITICAL + 1)  # Disable root logger
        
        # Create our specific logger
        self.logger = logging.getLogger('SARTracker')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []  # Ensure clean start
        self.logger.propagate = False  # Never propagate to parent loggers
        
        # File handler - always created
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(self.file_log_level)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler - only if needed
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.console_log_level)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Store file path
        self.log_file_path = log_file
        
        # Initial log messages
        self.logger.warning(f"Logging to: {log_file}")
        self.logger.warning(f"Console log level: {logging.getLevelName(self.console_log_level)}")
        self.logger.warning(f"File log level: {logging.getLevelName(self.file_log_level)}")
    
    def _generate_device_id(self, serial: str) -> str:
        """Generate CalTopo device ID from drone serial number"""
        last_four = serial[-4:] if len(serial) >= 4 else serial
        return f"{self.caltopo_connect_key}-{last_four}"
    
    def _make_console_safe(self, message):
        """Convert Unicode characters to safe alternatives only on Windows"""
        import platform
        
        # Only apply ASCII conversion on Windows
        if platform.system() != 'Windows':
            return message
        
        # Replace Unicode emoji with ASCII alternatives for Windows
        replacements = {
            '📍': '[GPS]',      '✅': '[OK]',       '❌': '[ERR]',
            '🔗': '[CONN]',     '🔧': '[DBG]',      '⚠️': '[WARN]',
            '🚁': '[DRONE]',    '📡': '[TRACK]',    '🗂️': '[DEV]',
            '🔌': '[DISC]',     '⏳': '[WAIT]',     '💔': '[FAIL]',
        }
        
        safe_message = message
        for unicode_char, ascii_replacement in replacements.items():
            safe_message = safe_message.replace(unicode_char, ascii_replacement)
        
        return safe_message
    
    def _update_caltopo_position(self, device_id: str, latitude: float, longitude: float, altitude=None) -> bool:
        """Update position in CalTopo Connect tracking"""
        try:
            device_identifier = device_id.split('-')[-1]
            
            params = {
                "id": device_identifier,
                "lat": latitude,
                "lng": longitude
            }
            
            if altitude is not None:
                params["alt"] = altitude
                
            url = f"https://caltopo.com/api/v1/position/report/{self.caltopo_connect_key}"
            
            self.logger.debug(f"CalTopo: {url}?{requests.compat.urlencode(params)}")
            
            response = requests.get(url, params=params, timeout=10)
            
            self.logger.debug(f"CalTopo Status: {response.status_code} | Response: {response.text[:100]}")
            
            if response.status_code == 200:
                return True
            else:
                self.logger.warning(f"CalTopo update failed: HTTP {response.status_code} for {device_id}")
                return False
                
        except Exception as e:
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
    """Track a single drone"""
    
    device_id = tracker._generate_device_id(serial)
    url = f"wss://stream.skydio.com/data/{serial}"
    
    tracker.logger.warning(f"Starting tracking for Drone ID [{serial}] -> CalTopo Object [{device_id}]")
    
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
        
        for key in status.keys():
            if 'attachment' in key.lower() and key != 'sensor_package':
                attachments.append(str(status[key]))
        
        attachments_str = ', '.join(attachments) if attachments else 'None'
        
        tracker.logger.warning(f"Found {serial}: {name} | Flight: {flight_status} | Battery: {battery_pct:.1f}% | Attachments: {attachments_str} | Online: {is_online}")
    else:
        tracker.logger.info(f"Could not find drone {serial}")
        return
    
    # Connect to WebSocket
    headers = {"Authorization": f"ApiToken {tracker.api_token}"}
    
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            tracker.logger.warning(f"Connecting to {url}...")
            
            async with websockets.connect(url, additional_headers=headers) as websocket:
                tracker.logger.warning(f"Connected to {serial}")
                
                message_count = 0
                first_position_logged = False
                last_update_time = 0
                
                async for message in websocket:
                    try:
                        message_count += 1
                        current_time = time.time()
                        
                        # Parse telemetry
                        data = json.loads(message)
                        
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
                                    tracker.logger.warning(f"Posting CalTopo Updates As: {example_url}")
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
                                tracker.logger.info(update_msg)
                                
                                if not success:
                                    tracker.logger.warning(f"CalTopo update failed for {device_id}")
                                
                                last_update_time = current_time
                            else:
                                # Log telemetry received but not processed (debug only)
                                tracker.logger.debug(f"Telemetry received (waiting for poll interval): {message_count}")
                        else:
                            tracker.logger.debug(f"{device_id}: {data.get('type', 'unknown')} message #{message_count} (no GPS)")
                            
                    except json.JSONDecodeError:
                        tracker.logger.warning(f"Invalid JSON received from {serial}")
                    except Exception as e:
                        tracker.logger.error(f"Error processing message from {serial}: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            tracker.logger.info(f"Connection closed for {serial}")
            retry_count += 1
        except Exception as e:
            tracker.logger.error(f"Connection error for {serial}: {e}")
            retry_count += 1
            
        if retry_count < max_retries:
            wait_time = 2 ** retry_count
            tracker.logger.info(f"Retrying {serial} in {wait_time}s...")
            await asyncio.sleep(wait_time)
    
    tracker.logger.error(f"Max retries exceeded for {serial}")

async def main():
    """Main tracking function"""
    
    try:
        tracker = SimpleDroneTracker()
        
        tracker.logger.warning("SAR Drone Tracker")
        tracker.logger.warning(f"Tracking: {tracker.drone_serials}")
        tracker.logger.warning(f"Device IDs: {[tracker._generate_device_id(s) for s in tracker.drone_serials]}")
        tracker.logger.warning(f"Poll Interval: {tracker.poll_interval} seconds")
        tracker.logger.warning(f"Debug Mode: {'Enabled' if tracker.debug_enabled else 'Disabled'}")
        tracker.logger.warning("=" * 60)
        
        # Create tasks for each drone
        tasks = []
        for serial in tracker.drone_serials:
            task = asyncio.create_task(track_single_drone(tracker, serial))
            tasks.append(task)
        
        # Run all drone tracking tasks
        await asyncio.gather(*tasks, return_exceptions=True)
        
    except ValueError as e:
        # Only print configuration errors directly (no logging setup yet)
        print(f"Configuration Error: {e}")
        print("\nRequired environment variables:")
        print("  API_TOKEN=your_skydio_api_token")
        print("  CALTOPO_CONNECT_KEY=your_caltopo_connect_key") 
        print("  DRONE_SERIALS=serial1,serial2,serial3")
        print("Optional:")
        print("  DEBUG=true")
        print("  POLL_INTERVAL_SECONDS=10")
        print("  CONSOLE_LOG_LEVEL=ERROR")
        print("  FILE_LOG_LEVEL=INFO")
    except KeyboardInterrupt:
        try:
            if 'tracker' in locals():
                tracker.logger.info("Stopped by user")
            else:
                print("\nStopped by user")
        except:
            print("\nStopped by user")
    except Exception as e:
        try:
            if 'tracker' in locals():
                tracker.logger.error(f"Unexpected error: {e}")
            else:
                print(f"Error: {e}")
        except:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
