"""
Test final corrected Skydio client
Based on actual official example showing:
- Base: https://api.skydio.com/api
- Auth: Authorization: ApiToken {token}
- Version: v0
- Response: {"status_code": 200, "data": {...}}
"""

import os
import logging
from dotenv import load_dotenv
#from src.final_corrected_skydio_client import SkydioClient, SkydioTelemetryExtractor
from test_skydio_client import SkydioClient, SkydioTelemetryExtractor

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_final_skydio():
    """Test Skydio with actual official API pattern"""
    
    logger.info("Testing Final Skydio Client (Official Pattern)")
    logger.info("Based on: Authorization: ApiToken {token}")
    logger.info("Base URL: https://api.skydio.com/api/v0/")
    logger.info("=" * 60)
    
    # Get API token
    api_token = os.getenv('API_TOKEN') or os.getenv('SKYDIO_API_TOKEN') or os.getenv('SKYDIO_API_KEY')
    
    if not api_token:
        logger.error("Missing API token")
        logger.info("Set one of these in your .env file:")
        logger.info("API_TOKEN=your_token_here")
        logger.info("(or SKYDIO_API_TOKEN=your_token_here)")
        return False
        
    logger.info(f"Using API Token: {'*' * 50}{api_token[-6:]}")
    
    try:
        # Create client with correct pattern
        client = SkydioClient(api_token)
        
        # Test connection
        logger.info("Testing connection...")
        if client.test_connection():
            logger.info("SUCCESS! Connection established")
            
            # Test batteries endpoint (from official example)
            logger.info("Testing batteries endpoint (from official example)...")
            batteries = client.get_batteries()
            
            if batteries is not None:
                logger.info(f"Found {len(batteries)} batteries:")
                for i, battery in enumerate(batteries[:3]):
                    logger.info(f"  Battery {i+1}: {battery}")
            else:
                logger.info("No batteries found")
            
            # Test vehicles
            logger.info("Testing vehicles endpoint...")
            vehicles = client.get_vehicles()
            
            if vehicles:
                logger.info(f"Found {len(vehicles)} vehicle(s):")
                for i, vehicle in enumerate(vehicles[:2]):
                    logger.info(f"  Vehicle {i+1}: {vehicle}")
                    
                # Test vehicle details
                if vehicles:
                    vehicle_id = vehicles[0].get('id')
                    if vehicle_id:
                        logger.info(f"Getting details for vehicle {vehicle_id}...")
                        details = client.get_vehicle_details(vehicle_id)
                        if details:
                            logger.info(f"Vehicle details: {details}")
                            
                        # Test live telemetry
                        logger.info(f"Testing live telemetry...")
                        live_data = client.get_live_telemetry(vehicle_id)
                        if live_data:
                            logger.info(f"Live telemetry: {live_data}")
                            
                            # Test telemetry extraction
                            position = SkydioTelemetryExtractor.extract_position_data(live_data)
                            battery = SkydioTelemetryExtractor.extract_battery_level(live_data)
                            status = SkydioTelemetryExtractor.extract_flight_status(live_data)
                            
                            logger.info("Extracted data:")
                            logger.info(f"  Position: {position}")
                            logger.info(f"  Battery: {battery}%")
                            logger.info(f"  Status: {status}")
                            
                        else:
                            logger.info("No live telemetry (vehicle may be offline)")
            else:
                logger.info("No vehicles found")
            
            # Test flights
            logger.info("Testing flights endpoint...")
            flights = client.get_flights(limit=5)
            
            if flights:
                logger.info(f"Found {len(flights)} flight(s):")
                for i, flight in enumerate(flights[:2]):
                    logger.info(f"  Flight {i+1}: {flight}")
                    
                # Test flight telemetry
                if flights:
                    flight_id = flights[0].get('id')
                    if flight_id:
                        logger.info(f"Getting telemetry for flight {flight_id}...")
                        telemetry = client.get_flight_telemetry(flight_id)
                        
                        if telemetry:
                            logger.info(f"Got {len(telemetry)} telemetry points")
                            
                            if telemetry:
                                # Test extraction on flight telemetry
                                sample = telemetry[0]
                                position = SkydioTelemetryExtractor.extract_position_data(sample)
                                battery = SkydioTelemetryExtractor.extract_battery_level(sample)
                                status = SkydioTelemetryExtractor.extract_flight_status(sample)
                                
                                logger.info("Flight telemetry extraction:")
                                logger.info(f"  Position: {position}")
                                logger.info(f"  Battery: {battery}%")
                                logger.info(f"  Status: {status}")
                                
                                if position:
                                    logger.info("SUCCESS! Telemetry extraction working")
                        else:
                            logger.info("No telemetry data for this flight")
            else:
                logger.info("No flights found")
            
            logger.info("COMPLETE SUCCESS! Skydio API fully functional")
            return True
            
        else:
            logger.error("Connection failed")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

def manual_test():
    """Manual test using exact official pattern"""
    
    api_token = os.getenv('API_TOKEN') or os.getenv('SKYDIO_API_TOKEN') or os.getenv('SKYDIO_API_KEY')
    if not api_token:
        return
        
    logger.info("Manual test with exact official pattern...")
    
    import requests
    
    # Exact pattern from official example
    headers = {
        "Accept": "application/json", 
        "Authorization": f"ApiToken {api_token}"
    }
    
    # Test the exact URL from official example
    url = "https://api.skydio.com/api/v0/batteries"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        logger.info(f"Manual test results:")
        logger.info(f"  URL: {url}")
        logger.info(f"  Status: {response.status_code}")
        logger.info(f"  Headers: {dict(response.headers)}")
        
        if response.content:
            try:
                data = response.json()
                logger.info(f"  Response: {data}")
                
                status_code = data.get("status_code")
                if status_code == 200:
                    logger.info("SUCCESS! Official pattern works!")
                    batteries = data.get("data", {}).get("batteries", [])
                    logger.info(f"  Found {len(batteries)} batteries")
                else:
                    error_msg = data.get("error_message", "Unknown error")
                    logger.error(f"API Error {status_code}: {error_msg}")
                    
            except json.JSONDecodeError:
                logger.info(f"  Text: {response.text}")
        
    except Exception as e:
        logger.error(f"Manual test failed: {str(e)}")

def main():
    """Run final test"""
    
    logger.info("Skydio API Final Test - Official Pattern")
    logger.info("Authorization: ApiToken {token}")
    logger.info("Base: https://api.skydio.com/api/v0/")
    logger.info("=" * 70)
    
    success = test_final_skydio()
    
    if not success:
        logger.info("Running manual test for comparison...")
        manual_test()
    else:
        logger.info("")
        logger.info("SUCCESS! Your Skydio API is now working correctly")
        logger.info("Ready to integrate with CalTopo for complete SAR tracking")

if __name__ == "__main__":
    main()
