# API Setup Guide

This guide walks you through setting up API access for both CalTopo and Skydio to enable drone tracking integration.

## CalTopo API Setup

### Step 1: Verify Team Account
1. Ensure your SAR organization has a **CalTopo Team account**
2. You need **Team Admin** privileges to create service accounts
3. Go to your team admin page: `https://caltopo.com/group/[your-team-id]/admin/details`

### Step 2: Create Service Account
1. In the Team Admin page, click the **Details** tab
2. Scroll to the bottom and find "Service Account" section
3. Click **Create a Service Account**
4. Choose:
   - **Title**: "SAR Drone Tracker"
   - **Permission Level**: "UPDATE" (minimum required)
5. Click **Create**

### Step 3: Save Credentials
⚠️ **IMPORTANT**: The credential secret appears only once!

1. Copy the **Credential Secret** immediately
2. Copy the **Credential ID** (you can view this later)
3. Note your **Team ID** from the URL
4. Find your **Map ID** by opening the map you want to use: `https://caltopo.com/m/[map-id]`

### Step 4: Add to .env File
```bash
CALTOPO_CREDENTIAL_ID=your_credential_id_here
CALTOPO_CREDENTIAL_SECRET=your_credential_secret_here
CALTOPO_TEAM_ID=your_team_id_here
CALTOPO_MAP_ID=your_map_id_here
```

### Step 5: Test CalTopo Connection
```bash
python test_caltopo_integration.py
```

## Skydio API Setup

### Step 1: Verify Enterprise Account
1. Confirm you have **Skydio X10** with **Enterprise account**
2. Access to **Fleet Manager** or **Remote Ops**
3. Contact your Skydio account manager if unsure

### Step 2: Access API Documentation
1. Go to: https://apidocs.skydio.com/reference/introduction
2. Sign in with your Skydio Enterprise account
3. Navigate to authentication section

### Step 3: Generate API Credentials
1. In Skydio Cloud dashboard, go to **Settings** → **API Keys**
2. Click **Generate New API Key**
3. Choose appropriate permissions:
   - ✅ Read telemetry data
   - ✅ Read fleet information
   - ✅ Read flight data
4. Copy the **API Key** and **API Secret**

### Step 4: Find Drone ID
1. In Fleet Manager, select your drone
2. Note the **Serial Number** or **Drone ID**
3. This will be used to identify your specific drone

### Step 5: Add to .env File
```bash
SKYDIO_API_KEY=your_api_key_here
SKYDIO_API_SECRET=your_api_secret_here
SKYDIO_DRONE_ID=your_drone_serial_here
```

## Google Cloud Platform Setup

### Step 1: Create GCP Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing one
3. Note the **Project ID**

### Step 2: Enable Required APIs
```bash
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable logging.googleapis.com
```

### Step 3: Create Service Account
```bash
gcloud iam service-accounts create sar-drone-tracker \
    --display-name="SAR Drone Tracker Service Account"
```

### Step 4: Generate Service Account Key
```bash
gcloud iam service-accounts keys create credentials.json \
    --iam-account=sar-drone-tracker@[YOUR-PROJECT-ID].iam.gserviceaccount.com
```

### Step 5: Add to .env File
```bash
GCP_PROJECT_ID=your_project_id_here
GOOGLE_APPLICATION_CREDENTIALS=./credentials.json
```

## Security Best Practices

### Protect Your Credentials
- ✅ Never commit `.env` file to git
- ✅ Store backup copies securely (encrypted)
- ✅ Limit access to essential team members only
- ✅ Rotate keys quarterly

### Repository Secrets (for GitHub Actions)
1. Go to Repository → Settings → Secrets and Variables → Actions
2. Add these secrets:
```
CALTOPO_CREDENTIAL_ID
CALTOPO_CREDENTIAL_SECRET
SKYDIO_API_KEY
SKYDIO_API_SECRET
GCP_PROJECT_ID
GCP_SERVICE_ACCOUNT_KEY (paste contents of credentials.json)
```

## Testing Your Setup

### Test CalTopo Only
```bash
# Test basic connection
python -c "
from src.caltopo_client import CalTopoClient
import os
from dotenv import load_dotenv
load_dotenv()
client = CalTopoClient(
    os.getenv('CALTOPO_CREDENTIAL_ID'),
    os.getenv('CALTOPO_CREDENTIAL_SECRET'),
    os.getenv('CALTOPO_TEAM_ID')
)
result = client.get_team_maps()
print('✅ CalTopo connection successful' if result else '❌ CalTopo connection failed')
"
```

### Test Full Integration
```bash
python test_caltopo_integration.py
```

## Troubleshooting

### Common CalTopo Issues
- **"Authentication failed"**: Check credential ID and secret
- **"Permission denied"**: Ensure service account has UPDATE permission
- **"Map not found"**: Verify map ID and team access

### Common Skydio Issues
- **"API key invalid"**: Verify enterprise account access
- **"Drone not found"**: Check drone ID format
- **"No telemetry data"**: Ensure drone is powered and connected

### Common GCP Issues
- **"Project not found"**: Check project ID spelling
- **"Service account error"**: Verify credentials.json file exists
- **"Permission denied"**: Check service account roles

## Support Contacts

### Internal Team
- Lead Developer: [Your Name] - [your.email@sar.org]
- SAR Operations: [Ops Lead] - [ops.email@sar.org]

### External Support
- **CalTopo Team Support**: Use the support chat on caltopo.com
- **Skydio Enterprise**: Contact your account manager
- **Google Cloud**: Use Google Cloud Console support

## API Rate Limits

### CalTopo
- Standard team accounts: Reasonable use policy
- Recommended: No more than 1 request per 5 seconds per drone

### Skydio
- Enterprise accounts: Higher limits (check documentation)
- Recommended: Poll telemetry every 10-30 seconds

### Google Cloud Functions
- 1000 requests per 100 seconds per function
- Should be sufficient for typical SAR operations

---

**Last Updated**: [Current Date]  
**Next**: See [deployment.md](deployment.md) for deployment instructions

