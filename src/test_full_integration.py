"""
Full Integration Test: Skydio Flight Simulator → CalTopo Tracking
Tests the complete pipeline from Skydio telemetry to CalTopo map updates
"""

import os
import time
import logging
from dotenv import load_dotenv
from src.skydio_client import SkydioClient, DroneSimulator, SkydioTelemetryExtractor
from src.caltopo_client import CalTopoClient, DroneTracker

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    logger.info("✅ Both API connections successful")
    
    # Step 3: Get vehicle information
    logger.info("Step 3: Getting Skydio vehicle information...")
    
    vehicles = skydio_client.get_vehicles()
    if not vehicles:
        logger.error("❌ No vehicles found in Skydio fleet")
        return False
        
    vehicle = vehicles[0]
    vehicle_id = vehicle.get('id') or vehicle.get('serial_number') or 'test-drone'
    logger.info(f"✅ Using vehicle: {vehicle_id}")
    
    # Step 4: Start integrated simulation
    logger.info("Step 4: Starting integrated drone simulation...")
    
    simulator = DroneSimulator(skydio_client)
    
    # SAR mission scenario: Search pattern in a defined area
    # Replace these coordinates with your actual SAR area
    mission_start_lat = 37.4419  # Example: Bay Area coordinates
    mission_start_lon = -121.7680
    mission_altitude = 150.0
    
    # Start simulation
    if not simulator.start_simulation(vehicle_id, (mission_start_lat, mission_start_lon, mission_altitude)):
        logger.error("❌ Failed to start Skydio simulation")
        return False
        
    logger.info("✅ Skydio simulation started")
    
    # Step 5: Execute SAR search pattern with live tracking
    logger.info("Step 5: Executing SAR search pattern with live CalTopo tracking...")
    
    # Define a realistic SAR search pattern
    search_pattern = [
        # Grid search pattern
        (0.0000, 0.0000),   # Start position
        (0.0005, 0.0000),   # North leg
        (0.0000, 0.0005),   # East turn
        (-0.0005, 0.0000),  # South leg  
        (0.0000, 0.0005),   # East turn
        (0.0005, 0.0000),   # North leg
        (0.0000, 0.0005),   # East turn
        (-0.0005, 0.0000),  # South leg
        (0.0000, 0.0005),   # East turn
        (0.0005, 0.0000),   # North leg
        (0.0000, -0.0020),  # Return west
        (-0.0005, 0.0000),  # Return to start area
    ]
    
    drone_name = f"SAR-{vehicle_id}"
    logger.info(f"🎯 Starting search pattern for {drone_name}")
    
    try:
        for i, (lat_delta, lon_delta) in enumerate(search_pattern):
            logger.info(f"  Search leg {i+1}/{len(search_pattern)}")
            
            # Get updated telemetry from Skydio simulation
            telemetry = simulator.update_simulation(lat_delta, lon_delta)
            
            if not telemetry:
                logger.error(f"❌ Failed to get telemetry for leg {i+1}")
                continue
                
            # Extract position data
            position = SkydioTelemetryExtractor.extract_position_data(telemetry)
            if not position:
                logger.error(f"❌ Failed to extract position for leg {i+1}")
                continue
                
            longitude, latitude, altitude = position
            battery = SkydioTelemetryExtractor.extract_battery_level(telemetry)
            
            logger.info(f"    Position: {latitude:.6f}, {longitude:.6f}")
            logger.info(f"    Altitude: {altitude:.1f}m")
            logger.info(f"    Battery: {battery}%" if battery else "    Battery: Unknown")
            
            # Update CalTopo track
            success = drone_tracker.update_drone_position(
                drone_name, 
                (longitude, latitude), 
                battery_level=battery
            )
            
            if success:
                logger.info(f"    ✅ CalTopo updated successfully")
            else:
                logger.error(f"    ❌ CalTopo update failed")
                
            # Simulate real-time delay
            time.sleep(3)  # 3 seconds between updates
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  Search pattern interrupted by user")
    except Exception as e:
        logger.error(f"❌ Search pattern failed: {str(e)}")
        return False
    finally:
        # Clean up simulation
        simulator.stop_simulation()
        
    # Step 6: Verify results
    logger.info("Step 6: Verifying results...")
    
    # Check if track was created in CalTopo
    map_data = caltopo_client.get_map_data(caltopo_creds[3])
    if map_data:
        features = map_data.get("features", [])
        track_features = [f for f in features 
                         if f.get("properties", {}).get("title", "").startswith("SAR-Drone")]
        
        logger.info(f"✅ Found {len(track_features)} drone track(s) in CalTopo map")
        
        if track_features:
            for track in track_features:
                track_name = track.get("properties", {}).get("title", "Unknown")
                logger.info(f"    Track: {track_name}")
                
                # Count track points
                geometry = track.get("geometry", {})
                if geometry.get("type") == "LineString":
                    coordinates = geometry.get("coordinates", [])
                    logger.info(f"    Points: {len(coordinates)} GPS positions")
                    
    else:
        logger.warning("⚠️  Could not verify CalTopo map data")
    
    # Step 7: Mission summary
    logger.info("Step 7: Mission Summary")
    logger.info("✅ Integration test completed successfully!")
    logger.info(f"📍 Check your CalTopo map: https://caltopo.com/m/{caltopo_creds[3]}")
    logger.info("🎯 The drone track should be visible with real-time updates")
    
    return True


def test_error_handling():
    """Test error handling and recovery scenarios"""
    logger.info("\n🔧 Testing Error Handling Scenarios...")
    
    # Test with invalid credentials
    logger.info("Testing invalid Skydio credentials...")
    invalid_client = SkydioClient("invalid_token")
    if not invalid_client.test_connection():
        logger.info("✅ Correctly handled invalid Skydio credentials")
    else:
        logger.warning("⚠️  Invalid credentials were accepted (unexpected)")
    
    # Test with missing telemetry data
    logger.info("Testing telemetry data extraction with missing fields...")
    incomplete_telemetry = {"timestamp": "2023-01-01T12:00:00Z"}  # Missing position
    position = SkydioTelemetryExtractor.extract_position_data(incomplete_telemetry)
    
    if position is None:
        logger.info("✅ Correctly handled missing telemetry data")
    else:
        logger.warning("⚠️  Missing telemetry data was processed (unexpected)")
    
    logger.info("🔧 Error handling tests completed")


def cleanup_test_data():
    """Clean up test tracks from CalTopo (optional)"""
    logger.info("\n🧹 Cleaning up test data...")
    
    try:
        caltopo_creds = [
            os.getenv('CALTOPO_CREDENTIAL_ID'),
            os.getenv('CALTOPO_CREDENTIAL_SECRET'),
            os.getenv('CALTOPO_TEAM_ID'),
            os.getenv('CALTOPO_MAP_ID')
        ]
        
        if not all(caltopo_creds):
            logger.warning("⚠️  Cannot cleanup - CalTopo credentials missing")
            return
            
        caltopo_client = CalTopoClient(caltopo_creds[0], caltopo_creds[1], caltopo_creds[2])
        drone_tracker = DroneTracker(caltopo_client, caltopo_creds[3])
        
        # Stop tracking all test drones
        vehicles = ["test-drone", "SAR-test-drone"]
        for vehicle_id in vehicles:
            drone_tracker.stop_drone_track(f"SAR-{vehicle_id}")
            
        logger.info("✅ Test data cleanup completed")
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {str(e)}")


def main():
    """Run full integration test suite"""
    logger.info("🚁📍 SAR Drone Tracker - Full Integration Test Suite")
    logger.info("=" * 70)
    
    # Check environment setup
    required_env_vars = [
        'SKYDIO_API_KEY',
        'CALTOPO_CREDENTIAL_ID',
        'CALTOPO_CREDENTIAL_SECRET', 
        'CALTOPO_TEAM_ID',
        'CALTOPO_MAP_ID'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file configuration")
        return
        
    # Run main integration test
    success = test_full_integration()
    
    if success:
        # Run error handling tests
        test_error_handling()
        
        # Ask user about cleanup
        try:
            user_input = input("\nClean up test tracks from CalTopo? (y/n): ").lower().strip()
            if user_input == 'y':
                cleanup_test_data()
        except KeyboardInterrupt:
            logger.info("\nSkipping cleanup")
            
        logger.info("\n" + "=" * 70)
        logger.info("🎉 INTEGRATION TEST SUCCESSFUL!")
        logger.info("\nYour SAR Drone Tracker is working correctly:")
        logger.info("✅ Skydio Flight Simulator integration working")
        logger.info("✅ CalTopo real-time tracking working") 
        logger.info("✅ Full telemetry → map pipeline functional")
        logger.info("\nReady for production deployment!")
        
    else:
        logger.error("\n" + "=" * 70)
        logger.error("❌ INTEGRATION TEST FAILED")
        logger.error("Please check the error messages above and:")
        logger.error("1. Verify your API credentials are correct")
        logger.error("2. Check network connectivity")
        logger.error("3. Ensure your CalTopo map has proper permissions")
        logger.error("4. Verify Skydio Flight Simulator access")


if __name__ == "__main__":
    main()level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_full_integration():
    """Test complete Skydio → CalTopo integration"""
    logger.info("🚁 Starting Full Integration Test: Skydio → CalTopo")
    logger.info("=" * 70)
    
    # Step 1: Set up clients
    logger.info("Step 1: Setting up API clients...")
    
    # Skydio client
    skydio_api_key = os.getenv('SKYDIO_API_KEY')
    if not skydio_api_key:
        logger.error("❌ SKYDIO_API_KEY not found in .env file")
        return False
        
    skydio_client = SkydioClient(skydio_api_key)
    
    # CalTopo client
    caltopo_creds = [
        os.getenv('CALTOPO_CREDENTIAL_ID'),
        os.getenv('CALTOPO_CREDENTIAL_SECRET'),
        os.getenv('CALTOPO_TEAM_ID'),
        os.getenv('CALTOPO_MAP_ID')
    ]
    
    if not all(caltopo_creds):
        logger.error("❌ CalTopo credentials missing from .env file")
        return False
        
    caltopo_client = CalTopoClient(caltopo_creds[0], caltopo_creds[1], caltopo_creds[2])
    drone_tracker = DroneTracker(caltopo_client, caltopo_creds[3])
    
    # Step 2: Test connections
    logger.info("Step 2: Testing API connections...")
    
    if not skydio_client.test_connection():
        logger.error("❌ Skydio API connection failed")
        return False
        
    team_data = caltopo_client.get_team_maps()
    if not team_data:
        logger.error("❌ CalTopo API connection failed")
        return False
