"""
Test script for CalTopo integration using sample drone track data
Run this to test your CalTopo API setup before connecting to Skydio
"""

import os
import time
import logging
from dotenv import load_dotenv
from src.caltopo_client import CalTopoClient, DroneTracker

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample drone track data (replace with your test area coordinates)
SAMPLE_TRACKS = {
    "drone_001": [
        # Example coordinates around a search area
        # Format: (longitude, latitude)
        (-121.7680, 37.4419),  # Start position
        (-121.7685, 37.4425),  # Moving northeast
        (-121.7690, 37.4430),  # Continuing pattern
        (-121.7695, 37.4435),  # Search grid
        (-121.7700, 37.4440),  # Further out
        (-121.7695, 37.4445),  # Return sweep
        (-121.7690, 37.4450),  # Systematic coverage
        (-121.7685, 37.4445),  # Back track
        (-121.7680, 37.4440),  # Closing pattern
    ],
    "drone_002": [
        # Second drone with different search pattern
        (-121.7650, 37.4400),  # Different start
        (-121.7655, 37.4405),  # Parallel search
        (-121.7660, 37.4410),  # Moving east
        (-121.7665, 37.4415),  # Continuing
        (-121.7670, 37.4420),  # Further coverage
        (-121.7665, 37.4425),  # Return pattern
        (-121.7660, 37.4430),  # Systematic
        (-121.7655, 37.4435),  # Back sweep
    ]
}


def test_caltopo_connection():
    """Test basic CalTopo API connection"""
    logger.info("Testing CalTopo API connection...")
    
    # Get credentials from environment
    credential_id = os.getenv('CALTOPO_CREDENTIAL_ID')
    credential_secret = os.getenv('CALTOPO_CREDENTIAL_SECRET') 
    team_id = os.getenv('CALTOPO_TEAM_ID')
    map_id = os.getenv('CALTOPO_MAP_ID')
    
    if not all([credential_id, credential_secret, team_id, map_id]):
        logger.error("Missing CalTopo credentials. Check your .env file.")
        return False
        
    try:
        # Create client
        client = CalTopoClient(credential_id, credential_secret, team_id)
        
        # Test connection by getting team data
        team_data = client.get_team_maps()
        if team_data:
            logger.info("✅ Successfully connected to CalTopo API")
            
            # List available maps
            maps = [f for f in team_data.get("features", []) 
                   if f.get("properties", {}).get("class") == "CollaborativeMap"]
            logger.info(f"Found {len(maps)} maps in team")
            
            return True
        else:
            logger.error("❌ Failed to connect to CalTopo API")
            return False
            
    except Exception as e:
        logger.error(f"❌ CalTopo connection test failed: {str(e)}")
        return False


def test_track_creation():
    """Test creating and updating drone tracks"""
    logger.info("Testing drone track creation...")
    
    # Get credentials
    credential_id = os.getenv('CALTOPO_CREDENTIAL_ID')
    credential_secret = os.getenv('CALTOPO_CREDENTIAL_SECRET')
    team_id = os.getenv('CALTOPO_TEAM_ID')
    map_id = os.getenv('CALTOPO_MAP_ID')
    
    try:
        # Create client and tracker
        client = CalTopoClient(credential_id, credential_secret, team_id)
        tracker = DroneTracker(client, map_id)
        
        logger.info("🚁 Starting drone track simulation...")
        
        # Simulate multiple drones
        for drone_id, coordinates in SAMPLE_TRACKS.items():
            logger.info(f"Starting track for {drone_id}")
            
            # Start tracking with first position
            first_pos = coordinates[0]
            success = tracker.start_drone_track(drone_id, first_pos)
            
            if not success:
                logger.error(f"Failed to start track for {drone_id}")
                continue
                
            # Simulate movement through remaining positions
            for i, position in enumerate(coordinates[1:], 1):
                logger.info(f"  {drone_id}: Position {i+1}/{len(coordinates)}")
                
                # Simulate battery drain
                battery = max(100 - (i * 5), 10)
                
                success = tracker.update_drone_position(
                    drone_id, position, battery_level=battery
                )
                
                if not success:
                    logger.error(f"Failed to update position for {drone_id}")
                    break
                    
                # Small delay to simulate real-time updates
                time.sleep(2)
                
            logger.info(f"✅ Completed track simulation for {drone_id}")
            
        logger.info("🎯 All drone tracks completed successfully!")
        logger.info(f"Check your CalTopo map: https://caltopo.com/m/{map_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Track creation test failed: {str(e)}")
        return False


def test_cleanup():
    """Clean up test data (optional)"""
    logger.info("Cleaning up test data...")
    
    credential_id = os.getenv('CALTOPO_CREDENTIAL_ID')
    credential_secret = os.getenv('CALTOPO_CREDENTIAL_SECRET')
    team_id = os.getenv('CALTOPO_TEAM_ID')
    map_id = os.getenv('CALTOPO_MAP_ID')
    
    try:
        client = CalTopoClient(credential_id, credential_secret, team_id)
        tracker = DroneTracker(client, map_id)
        
        # Stop tracking all test drones
        for drone_id in SAMPLE_TRACKS.keys():
            tracker.stop_drone_track(drone_id)
            
        logger.info("✅ Cleanup completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    logger.info("🧪 Starting CalTopo Integration Tests")
    logger.info("=" * 50)
    
    # Test 1: Basic connection
    if not test_caltopo_connection():
        logger.error("❌ Basic connection test failed. Check your credentials.")
        return
        
    # Test 2: Track creation
    if not test_track_creation():
        logger.error("❌ Track creation test failed.")
        return
        
    # Optional: Clean up test data
    user_input = input("\nClean up test tracks? (y/n): ").lower().strip()
    if user_input == 'y':
        test_cleanup()
        
    logger.info("=" * 50)
    logger.info("🎉 All tests completed!")
    logger.info("\nNext steps:")
    logger.info("1. Check your CalTopo map for the test tracks")
    logger.info("2. Verify the tracks appear correctly")
    logger.info("3. Ready to integrate with Skydio API")


if __name__ == "__main__":
    main()
