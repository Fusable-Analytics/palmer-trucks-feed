import json
import csv

# Dealer location lookup with full address parts
location_lookup = {
    "Kenworth of Effingham": {
        "addr1": "1010 Outer Belt W.",
        "city": "Effingham",
        "region": "IL",
        "postal_code": "62401",
        "country": "United States"
    },
    "Kenworth of Evansville": {
        "addr1": "1040 E. Mount Pleasant Rd.",
        "city": "Evansville",
        "region": "IN",
        "postal_code": "47725",
        "country": "United States"
    },
    "Kenworth of Fort Wayne": {
        "addr1": "3535 Coliseum Blvd W",
        "city": "Fort Wayne",
        "region": "IN",
        "postal_code": "46808",
        "country": "United States"
    },
    "TRP of Fort Wayne": {
        "addr1": "7006 Ardmore Ave",
        "city": "Fort Wayne",
        "region": "IN",
        "postal_code": "46809",
        "country": "United States"
    },
    "Kenworth of Fremont": {
        "addr1": "6503 N. Old US 27",
        "city": "Fremont",
        "region": "IN",
        "postal_code": "46737",
        "country": "United States"
    },
    "Kenworth of Indianapolis - East": {
        "addr1": "9704 E. 30th St.",
        "city": "Indianapolis",
        "region": "IN",
        "postal_code": "46229",
        "country": "United States"
    },
    "Kenworth of Indianapolis - West": {
        "addr1": "2929 South Holt RD.",
        "city": "Indianapolis",
        "region": "IN",
        "postal_code": "46241",
        "country": "United States"
    },
    "Kenworth of Sellersburg": {
        "addr1": "1503 Avco Blvd.",
        "city": "Sellersburg",
        "region": "IN",
        "postal_code": "47172",
        "country": "United States"
    },
    "Kenworth of Terre Haute": {
        "addr1": "6425 East State Road 42",
        "city": "Terre Haute",
        "region": "IN",
        "postal_code": "47803",
        "country": "United States"
    },
    "Kenworth of Cincinnati": {
        "addr1": "65 Partnership Way",
        "city": "Cincinnati",
        "region": "OH",
        "postal_code": "45241",
        "country": "United States"
    },
    "Kenworth of Dayton": {
        "addr1": "7740 Center Point 70 Blvd.",
        "city": "Dayton",
        "region": "OH",
        "postal_code": "45424",
        "country": "United States"
    },
    "TRP of Greenville": {
        "addr1": "5378 Sebring Warner Road",
        "city": "Greenville",
        "region": "OH",
        "postal_code": "45331",
        "country": "United States"
    },
    "Kenworth of Bowling Green": {
        "addr1": "131 Parker Ave",
        "city": "Bowling Green",
        "region": "KY",
        "postal_code": "42101",
        "country": "United States"
    },
    "Kenworth of Louisville": {
        "addr1": "4330 Poplar Level Rd",
        "city": "Louisville",
        "region": "KY",
        "postal_code": "40213",
        "country": "United States"
    },
    "TRP of Calvert City": {
        "addr1": "163 Kennedy Avenue",
        "city": "Calvert City",
        "region": "KY",
        "postal_code": "42029",
        "country": "United States"
    },
    "TRP of Northern Kentucky": {
        "addr1": "2782 Circleport Drive",
        "city": "Erlanger",
        "region": "KY",
        "postal_code": "41018",
        "country": "United States"
    }
}

# Load JSON data
with open("response.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Write CSV
with open("facebook_catalog_feed.csv", "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = [
        "vehicle_id",
        "title",
        "description",
        "availability",
        "state_of_vehicle",
        "price",
        "url",
        "image",
        "make",
        "model",
        "year",
        "body_style",
        "mileage.unit",
        "mileage.value",
        "address.addr1",
        "address.city",
        "address.region",
        "address.postal_code",
        "address.country"
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    skipped = []

    for item in data:
        general = item.get("General-Details", {})
        vin = general.get("VIN", "")
        location = general.get("Location", "")
        condition_raw = general.get("Condition")
        mileage = general.get("Mileage")
        stock_number = general.get("Stock-Number", "")
        make = general.get("Make", "")
        model = general.get("Model", "")
        year = general.get("Year", "")
        category = general.get("Category", "")
        description = item.get("Additional-Information", "")
        price_raw = item.get("Price", "")
        image_urls = item.get("ImageURLS", [])
        image_link = image_urls[0] if image_urls else ""

        # Address mapping
        address = location_lookup.get(location)

        # Determine condition
        condition = "USED" if mileage else (condition_raw or "NEW").upper()

        # Determine mileage value and unit
        try:
            mileage_val = int(float(mileage))
        except (ValueError, TypeError):
            mileage_val = 0
        mileage_unit = "MI"

        # Determine body style
        if "trailer" in category.lower():
            body_style = "OTHER"
        else:
            body_style = "TRUCK"

        # Format price
        try:
            price = f"{float(price_raw):.2f} USD"
        except (ValueError, TypeError):
            price = ""

        # Build product page URL
        if vin and make and model and category:
            url = f"https://www.palmertrucks.com/truck-details/category-{category.replace(' ', '-')}/make-{make}/model-{model}/vin-{vin}/"
        else:
            url = ""

        # Build title
        title = f"{year} {make} {model}".strip()

        # Validate required fields
        missing_fields = []
        if not description:
            missing_fields.append("description")
        if not price:
            missing_fields.append("price")
        if not image_link:
            missing_fields.append("image")
        if not address:
            missing_fields.append("address")

        if missing_fields:
            print(f"⚠️ Skipping {vin}, missing: {', '.join(missing_fields)}")
            print(f"🔗 URL: {url}")
            continue

        # Write row
        writer.writerow({
            "vehicle_id": stock_number or vin,
            "title": title,
            "description": description,
            "availability": "AVAILABLE",
            "state_of_vehicle": condition,
            "price": price,
            "url": url,
            "image": image_link,
            "make": make,
            "model": model,
            "year": year,
            "body_style": body_style,
            "mileage.unit": mileage_unit,
            "mileage.value": mileage_val,
            "address.addr1": address["addr1"],
            "address.city": address["city"],
            "address.region": address["region"],
            "address.postal_code": address["postal_code"],
            "address.country": address["country"]
        })

print("✅ Facebook catalog feed generated: facebook_catalog_feed.csv")
