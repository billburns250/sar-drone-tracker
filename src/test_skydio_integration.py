"""
Test script for Skydio Flight Simulator integration
Tests API connection, vehicle discovery, and telemetry data extraction
"""

import os
import time
import logging
from dotenv import load_dotenv
from src.skydio_client import SkydioClient, DroneSimulator, SkydioTelemetryExtractor

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_skydio_connection():
    """Test basic Skydio API connection"""
    logger.info("Testing Skydio API connection...")
    
    api_token = os.getenv('SKYDIO_API_KEY')
    if not api_token:
        logger.error("❌ SKYDIO_API_KEY not found in .env file")
        return False
    
    try:
        client = SkydioClient(api_token)
        
        # Test connection
        if client.test_connection():
            logger.info("✅ Successfully connected to Skydio API")
            return client
        else:
            logger.error("❌ Failed to connect to Skydio API")
            return False
            
    except Exception as e:
        logger.error(f"❌ Skydio connection test failed: {str(e)}")
        return False


def test_vehicle_discovery(client):
    """Test vehicle discovery and information retrieval"""
    logger.info("Testing vehicle discovery...")
    
    try:
        # Get list of vehicles
        vehicles = client.get_vehicles()
        
        if vehicles is None:
            logger.error("❌ Failed to retrieve vehicles list")
            return None
            
        logger.info(f"✅ Found {len(vehicles)} vehicle(s) in fleet")
        
        # Display vehicle information
        for i, vehicle in enumerate(vehicles):
            logger.info(f"  Vehicle {i+1}:")
            logger.info(f"    ID: {vehicle.get('id', 'Unknown')}")
            logger.info(f"    Serial: {vehicle.get('serial_number', 'Unknown')}")
            logger.info(f"    Model: {vehicle.get('model', 'Unknown')}")
            logger.info(f"    Status: {vehicle.get('status', 'Unknown')}")
            
        # Return the first vehicle for testing
        return vehicles[0] if vehicles else None
        
    except Exception as e:
        logger.error(f"❌ Vehicle discovery failed: {str(e)}")
        return None


def test_flight_history(client, vehicle_id):
    """Test retrieving flight history"""
    logger.info(f"Testing flight history for vehicle {vehicle_id}...")
    
    try:
        flights = client.get_flights(vehicle_id=vehicle_id, limit=5)
        
        if flights is None:
            logger.error("❌ Failed to retrieve flight history")
            return None
            
        logger.info(f"✅ Found {len(flights)} recent flight(s)")
        
        # Display flight information
        for i, flight in enumerate(flights):
            logger.info(f"  Flight {i+1}:")
            logger.info(f"    ID: {flight.get('id', 'Unknown')}")
            logger.info(f"    Date: {flight.get('start_time', 'Unknown')}")
            logger.info(f"    Duration: {flight.get('duration', 'Unknown')}")
            logger.info(f"    Status: {flight.get('status', 'Unknown')}")
            
        return flights[0] if flights else None
        
    except Exception as e:
        logger.error(f"❌ Flight history test failed: {str(e)}")
        return None


def test_telemetry_extraction(client, flight_id):
    """Test telemetry data extraction"""
    logger.info(f"Testing telemetry extraction for flight {flight_id}...")
    
    try:
        telemetry_data = client.get_flight_telemetry(flight_id)
        
        if telemetry_data is None:
            logger.error("❌ Failed to retrieve telemetry data")
            return False
            
        logger.info(f"✅ Retrieved {len(telemetry_data)} telemetry points")
        
        if len(telemetry_data) > 0:
            # Test telemetry extraction on first few points
            logger.info("Testing telemetry data extraction...")
            
            for i, point in enumerate(telemetry_data[:3]):  # Test first 3 points
                logger.info(f"  Telemetry Point {i+1}:")
                
                # Extract position
                position = SkydioTelemetryExtractor.extract_position_data(point)
                if position:
                    lon, lat, alt = position
                    logger.info(f"    Position: {lat:.6f}, {lon:.6f}")
                    if alt:
                        logger.info(f"    Altitude: {alt:.1f}m")
                else:
                    logger.warning(f"    Position: Not available")
                    logger.debug(f"    Raw data: {point}")
                
                # Extract battery
                battery = SkydioTelemetryExtractor.extract_battery_level(point)
                if battery is not None:
                    logger.info(f"    Battery: {battery}%")
                else:
                    logger.info(f"    Battery: Not available")
                
                # Extract status
                status = SkydioTelemetryExtractor.extract_flight_status(point)
                logger.info(f"    Status: {status}")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Telemetry extraction test failed: {str(e)}")
        return False


def test_flight_simulator(client):
    """Test flight simulator functionality"""
    logger.info("Testing Flight Simulator functionality...")
    
    try:
        # Get a vehicle ID for simulation
        vehicles = client.get_vehicles()
        if not vehicles:
            logger.error("❌ No vehicles available for simulation")
            return False
            
        vehicle_id = vehicles[0].get('id') or vehicles[0].get('serial_number')
        if not vehicle_id:
            logger.error("❌ Could not determine vehicle ID for simulation")
            return False
            
        logger.info(f"Using vehicle {vehicle_id} for simulation")
        
        # Create simulator
        simulator = DroneSimulator(client)
        
        # Start simulation with SAR-appropriate coordinates
        # (Replace with coordinates relevant to your SAR area)
        start_lat, start_lon, start_alt = 37.4419, -121.7680, 150.0
        
        if simulator.start_simulation(vehicle_id, (start_lat, start_lon, start_alt)):
            logger.info("✅ Flight simulation started")
            
            # Simulate a search pattern
            logger.info("🚁 Simulating SAR search pattern...")
            
            search_pattern = [
                (0.0001, 0.0000),   # North
                (0.0000, 0.0001),   # East
                (0.0001, 0.0000),   # North
                (0.0000, 0.0001),   # East
                (-0.0001, 0.0000),  # South
                (0.0000, 0.0001),   # East
                (-0.0001, 0.0000),  # South
                (0.0000, -0.0003),  # West (return)
            ]
            
            for i, (lat_delta, lon_delta) in enumerate(search_pattern):
                logger.info(f"  Movement {i+1}/{len(search_pattern)}")
                
                # Update simulation
                telemetry = simulator.update_simulation(lat_delta, lon_delta)
                
                if telemetry:
                    logger.info(f"    Position: {telemetry['latitude']:.6f}, {telemetry['longitude']:.6f}")
                    logger.info(f"    Altitude: {telemetry['altitude']:.1f}m")
                    logger.info(f"    Battery: {telemetry['battery_level']:.1f}%")
                    logger.info(f"    Status: {telemetry['status']}")
                else:
                    logger.error("❌ Failed to get simulated telemetry")
                    break
                    
                # Small delay to simulate real-time
                time.sleep(1)
                
            # Stop simulation
            simulator.stop_simulation()
            logger.info("✅ Flight simulation completed")
            return True
            
        else:
            logger.error("❌ Failed to start flight simulation")
            return False
            
    except Exception as e:
        logger.error(f"❌ Flight simulator test failed: {str(e)}")
        return False


def test_live_telemetry(client):
    """Test live telemetry retrieval (if available)"""
    logger.info("Testing live telemetry access...")
    
    try:
        vehicles = client.get_vehicles()
        if not vehicles:
            logger.warning("⚠️  No vehicles available for live telemetry test")
            return True  # Not a failure, just no active flights
            
        for vehicle in vehicles:
            vehicle_id = vehicle.get('id') or vehicle.get('serial_number')
            logger.info(f"Checking live telemetry for vehicle {vehicle_id}...")
            
            live_data = client.get_live_telemetry(vehicle_id)
            
            if live_data:
                logger.info("✅ Live telemetry data available:")
                
                position = SkydioTelemetryExtractor.extract_position_data(live_data)
                if position:
                    lon, lat, alt = position
                    logger.info(f"    Current Position: {lat:.6f}, {lon:.6f}")
                    if alt:
                        logger.info(f"    Current Altitude: {alt:.1f}m")
                        
                battery = SkydioTelemetryExtractor.extract_battery_level(live_data)
                if battery is not None:
                    logger.info(f"    Current Battery: {battery}%")
                    
                status = SkydioTelemetryExtractor.extract_flight_status(live_data)
                logger.info(f"    Current Status: {status}")
                
                return True
            else:
                logger.info(f"    No live telemetry available (vehicle may not be active)")
                
        logger.info("✅ Live telemetry test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Live telemetry test failed: {str(e)}")
        return False


def main():
    """Run all Skydio API tests"""
    logger.info("🛸 Starting Skydio Flight Simulator Integration Tests")
    logger.info("=" * 60)
    
    # Test 1: Basic connection
    client = test_skydio_connection()
    if not client:
        logger.error("❌ Basic connection failed. Check your API token.")
        return
    
    # Test 2: Vehicle discovery
    vehicle = test_vehicle_discovery(client)
    if not vehicle:
        logger.error("❌ Vehicle discovery failed.")
        return
        
    vehicle_id = vehicle.get('id') or vehicle.get('serial_number')
    
    # Test 3: Flight history
    flight = test_flight_history(client, vehicle_id)
    if flight:
        # Test 4: Telemetry extraction
        flight_id = flight.get('id')
        if flight_id:
            test_telemetry_extraction(client, flight_id)
    
    # Test 5: Live telemetry
    test_live_telemetry(client)
    
    # Test 6: Flight simulator
    test_flight_simulator(client)
    
    logger.info("=" * 60)
    logger.info("🎉 Skydio API tests completed!")
    logger.info("\nNext steps:")
    logger.info("1. If all tests passed, you're ready to integrate with CalTopo")
    logger.info("2. If some tests failed, check the Skydio API documentation")
    logger.info("3. Test the full integration with both Skydio and CalTopo")


if __name__ == "__main__":
    main()
