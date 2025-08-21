import json
import xml.etree.ElementTree as ET
import requests
import urllib3

print("🔧 Script started")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://prod-palmertrucks-inventory-ws-ti0xfp.5sc6y6-4.usa-e2.cloudhub.io/api/inventory"
headers = {
    "client_id": "8d6377ba1b17482393c269defe61da54",
    "client_secret": "736cfa551eA1495bba3a0020A604dfF7",
    "Accept": "application/json"
}

print("📡 Fetching data from API...")
response = requests.get(url, headers=headers, verify=False)

print(f"📥 API response status: {response.status_code}")

if response.status_code != 200:
    print(f"❌ Failed to fetch data. Exiting.")
    exit()
else:
    print("✅ API fetch succeeded.")

data = response.json()
print(f"🔎 Inventory items received: {len(data)}")

if not data:
    print("⚠️ No inventory returned from API. Exiting.")
    exit()


# --- Helper Function for Case-Insensitive Key Lookup ---
def get_key_ci(data, target_key):
    for key in data:
        if key.strip().lower() == target_key.strip().lower():
            return data[key]
    return None

# --- Location Lookup Table ---
location_lookup = {
    "Kenworth of Effingham": ["1010 Outer Belt W.", "Effingham", "IL", "62401", "United States"],
    "Kenworth of Evansville": ["1040 E. Mount Pleasant Rd.", "Evansville", "IN", "47725", "United States"],
    "Kenworth of Fort Wayne": ["3535 Coliseum Blvd W", "Fort Wayne", "IN", "46808", "United States"],
    "TRP of Fort Wayne": ["7006 Ardmore Ave", "Fort Wayne", "IN", "46809", "United States"],
    "Kenworth of Fremont": ["6503 N. Old US 27", "Fremont", "IN", "46737", "United States"],
    "Kenworth of Indianapolis - East": ["9704 E. 30th St.", "Indianapolis", "IN", "46229", "United States"],
    "Kenworth of Indianapolis - West": ["2929 South Holt RD.", "Indianapolis", "IN", "46241", "United States"],
    "Kenworth of Sellersburg": ["1503 Avco Blvd.", "Sellersburg", "IN", "47172", "United States"],
    "Kenworth of Terre Haute": ["6425 East State Road 42", "Terre Haute", "IN", "47803", "United States"],
    "Kenworth of Cincinnati": ["65 Partnership Way", "Cincinnati", "OH", "45241", "United States"],
    "Kenworth of Dayton": ["7740 Center Point 70 Blvd.", "Dayton", "OH", "45424", "United States"],
    "TRP of Greenville": ["5378 Sebring Warner Road", "Greenville", "OH", "45331", "United States"],
    "Kenworth of Bowling Green": ["131 Parker Ave", "Bowling Green", "KY", "42101", "United States"],
    "Kenworth of Louisville": ["4330 Poplar Level Rd", "Louisville", "KY", "40213", "United States"],
    "TRP of Calvert City": ["163 Kennedy Avenue", "Calvert City", "KY", "42029", "United States"],
    "TRP of Northern Kentucky": ["2782 Circleport Drive", "Erlanger", "KY", "41018", "United States"]
}

# --- XML Root ---
root = ET.Element("listings")
ET.SubElement(root, "title").text = "Palmer Trucks Inventory"

skipped_count = 0

for item in data:
    general = item.get("General-Details", {})
    power = item.get("Power", {})

    location = get_key_ci(general, "Location") or ""
    stock_number = get_key_ci(general, "Stock-Number") or ""
    make = get_key_ci(general, "Make") or ""
    model = get_key_ci(general, "Model") or ""
    year = get_key_ci(general, "Year") or ""
    mileage = get_key_ci(general, "Mileage")
    condition = get_key_ci(general, "Condition")
    price = item.get("Price", None)
    category = get_key_ci(general, "Category") or ""
    description = item.get("Additional-Information", "")
    color = get_key_ci(general, "Color") or ""
    vin = get_key_ci(general, "VIN")
    fuel_type_raw = str(power.get("Fuel-Type", "") or "").strip().upper()
    transmission_raw = str(power.get("Transmission-Type", "") or "").strip().upper()

    image_urls = item.get("ImageURLS", [])

    # Normalize fuel type
    if "DIESEL" in fuel_type_raw:
        fuel_type = "DIESEL"
    elif "ELECTRIC" in fuel_type_raw:
        fuel_type = "ELECTRIC"
    elif "GASOLINE" in fuel_type_raw or "PETROL" in fuel_type_raw:
        fuel_type = "GASOLINE"
    elif "HYBRID" in fuel_type_raw:
        fuel_type = "HYBRID"
    else:
        fuel_type = "OTHER"

    # Normalize transmission
    if "AUTOMATIC" in transmission_raw:
        transmission = "AUTOMATIC"
    elif "MANUAL" in transmission_raw:
        transmission = "MANUAL"
    else:
        transmission = "OTHER"

    # Determine state_of_vehicle
    if condition:
        state_of_vehicle = condition.upper()
    elif mileage and float(mileage) > 1000:
        state_of_vehicle = "USED"
    else:
        state_of_vehicle = "NEW"

    # Skip if required fields are missing
    if not (make and model and year and price and image_urls and description and vin):
        print(f"⚠️ Skipping missing required info: {stock_number or '[unknown stock]'}")
        continue

    # VIN fallback URL setup
    vin_url = f"https://www.palmertrucks.com/truck-details/category-{category.replace(' ', '-')}/make-{make}/model-{model}/vin-{vin}/"

    if location not in location_lookup:
        print(f"⚠️ Skipping {vin}, unknown location: {location}")
        print(f"   → {vin_url}")
        skipped_count += 1
        continue

    # --- Begin XML entry ---
    listing = ET.SubElement(root, "listing")

    for idx, img_url in enumerate(image_urls[:21]):
        image = ET.SubElement(listing, "image")
        ET.SubElement(image, "url").text = img_url
        if idx == 0:
            ET.SubElement(image, "tag").text = category

    ET.SubElement(listing, "vehicle_id").text = stock_number or vin
    ET.SubElement(listing, "description").text = description
    ET.SubElement(listing, "url").text = vin_url
    ET.SubElement(listing, "title").text = f"{year} {make} {model}"
    ET.SubElement(listing, "body_style").text = "OTHER" if "trailer" in category.lower() else "TRUCK"
    ET.SubElement(listing, "price").text = f"{float(price):.2f} USD"
    ET.SubElement(listing, "state_of_vehicle").text = state_of_vehicle
    ET.SubElement(listing, "make").text = make
    ET.SubElement(listing, "model").text = model
    ET.SubElement(listing, "year").text = str(year)
    ET.SubElement(listing, "stock_number").text = stock_number
    ET.SubElement(listing, "exterior_color").text = color
    ET.SubElement(listing, "fuel_type").text = fuel_type
    ET.SubElement(listing, "transmission").text = transmission
    ET.SubElement(listing, "vin").text = vin
    ET.SubElement(listing, "trim").text = category

    mileage_elem = ET.SubElement(listing, "mileage")
    ET.SubElement(mileage_elem, "unit").text = "MI"
    ET.SubElement(mileage_elem, "value").text = str(int(float(mileage))) if mileage else "0"

    address = ET.SubElement(listing, "address", format="simple")
    addr_parts = location_lookup.get(location, ["", "", "", "", ""])
    ET.SubElement(address, "component", name="addr1").text = addr_parts[0]
    ET.SubElement(address, "component", name="city").text = addr_parts[1]
    ET.SubElement(address, "component", name="region").text = addr_parts[2]
    ET.SubElement(address, "component", name="postal_code").text = addr_parts[3]
    ET.SubElement(address, "component", name="country").text = addr_parts[4]

# --- Save XML ---
OUT_CANDIDATE = "facebook_catalog_feed_new.xml"  # candidate, not live
ET.ElementTree(root).write(OUT_CANDIDATE, encoding="utf-8", xml_declaration=True)
print(f"✅ XML feed created (candidate): {OUT_CANDIDATE}")

if skipped_count:
    print(f"⚠️ {skipped_count} listings were skipped due to missing location or VIN.")
