# [README.](http://README.md)[md](http://README.md) \- sar\_drone\_tracker

Display and track your Skydio X10 drone’s real-time location in CalTopo using the native APIs within Skydio Cloud and CalTopo.

| View From Skydio Flight Deck ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/intro-skydio.png?raw=true)| View From CalTopo With Live Real-Time Drone Tracking ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/intro-caltopo.png?raw=true) |
| :---: | :---: |

## High Level Architecture


This script polls the Skydio Cloud for a vehicle status and then polls Skydio Cloud’s real-time telemetry API endpoint for the drone every 10 seconds (configurable) for the drone’s coordinates. The coordinates are immediately relayed to the CalTopo servers and posted to their respective “Trackable Device” at the same polling interval. The identifier of the X10 drone is set in a configuration file, and access to Skydio Cloud is authenticated by an API key. The only communication of this software is between Skydio Cloud API endpoints (vehicle status and realtime telemetry) and CalTopo’s Location Tracker API endpoint.

CalTopo doesn’t require / doesn’t allow any authentication to post location updates for these types of devices, so access is obscured by choosing harder-to-guess device names. This script does not need or use a [CalTopo API / Service Account](https://training.caltopo.com/all_users/team-accounts/teamapi). Each Trackable Device can be displayed on a map in realtime, and tracks leave a trail. According to CalTopo documentation, after 3000 tracks are received or after a device stops receiving updates for 24 hours or after manually stopping a tracks recording, the recorded track is converted to a “Line and Polygon”.

This script was designed to be run from a local system or server, to keep complexity and dependencies low. This information flows directly from Skydio Cloud ←→ this software ←→ CalTopo. No other intermediary systems are involved, to minmize security and privacy risk.

## Requirements

- A Skydio X10 drone and controller with internet access  
- Skydio real-time telemetry enabled  
- An API access key to your Skydio 10 Drone (or the Skydio Cloud Flight Simulator)  
- A CalTopo Team account (preferred but not required)  
- A CalTopo “Trackable Device” setup for your drone by your team admin or manager (preferred but not required)  
- A computer capable of running python3, with Internet access to both CalTopo and your Skydio Cloud account

## Known Issues

- This script has only been tested to work with one drone at a time. A future release of this software may support multiple simultaneous drone support.  
- CalTopo doesn’t record or display altitude information for Trackable Devices, only latitude and longitude. Your drone’s track profile will reflect the *terrain* profile, not your drone’s flight profile. This is a limitation of CalTopo, and a feature request has been filed. A future release of this software may implement tracking via a different map object type if altitude information is important.  
- ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/arch-profile.png?raw=true)
- Unknowns: This software hasn’t been tested to operate in a cloud environment, nor has it been used in an area with spotty communications. In testing, it seems tolerant to occasional Skydio and CalTopo connection failures, it just keeps retying but it may lose positional updates.

## 

## Installation Instructions

TBD

## Using This Software – Tracking Your Drone During A Mission

During a SAR mission, and especially in the first few hours of a new mission, you don’t want the operational burden of configuring a bunch of software. You want to get into the field and start searching. This software is designed to **start posting your drone information immediately into CalTopo** every time you launch it, After following the one-time setup below. Once your drone is launched, you can then tweak map settings to change how your drone is displayed.

### Step 1: Power On Your Drone

This software requires your drone to be powered on and communicating with Skydio Cloud. 

If the drone isn’t ready, the software will keep retrying to connect. While the software is running it will also keep publishing location information

### Step 2: Start the Software sar\_drone\_tracker

1. On your internet-connected computer (laptop or hosted on a server), run “python sar\_drone\_tracker”  
2. You should see it connect to Skydio cloud, connect to the drone and start generating telemetry at the polling frequency (default: every 10 seconds). You will see the Call Sign displayed, the battery level, attachments, and position information.  
3. It will also start publishing the drone’s location to CalTopo, using the Call Sign you configured.  
4. Now you need to add the drone’s object to your CalTopo map.

![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/using-console.png?raw=true)

### Step 3: Share Your Drone’s Location on CalTopo

Pro Tip: If you have a CalTopo *Teams* account, and have enabled “Shared Locations” in your Map Layers, your drone will automatically appear on your CalTopo map and its location (as a “dot”) will update as you fly.

#### If you have a CalTopo Teams Account

| How the drone real-time telemetry looks on CalTopo. Note that the label of this “Trackable Device” object was defined by the Team Admin in Configuration Step 4 below. | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/share-1.png?raw=true) |
| :---- | :---- |
| **To share your drone’s real-time tracks with others** who are monitoring this CalTopo map, click the drone’s marker Then click the “Record to Map” option Choose a Label for your Drone (Notice that the Device Type is pre-filled out and cannot be edited. This is your drone’s call sign.) Enter your preferred color, line style and weight. Pro Tip: Choose a directional line style, the arrows on the line will point in the flight direction of your drone. Click “OK” | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/share-2.png?raw=true) |
| **Your drone real-time location and tracks are shared to the CalTopo map.  Everyone else viewing that map, regardless of their account level, will see a new object appear under “Live Tracks”, your drone\! Here’s how that looks →** | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/share-3.png?raw=true) |
| Note: If you only want to show the drone’s tracks without creating and sharing a map object, instead of “Record to Map” click the drone’s marker and choose “Show Track”.  This might be useful if you’re flying but not yet at your assigned search area, and don’t want to complicate the search map. | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/share-4.png?raw=true)|

#### If you have a personal CalTopo Account (not Teams level)

According to [CalTopo’s directions](https://training.caltopo.com/all_users/share/live-tracking) you can add a drone call sign directly to a CalTopo map object and get real-time tracking. This is done via the “Locator” Map Object and it will use the same Call Sign you configured for your drone and that is displayed in the sar\_drone\_tracker software. It’s slightly more clumsy to configure than with a Teams account, because you have enter in the Call Sign each time you configure a new track recording. See CalTopo’s site for directions or the section below (“Create a Live Tracking Map Object \- Personal CalTopo Account”), but the Skydio and software configuration steps are identical.

### Step 4: Stop The Recording

Live Tracks are converted into Tracks stored under “Lines and Polygons” when you manually stop record, or when CalTopo stops receiving updates in 24 hours, or when your drone records more than 3,000 updates.

It’s a best practice to manually stop your recording once you’re done with your mission, or switch assignments.

| Click the pencil icon on your object to edit it | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/share-5.png?raw=true) |
| :---- | :---- |
| Choose “Stop Recording” Then click “Stop” | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/share-6.png?raw=true) ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/share-7.png?raw=true) |
| Your drone tracks are now moved to “Lines and Polygons” See “Team Drone 6” →  | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/share-8.png?raw=true)|

## Setup and Configuration (One-Time)

Here’s the high-level set of steps to get the software and systems configured. These are meant to be done one-time:

1. Get your Skydio drone information   
2. Generate a Skydio API token  
3. Enable Live Streaming for your Skydio account  
4. Create and configure a CalTopo Trackable Device  
5. Create a Call Sign for this Trackable Device  
6. Display and Configure your CalTopo Live Tracking Object OR  
7. Create a CalTopo Locator Map Object

### In Skydio Cloud

#### Get Your Skydio Drone Information

Within [Skydio Cloud](https://cloud.skydio.com), navigate to your drone to confirm its serial number. Go to Settings → Devices → *Your Drone* → Serial Number.  The serial number is typically formatted like “sim-d7y1odc2” (for flight simulator vehicles) or “SkydioX10-xxxx” (for physical X10 aircraft).

#### Store this *entire* serial number in your .env file, on the line **DRONE\_SERIALS=** 

Example: DRONE\_SERIALS=SkydioX10-x8a8

**IMPORTANT: The last 4 characters of the drone’s serial number will be used in CalTopo to create this drone’s “call sign” in later steps.**

#### Generate an API Token

Register a Skydio API Token. Depending on your level of access to Skydio Cloud, you may not see the option to generate API Tokens, in which case you’ll need to work with your Skydio administrator. It’s a security best practice to generate an API Token for each integration (like CalTopo), and for each token to have the *least* amount of permissions and access. Do not reuse an existing API Token since you don’t know what permissions and group access it may have.

![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/setup-1.png?raw=true)

| Create a new API Token and give it a descriptive name like “CalTopo Integration Read Only” | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/setup-2.png?raw=true) |
| :---- | :---- |
| Groups \- Set this to the group that includes your drones. You might set this to access your entire fleet. |  |
| Your API access key needs to have the following read-only access permissions set: Attachments, Batteries, Flight Telemetry, Flights, JWT Validation, Live Telemetry, OpenAPI Spec, Sensor Package, Users, Vehicles, Webhook Validation, Webhooks, and Whoami. | By default no permissions are granted, but these can be changed if you need to make adjustments after creation.  |

Finally, store this API Token in your .env file on the line **API\_TOKEN=**

**VERY IMPORTANT: Copy and/or save the API Token secret key (e.g. “API\_TOKEN”) immediately\!** When you generate an API Token, it is displayed on the screen but *never shown again*. 

#### Enable Live Telemetry

In Skydio Cloud, navigate to Settings → Live Streaming, and make sure “Live Telemetry” is enabled. This script doesn’t use RTSP Streaming because it doesn’t interact with the drone’s streaming video feed or images.  
![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/setup-3.png?raw=true) 

### In CalTopo 

NOTE: You will need a Teams-level CalTopo account to configure a Trackable Device. See [CalTopo Team and Device Tracking](https://training.caltopo.com/all_users/team-accounts/team-tracking#trackabledevice) for more info.  If you do not have a Teams-level CalTopo account, you can configure a Locator Map Object as an alternative. But you still need to create a Call Sign for your drone, it is configured the same way whether or not you have a Teams-level CalTopo account.

#### Create the Drone’s Call Sign

CalTopo uses a “Call Sign” to uniquely reference your drone. The Call Sign is made up of three parts: 

1. A *Connect Key* that you can define. Pick your agency name, for example. Do not include hyphens in your Connect Key.  
2. A hyphen character (“-”)  
3. The *Device ID* \- the last four characters of your Skydio drone’s serial number.

Example Call Signs:

| Call Sign | How it was constructed |
| :---- | :---- |
| CITY\_SAR-x8a8 | The *Connect Key* of “CITY\_SAR”, plus a “-”, plus the *Device ID* of the last 4 digits of drone serial number ending in x8a8 |
| SARTRUCKS-1414 | *Connect Key* of “SARTRUCKS”, plus a “-”, plus a *Device ID* based on the last 4 digits of a drone serial number ending in “1414” |
| XSCSAR\_4EXHJJ2-x8a8 | A more secure example. A *Connect Key* of “XSCSAR\_4EXHJJ2”, plus a “-”, plus a *Device ID* based on the last 4 digits of drone serial number ending in x8a8 |

**Security Consideration:** Pick something distinctive and unique for the *Connect Key* part of the Call Sign. If someone knows or can guess your Call Sign, they could send bogus telemetry signals to CalTopo for your drone’s CalTopo live tracks, confusing people. Consider adding random letters and numbers, such as “CITY\_SAR\_x7g5aa9j”

**IMPORTANT \- When registering the Trackable Device in CalTopo, the Call Sign *cannot be edited* after you configure it in CalTopo.** If you make a mistake here, delete it and create the corrected one. The Label can be edited, but that’s not necessary to change it after configuring it. The “Label” you enter here is displayed when the drone appears as a real-time “shared location” device. You can create and edit new labels for the device during missions.

#### Create and Configure a Trackable Device – CalTopo Teams Accounts

[Follow these instructions](https://training.caltopo.com/all_users/team-accounts/team-tracking#trackabledevice) to configure CalTopo to receive telemetry from this script of your drone’s location. You will be configuring a “Trackable Device”, Type “Other Device”.

| Within your CalTopo admin console, create a “Trackable Device”. Choose “Add Other Device” Tip: The Admin interface URL is [https://caltopo.com/group/](https://caltopo.com/group/)\<team\_ID\>/admin/trackables | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/trackable-1.png?raw=true)   |
| :---- | :---- |
| IMPORTANT: Enter the Call Sign exactly as you specified | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/trackable-2.png?raw=true) |
| Two examples listed. | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/trackable-3.png?raw=true) |
| Note: Anytime a connected device (aka “Trackable Device”) is on and reporting its location, it will appear in the Shared Locations Map overlay. | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/trackable-4.png?raw=true) |

If you have a CalTopo Teams account, you are done configuring your drone in CalTopo. 

#### Create a Live Tracking Map Object \- CalTopo Personal Accounts

This step is not necessary for CalTopo Teams-level Accounts. Each time you need to track your drone’s flight, you will need to create a Locator Map Object, enter in your drone’s Call Sign (see above). CalTopo will take location updates from this software and display them on your map.

| Within your Map Objects panel, create a new “Locator” Map Object | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/trackable-5.png?raw=true) |
| :---- | :---- |
| Choose “Live Track \- Fleet, Email, Other” | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/trackable-6.png?raw=true) |
| Use the **Call Sign** information (earlier step) for this object. Add a Label and color to make it easy to see on the map | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/trackable-7.png?raw=true)|
| Tip: Configure the “line style” to be an arrow to show direction of travel in the drone’s tracks. | ![](https://github.com/billburns250/sar-drone-tracker/blob/main/assets/trackable-8.png?raw=true) |

## Additional Information and Resources

- [CalTopo Live Tracking and Locators](https://training.caltopo.com/all_users/share/live-tracking)   
- [CalTopo Live Team Tracking](https://training.caltopo.com/all_users/team-accounts/team-tracking)  
- [Skydio API Docs](https://apidocs.skydio.com/reference/introduction)  
- [Skydio’s Cloud API github repository](https://github.com/Skydio/skydio-cloud-api-examples)  
- [Skydio Cloud](https://cloud.skydio.com/)  
- [Skydio Cloud Live Telemetry API](https://apidocs.skydio.com/reference/live-telemetry)  
- [This script’s github repository](https://github.com/users/billburns250/projects/1) (private)

### Your Skydio Cloud Account

Your API access key needs to have the following read-only access permissions: Attachments, Batteries, Flight Telemetry, Flights, JWT Validation, Live Telemetry, OpenAPI Spec, Sensor Package, Users, Vehicles, Webhook Validation, Webhooks, and Whoami.

You can test your API access-level by using the included test script “test\_final\_skydio.py”

You can test your real-time telemetry (websocket) access by using the included test script “websocket\_test.py”

### Your Skydio Drone

It’s not known if one or both of the drone and the controller need a live internet connection, either 5G Cellular or Wifi.

### Your Local System

1. python 3.13.7 or newer  
2. These files: [https://github.com/users/billburns250/projects/1](https://github.com/users/billburns250/projects/1)  
3. These python dependencies (need to confirm these)  
   1. \# Core dependencies  
   2. requests\>=2.31.0  
   3. python-dotenv\>=1.0.0  
   4. \# Time and date handling  
   5. python-dateutil\>=2.8.2  
   6. pytz\>=2023.3  
   7. \# Data processing  
   8. geojson\>=3.1.0  
   9. \# Development and testing  
   10. pytest\>=7.4.0  
   11. pytest-cov\>=4.1.0  
   12. black\>=23.9.1  
   13. flake8\>=6.1.0  
   14. \# For local development and testing  
   15. flask\>=2.3.3
