import csv
import requests
import urllib3

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
    print("❌ Failed to fetch data.")
    print(f"📄 API response body: {response.text[:2000]}")
    print("🛑 Exiting without creating candidate feed.")
    raise SystemExit(1)

print("✅ API fetch succeeded.")

data = response.json()
print(f"🔎 Inventory items received: {len(data)}")

if not data:
    print("⚠️ No inventory returned from API. Exiting.")
    raise SystemExit(1)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def get_key_ci(data, target_key):
    for key in data:
        if key.strip().lower() == target_key.strip().lower():
            return data[key]
    return None


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_google_description(text):
    """
    Normalize descriptions that are effectively ALL CAPS for Google Ads.
    Normal mixed-case descriptions are returned unchanged.
    """
    text = clean(text)

    if not text:
        return ""

    letters = [c for c in text if c.isalpha()]

    if not letters:
        return text

    uppercase_ratio = sum(c.isupper() for c in letters) / len(letters)

    # Only intervene when the description is overwhelmingly uppercase.
    if uppercase_ratio >= 0.90:
        text = text.lower()
        text = text[:1].upper() + text[1:]

        # Preserve known brands and common inventory acronyms.
        replacements = {
            "thermo king": "Thermo King",
            "espar": "Espar",
            "apu": "APU",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

    return text


def add_keyword(keywords, value):
    value = clean(value)

    if value and value.lower() not in {
        keyword.lower() for keyword in keywords
    }:
        keywords.append(value)

# ---------------------------------------------------------
# Palmer location lookup
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Google Business Data schema
# ---------------------------------------------------------

fieldnames = [
    "ID",
    "ID2",
    "Final URL",
    "Image URL",
    "Item title",
    "Item subtitle",
    "Item description",
    "Item address",
    "Item category",
    "Price",
    "Formatted price",
    "Sale price",
    "Formatted sale price",
    "Contextual keywords",
    "Tracking template",
    "Android app link",
    "iOS app link",
    "iOS app store ID",
    "Similar IDs",
    "Status"
]


rows = []
on_hold_count = 0
missing_identity_count = 0
unknown_location_count = 0


# ---------------------------------------------------------
# Build Google rows
# ---------------------------------------------------------

for item in data:
    general = item.get("General-Details", {}) or {}
    power = item.get("Power", {}) or {}

    status = clean(get_key_ci(general, "Status"))

    # Google feed contains Available inventory only.
    if status.lower() != "available":
        on_hold_count += 1
        continue

    location = clean(get_key_ci(general, "Location"))
    stock_number = clean(get_key_ci(general, "Stock-Number"))
    year = clean(get_key_ci(general, "Year"))
    make = clean(get_key_ci(general, "Make"))
    model = clean(get_key_ci(general, "Model"))
    vin = clean(get_key_ci(general, "VIN"))
    condition = clean(get_key_ci(general, "Condition"))
    category = clean(get_key_ci(general, "Category"))
    sub_category = clean(get_key_ci(general, "Sub-Category"))
    vehicle_class = clean(get_key_ci(general, "Class"))

    website_application = clean(item.get("Website-Application"))
    unit_type = clean(item.get("Unit-Type"))
    additional_info = clean(item.get("Additional-Information"))
    price = item.get("Price")
    image_urls = item.get("ImageURLS", []) or []

    engine = clean(power.get("Engine"))
    engine_make = clean(power.get("Type-of-Engine"))
    horsepower = clean(power.get("HP-HorsePower"))
    transmission_type = clean(power.get("Transmission-Type"))
    fuel_type = clean(power.get("Fuel-Type"))

    # Identity fields required by our feed architecture.
    if not all([stock_number, vin, year, make, model]):
        print(
            f"⚠️ Skipping missing identity fields: "
            f"{stock_number or vin or '[unknown]'}"
        )
        missing_identity_count += 1
        continue

    # Preserve the same Palmer detail URL logic used by Meta.
    final_url = (
        "https://www.palmertrucks.com/truck-details/"
        f"category-{category.replace(' ', '-')}/"
        f"make-{make}/model-{model}/vin-{vin}/"
    )

    # Google-facing category:
    # Palmer Website Application first, raw Category as fallback.
    item_category = website_application or category

    # First image only for Google Business Data.
    image_url = clean(image_urls[0]) if image_urls else ""

    # Price is optional here.
    google_price = ""
    if price not in (None, ""):
        try:
            google_price = f"{float(price):.2f} USD"
        except (TypeError, ValueError):
            print(
                f"⚠️ Invalid price for {stock_number}: {price}"
            )

    # Location/address is enrichment rather than an eligibility gate.
    item_address = ""

    if location in location_lookup:
        addr = location_lookup[location]
        item_address = ", ".join(
            part for part in addr if clean(part)
        )
    elif location:
        print(
            f"⚠️ Unknown location for {stock_number}: {location}"
        )
        unknown_location_count += 1

    # Basic display fields.
    item_title = f"{year} {make} {model}"

    subtitle_parts = [
        value for value in [condition, item_category]
        if value
    ]
    item_subtitle = " | ".join(subtitle_parts)

    # Description:
    # Prefer Palmer's authored description when available.
    # Otherwise construct a useful description from structured data.
    if additional_info:
        item_description = normalize_google_description(additional_info)
    else:
        description_parts = []

        if condition:
            description_parts.append(condition)

        description_parts.append(
            f"{year} {make} {model}"
        )

        if item_category:
            description_parts.append(item_category)

        if engine:
            description_parts.append(engine)
        elif engine_make:
            description_parts.append(engine_make)

        if horsepower:
            description_parts.append(f"{horsepower} HP")

        if transmission_type:
            description_parts.append(transmission_type)

        if fuel_type:
            description_parts.append(fuel_type)

        item_description = ", ".join(
            part for part in description_parts if part
        )

    # Contextual keywords:
    # Populate useful structured metadata now.
    # Campaigns do not have to use it.
    keywords = []

    for value in [
        website_application,
        category,
        sub_category,
        unit_type,
        condition,
        make,
        model,
        f"Class {vehicle_class}" if vehicle_class else "",
        fuel_type,
        transmission_type,
        engine_make,
        engine
    ]:
        add_keyword(keywords, value)

    contextual_keywords = "; ".join(keywords)

    rows.append({
        "ID": stock_number,
        "ID2": "",
        "Final URL": final_url,
        "Image URL": image_url,
        "Item title": item_title,
        "Item subtitle": item_subtitle,
        "Item description": item_description,
        "Item address": item_address,
        "Item category": item_category,
        "Price": google_price,
        "Formatted price": "",
        "Sale price": "",
        "Formatted sale price": "",
        "Contextual keywords": contextual_keywords,
        "Tracking template": "",
        "Android app link": "",
        "iOS app link": "",
        "iOS app store ID": "",
        "Similar IDs": "",
        "Status": "Eligible"
    })


# ---------------------------------------------------------
# Write candidate CSV
# ---------------------------------------------------------

OUT_CANDIDATE = "google_ads_feed_new.csv"

with open(
    OUT_CANDIDATE,
    "w",
    newline="",
    encoding="utf-8-sig"
) as csvfile:
    writer = csv.DictWriter(
        csvfile,
        fieldnames=fieldnames,
        quoting=csv.QUOTE_MINIMAL
    )

    writer.writeheader()
    writer.writerows(rows)


print(f"✅ Google Ads feed created (candidate): {OUT_CANDIDATE}")
print(f"📦 Google feed rows: {len(rows)}")
print(f"⏸️ On Hold excluded: {on_hold_count}")

if missing_identity_count:
    print(
        f"⚠️ Missing identity fields excluded: "
        f"{missing_identity_count}"
    )

if unknown_location_count:
    print(
        f"⚠️ Available listings with unknown location: "
        f"{unknown_location_count}"
    )