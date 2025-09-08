import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_token = os.getenv('SKYDIO_API_TOKEN') or os.getenv('SKYDIO_API_KEY')

headers = {'Authorization': f'Bearer {api_token}', 'Accept': 'application/json'}

# Test different base URLs
base_urls = [
#    "https://cloud.skydio.com/api/v1/vehicles",
    "https://api.skydio.com/api/v0/batteries", 
    "https://api.skydio.com/api/vehicles", 
    "https://api.skydio.com/v1/vehicles", 
    "https://api.skydio.com/vehicles",
]

for url in base_urls:
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"{url}: {response.status_code}")
        if response.status_code == 200:
            print(f"  SUCCESS! Response: {response.json()}")
            break
    except Exception as e:
        print(f"{url}: Error - {e}")
