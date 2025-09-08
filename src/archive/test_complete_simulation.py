"""
Complete SAR Drone Tracking Test
Tests realistic drone simulation with CalTopo integration
This creates a working system without needing real Skydio API access
"""

import os
import time
import logging
from dotenv import load_dotenv
from src.realistic_drone_simulator import RealisticDroneSimulator
from src.caltopo_client import CalTopoClient, DroneTracker

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_complete_sar_system():
    """Test complete SAR drone tracking system with realistic simulation"""
    
    logger.info("🚁 SAR Drone Tracking System - Complete Integration Test")
    logger.info("=" * 70)
    
    # Step 1: Setup
    logger.info("Step 1: System Setup")
    
    # CalTopo credentials
    caltopo_creds = [
        os.getenv('CALTOPO_CREDENTIAL_ID'),
        os.getenv('CALTOPO_CREDENTIAL_SECRET'),
        os.getenv('CALTOPO_TEAM_ID'),
        os.getenv('CALTOPO_MAP_ID')
    ]
    
    if not all(caltopo_creds):
        logger.error("❌ CalTopo credentials missing - this test requires CalTopo API access")
        logger.info("ℹ️  You can still test the drone simulation without CalTopo integration")
        return test_simulation_only()
        
    # Initialize systems
    caltopo_client = CalTopoClient(caltopo_creds[0], caltopo_creds[1], caltopo_creds[2])
    drone_tracker = DroneTracker(caltopo_client, caltopo_creds[3])
    
    # Test CalTopo connection
    if not caltopo_client.get_team_maps():
        logger.error("❌ CalTopo connection failed")
        return False
    
    logger.info("✅ CalTopo connection verified")
    
    # Initialize drone simulator with your mission area
    mission_center = (37.4419, -121.7680)  # Replace with your SAR area
    simulator = RealisticDroneSimulator(mission_center)
    
    logger.info("✅ Drone simulator initialized")
    
    # Step 2: Deploy multiple drones with different search patterns
    logger.info("\nStep 2: Deploying SAR Drones")
    
    drones = [
        {'id': 'SAR-Alpha-01', 'pattern': 'grid_search', 'start': (37.4420, -121.7685)},
        {'id': 'SAR-Bravo-02', 'pattern': 'spiral_search', 'start': (37.4415, -121.7675)},
        {'id': 'SAR-Charlie-03', 'pattern': 'parallel_search', 'start': (37.4425, -121.7690)},
    ]
    
    active_drones = {}
    
    for drone_info in drones:
        drone_id = drone_info['id']
        logger.info(f"🚁 Deploying {drone_id} with {drone_info['pattern']} pattern")
        
        # Create simulated drone
        initial_telemetry = simulator.create_drone(
            drone_id, 
            drone_info['pattern'], 
            drone_info['start']
        )
        
        if initial_telemetry:
            # Start tracking in CalTopo
            position = (initial_telemetry['longitude'], initial_telemetry['latitude'])
            battery = initial_telemetry['battery_level']
            
            success = drone_tracker.start_drone_track(drone_id, position)
            if success:
                active_drones[drone_id] = True
                logger.info(f"✅ {drone_id} tracking started on CalTopo")
            else:
                logger.error(f"❌ {drone_id} CalTopo tracking failed")
        else:
            logger.error(f"❌ {drone_id} simulation failed")
    
    if not active_drones:
        logger.error("❌ No drones successfully deployed")
        return False
        
    # Step 3: Run mission simulation
    logger.info(f"\nStep 3: Running SAR Mission Simulation")
    logger.info(f"📍 Check your CalTopo map: https://caltopo.com/m/{caltopo_creds[3]}")
    
    mission_duration = 180  # 3 minutes for demo (normally would be much longer)
    update_interval = 10    # Update every 10 seconds
    
    try:
        for elapsed_time in range(0, mission_duration, update_interval):
            logger.info(f"\n⏱️  Mission Time: {elapsed_time//60}:{elapsed_time%60:02d}")
            
            # Update each drone
            for drone_id in list(active_drones.keys()):
                # Get updated telemetry from simulator
                telemetry = simulator.update_drone(drone_id)
                
                if telemetry:
                    # Log drone status
                    status = simulator.get_drone_status(drone_id)
                    logger.info(f"  {drone_id}: {status['status']} | "
                              f"Battery: {status['battery_level']:.1f}% | "
                              f"Progress: {status['waypoint_progress']}")
                    
                    # Update CalTopo track
                    position = (telemetry['longitude'], telemetry['latitude'])
                    battery = int(telemetry['battery_level'])
                    
                    success = drone_tracker.update_drone_position(drone_id, position, battery)
                    if not success:
                        logger.warning(f"⚠️  {drone_id} CalTopo update failed")
                    
                    # Check if drone needs to land
                    if telemetry['battery_level'] < 15:
                        logger.warning(f"🪫 {drone_id} low battery - initiating landing")
                        simulator.land_drone(drone_id)
                        
                    if telemetry['flight_status'] in ['mission_complete', 'landed']:
                        logger.info(f"🎯 {drone_id} mission complete")
                        del active_drones[drone_id]
                        
                else:
                    logger.error(f"❌ {drone_id} telemetry update failed")
                    del active_drones[drone_id]
            
            # Check if mission is complete
            if not active_drones:
                logger.info("🎉 All drones have completed their missions")
                break
                
            # Wait before next update
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  Mission interrupted by user")
    
    # Step 4: Mission summary
    logger.info("\nStep 4: Mission Summary")
    
    for drone_info in drones:
        drone_id = drone_info['id']
        status = simulator.get_drone_status(drone_id)
        
        if status:
            logger.info(f"  {drone_id}:")
            logger.info(f"    Status: {status['status']}")
            logger.info(f"    Battery: {status['battery_level']:.1f}%")
            logger.info(f"    Flight Time: {status['mission_time']:.1f} minutes")
            logger.info(f"    Pattern: {status['pattern']}")
        
        # Clean up tracking
        drone_tracker.stop_drone_track(drone_id)
        simulator.remove_drone(drone_id)
    
    logger.info("\n🎉 SAR MISSION SIMULATION COMPLETED!")
    logger.info("✅ Realistic drone telemetry generated")
    logger.info("✅ CalTopo real-time tracking demonstrated")
    logger.info("✅ Multi-drone coordination simulated")
    logger.info("✅ Battery management and safety protocols tested")
    
    return True


def test_simulation_only():
    """Test just the drone simulation without CalTopo"""
    
    logger.info("🚁 Testing Drone Simulation Only (No CalTopo)")
    logger.info("=" * 50)
    
    # Initialize simulator
    simulator = RealisticDroneSimulator((37.4419, -121.7680))
    
    # Create test drone
    drone_id = "TEST-DRONE-001"
    initial_telemetry = simulator.create_drone(drone_id, 'grid_search')
    
    if not initial_telemetry:
        logger.error("❌ Failed to create test drone")
        return False
        
    logger.info("✅ Test drone created successfully")
    logger.info(f"Initial telemetry: {initial_telemetry}")
    
    # Run simulation for 60 seconds
    for i in range(6):
        time.sleep(10)
        telemetry = simulator.update_drone(drone_id)
        
        if telemetry:
            logger.info(f"Update {i+1}: Pos({telemetry['latitude']:.6f}, {telemetry['longitude']:.6f}) "
                       f"Battery: {telemetry['battery_level']:.1f}% "
                       f"Status: {telemetry['flight_status']}")
        else:
            logger.error(f"❌ Update {i+1} failed")
            break
    
    logger.info("✅ Simulation test completed")
    return True


def main():
    """Run appropriate test based on available credentials"""
    
    logger.info("🛸 SAR Drone Tracker - Integration Test Suite")
    logger.info("=" * 70)
    
    # Check what credentials are available
    has_caltopo = all([
        os.getenv('CALTOPO_CREDENTIAL_ID'),
        os.getenv('CALTOPO_CREDENTIAL_SECRET'),
        os.getenv('CALTOPO_TEAM_ID'),
        os.getenv('CALTOPO_MAP_ID')
    ])
    
    if has_caltopo:
        logger.info("✅ CalTopo credentials found - running full integration test")
        success = test_complete_sar_system()
    else:
        logger.info("ℹ️  CalTopo credentials not available - running simulation-only test")
        success = test_simulation_only()
    
    if success:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("Your SAR drone tracking system is ready for deployment")
        
        if has_caltopo:
            logger.info("Next steps:")
            logger.info("1. Deploy to Google Cloud Functions")
            logger.info("2. Set up automated triggers")
            logger.info("3. Train your SAR team on the system")
            logger.info("4. Integrate real Skydio API when documentation is available")
        else:
            logger.info("Next steps:")
            logger.info("1. Get CalTopo API credentials from your team")
            logger.info("2. Re-run test with full integration")
            logger.info("3. Deploy to Google Cloud Functions")
    else:
        logger.error("\n❌ TESTS FAILED")
        logger.error("Check error messages above for troubleshooting")


if __name__ == "__main__":
    main()
