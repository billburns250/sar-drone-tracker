Disclosure policy: If you find a security issue, please email bill@SaferFuturesByDesign.com

Safety Considerations: - This software only requires READ-ONLY API level access to Skydio Cloud. It doesn't require ANY API credentials
                       to CalTopo. 
                       - When this software fails, no aircraft, controller or software is impacted -- logging to CalTopo stops.
                       - You should practice least-privilege when configuring your API keys and access levels.
                       - CalTopo has NO AUTHENTICATION for location trackers, so you should not rely on drone telemetry since it may be
                       spoofed or jammed.

Security Update Policy: Security issues reported will be acknowledged within 72 hours. Fixes will be issued in a timely manned, commensurate with the level of severity.

Security Considerations: 
1. CalTopo CONNECT_KEY: Remember that CalTopo DOES NOT ALLOW AUTHENTICATION when position reports are posted. Therefore, the CONNECT_KEY that you set may be visible to others. If it is guessable, for example, a bad actor could inject false position information to CalTopo which would be added to your shared map. A "security through obscurity" approach is the best you can do here, consider adding random characters to your CONNECT_KEY. You cannot add random characters to your DEVICE_ID, because that's based on your Skydio drone serial number.
2. Skydio API Key: You should consider setting the minimum amount of permissions required and the least number of drones that can be queried by this software.
3. Protect your .env file because those credentials could give a bad actor access to your Skydio cloud devices and configuration.

Security Update policy: Security-based updates will be made in a timely manner, commensurate with the level of confirmed severity.

