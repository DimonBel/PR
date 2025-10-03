#!/bin/bash

# Function to get the LAN IP of the Wi-Fi / Ethernet interface
get_local_ip() {
    # Look for interfaces starting with wlp or eno (Wi-Fi/Ethernet), ignore docker/tailscale/lo
    ifconfig | awk '/^(wlp|eno)/ {iface=$1} /inet / && iface ~ /^(wlp|eno)/ {
        ip=$2; if(ip ~ /^192\.168\.|^10\.|^172\.(1[6-9]|2[0-9]|3[0-1])\./) {print ip; exit}
    }'
}

# Get the local IP
LOCAL_IP=$(get_local_ip)

if [ -z "$LOCAL_IP" ]; then
    echo "Error: Could not detect local network IP."
    echo "Please ensure you're connected to a Wi-Fi network."
    echo "You can manually set the IP by editing this script (e.g., LOCAL_IP='192.168.0.80')."
    echo "Current interfaces:"
    ifconfig | grep inet
    exit 1
fi

# Start Docker Compose in detached mode
echo "Starting Docker Compose services..."
docker-compose up -d

# Wait briefly to ensure services are up
sleep 2

# Display URLs
echo -e "\nFile servers are running!"
echo "Main Server:"
echo "  Local: http://localhost:1111"
echo "  Network: http://$LOCAL_IP:1111"
echo "Friend's Server:"
echo "  Local: http://localhost:1112"
echo "  Network: http://$LOCAL_IP:1112"
echo -e "\nAccess these URLs from your phone or other devices on the same Wi-Fi network."
echo "Press Ctrl+C to stop the servers."
echo "Logs can be viewed with: docker-compose logs -f"

# Keep the script running to show logs
docker-compose logs -f
