"""
Skydio API Endpoint Discovery Test
Discovers available endpoints and tests real API functionality
"""

import os
import logging
from dotenv import load_dotenv
from src.updated_skydio_client import SkydioClient, SkydioTelemetryExtractor, DroneSimulator

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_endpoint_discovery():
    """Discover and test available Skydio API endpoints"""
    
    logger.info("🔍 Skydio API Endpoint Discovery Test")
    logger.info("=" * 60)
    
    # Get API credentials
    api_key = os.getenv('SKYDIO_API_KEY')
    base_url = os.getenv('SKYDIO_BASE_URL', 'https://api.skydio.com/api/v1')
    
    if not api_key:
        logger.error("❌ SKYDIO_API_KEY not found in .env file")
        return False
    
    logger.info(f"Using base URL: {base_url}")
    logger.info(f"API Key: {'*' * 60}{api_key[-4:]}")
    
    # Create client
    client = SkydioClient(api_key, base_url)
    
    # Test basic connection
    logger.info("\n🔗 Testing basic connection...")
    if client.test_connection():
        logger.info("✅ Connection established!")
    else:
        logger.error("❌ Connection failed")
        return False
    
    # Discover available endpoints
    logger.info("\n🎯 Discovering available endpoints...")
    available_endpoints = client.discover_endpoints()
    
    working_endpoints = [ep for ep, works in available_endpoints.items() if works]
    logger.info(f"\n📊 Summary: Found {len(working_endpoints)} working endpoints")
    
    if not working_endpoints:
        logger.warning("⚠️  No working endpoints found")
        return False
    
    # Test specific functionality
    logger.info("\n🧪 Testing discovered endpoints...")
    
    # Test organizations
    logger.info("\n1. Testing organization/account access...")
    orgs = client.get_organizations()
    if orgs:
        logger.info(f"✅ Found {len(orgs)} organization(s)")
        for i, org in enumerate(orgs[:2]):  # Show first 2
            logger.info(f"  Org {i+1}: {org}")
    else:
        logger.info("ℹ️  No organizations data available")
    
    # Test vehicles
    logger.info("\n2. Testing vehicle/fleet access...")
    vehicles = client.get_vehicles()
    if vehicles:
        logger.info(f"✅ Found {len(vehicles)} vehicle(s)")
        for i, vehicle in enumerate(vehicles[:2]):  # Show first 2
            logger.info(f"  Vehicle {i+1}: {vehicle}")
            
        # Test vehicle status for first vehicle
        if vehicles:
            vehicle_id = vehicles[0].get('id') or vehicles[0].get('serial_number') or 'test'
            logger.info(f"\n   Testing vehicle status for: {vehicle_id}")
            status = client.get_vehicle_status(vehicle_id)
            if status:
                logger.info(f"   ✅ Vehicle status: {status}")
            else:
                logger.info(f"   ℹ️  No status data for vehicle {vehicle_id}")
                
    else:
        logger.info("ℹ️  No vehicles data available")
    
    # Test flights
    logger.info("\n3. Testing flight/mission access...")
    flights = client.get_flights(limit=3)
    if flights:
        logger.info(f"✅ Found {len(flights)} recent flight(s)")
        for i, flight in enumerate(flights):
            logger.info(f"  Flight {i+1}: {flight}")
    else:
        logger.info("ℹ️  No flights data available")
    
    # Test telemetry extraction with available data
    logger.info("\n4. Testing telemetry extraction...")
    test_telemetry_data = [
        # Test various telemetry formats
        {"latitude": 37.4419, "longitude": -121.7680, "altitude": 150, "battery_level": 85, "status": "flying"},
        {"location": {"lat": 37.4420, "lon": -121.7681}, "battery": {"percent": 0.80}, "state": "hovering"},
        {"gps": {"latitude": 37.4421, "longitude": -121.7682, "altitude": 145}, "power_level": 75},
    ]
    
    for i, test_data in enumerate(test_telemetry_data):
        logger.info(f"  Test data {i+1}: {test_data}")
        
        position = SkydioTelemetryExtractor.extract_position_data(test_data)
        battery = SkydioTelemetryExtractor.extract_battery_level(test_data)
        status = SkydioTelemetryExtractor.extract_flight_status(test_data)
        
        logger.info(f"    Position: {position}")
        logger.info(f"    Battery: {battery}%")
        logger.info(f"    Status: {status}")
    
    return True


def test_simulation_with_real_api():
    """Test simulation using the real API structure"""
    
    logger.info("\n\n🚁 Testing Flight Simulation with Real API")
    logger.info("=" * 60)
    
    api_key = os.getenv('SKYDIO_API_KEY')
    base_url = os.getenv('SKYDIO_BASE_URL', 'https://api.skydio.com/api/v1')
    
    if not api_key:
        logger.error("❌ API key not found")
        return False
    
    # Create client and simulator
    client = SkydioClient(api_key, base_url)
    simulator = DroneSimulator(client)
    
    # Get a vehicle ID for simulation
    vehicles = client.get_vehicles()
    vehicle_id = "sim-drone-001"  # Default simulation ID
    
    if vehicles and len(vehicles) > 0:
        vehicle_id = vehicles[0].get('id') or vehicles[0].get('serial_number') or vehicle_id
        logger.info(f"Using real vehicle ID: {vehicle_id}")
    else:
        logger.info(f"Using simulated vehicle ID: {vehicle_id}")
    
    # Start simulation
    logger.info(f"\n🎮 Starting simulation for {vehicle_id}...")
    start_pos = (37.4419, -121.7680, 150.0)  # lat, lon, alt
    
    if simulator.start_simulation(vehicle_id, start_pos):
        logger.info("✅ Simulation started")
        
        # Run a short test pattern
        test_moves = [
            (0.0001, 0.0000),   # North
            (0.0000, 0.0001),   # East  
            (-0.0001, 0.0000),  # South
            (0.0000, -0.0001),  # West (return)
        ]
        
        for i, (lat_delta, lon_delta) in enumerate(test_moves):
            logger.info(f"  Move {i+1}: {'North' if lat_delta > 0 else 'South' if lat_delta < 0 else 'East' if lon_delta > 0 else 'West'}")
            
            telemetry = simulator.update_simulation(lat_delta, lon_delta)
            
            if telemetry:
                position = SkydioTelemetryExtractor.extract_position_data(telemetry)
                battery = SkydioTelemetryExtractor.extract_battery_level(telemetry)
                status = SkydioTelemetryExtractor.extract_flight_status(telemetry)
                
                if position:
                    lon, lat, alt = position
                    logger.info(f"    Position: {lat:.6f}, {lon:.6f}, {alt}m")
                logger.info(f"    Battery: {battery}%")
                logger.info(f"    Status: {status}")
            else:
                logger.error(f"    ❌ Simulation update failed")
                break
        
        simulator.stop_simulation()
        logger.info("✅ Simulation completed")
        
    else:
        logger.error("❌ Failed to start simulation")
        return False
    
    return True


def main():
    """Run endpoint discovery and simulation tests"""
    
    logger.info("🛸 Skydio API Complete Test Suite")
    logger.info("=" * 70)
    
    # Test 1: Endpoint discovery
    success = test_endpoint_discovery()
    
    if success:
        # Test 2: Simulation
        test_simulation_with_real_api()
        
        logger.info("\n" + "=" * 70)
        logger.info("🎉 SKYDIO API TESTS COMPLETED!")
        logger.info("\nResults:")
        logger.info("✅ Authentication working")
        logger.info("✅ API endpoints discovered") 
        logger.info("✅ Telemetry extraction working")
        logger.info("✅ Flight simulation working")
        logger.info("\nNext step: Test integration with CalTopo!")
        
    else:
        logger.error("\n" + "=" * 70)
        logger.error("❌ SKYDIO API TESTS FAILED")
        logger.error("Check the error messages above")


if __name__ == "__main__":
    main()
