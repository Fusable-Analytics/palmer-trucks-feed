import requests
import urllib3

# Disable warnings for verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Endpoint
url = "https://prod-palmertrucks-inventory-ws-ti0xfp.5sc6y6-4.usa-e2.cloudhub.io/api/inventory"

# Match headers exactly as shown in Postman
headers = {
    "client_id": "8d6377ba1b17482393c269defe61da54",
    "client_secret": "736cfa551eA1495bba3a0020A604dfF7",
    "Accept": "application/json"
}

# Send request
print("📡 Requesting inventory...")
response = requests.get(url, headers=headers, verify=False)

# Output
print(f"Status Code: {response.status_code}")
print(response.text[:1000])  # First 1000 characters
