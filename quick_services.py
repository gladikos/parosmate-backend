# quick_services.py

import os
import requests
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PAROS_LAT = 37.0853
PAROS_LNG = 25.1500

@router.get("/quick_services")
def get_quick_services(type: str = Query(...)):
    if not GOOGLE_API_KEY:
        print("GOOGLE API ERROR:", data)
        raise HTTPException(status_code=500, detail="Missing Google API Key")

    url = (
        "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={PAROS_LAT},{PAROS_LNG}"
        f"&radius=15000"
        f"&type={type}"
        f"&key={GOOGLE_API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    if data.get("status") != "OK":
        print("GOOGLE API ERROR:", data)
        raise HTTPException(status_code=500, detail=data.get("error_message", "Google API Error"))

    places = []

    for place in data.get("results", []):
        place_id = place.get("place_id")

        # Fetch phone number from details endpoint
        phone = None
        try:
            detail_url = (
                f"https://maps.googleapis.com/maps/api/place/details/json"
                f"?place_id={place_id}"
                f"&fields=formatted_phone_number"
                f"&key={GOOGLE_API_KEY}"
            )
            detail_res = requests.get(detail_url)
            if detail_res.ok:
                detail_data = detail_res.json()
                phone = detail_data.get("result", {}).get("formatted_phone_number")
        except Exception as e:
            print(f"Failed to fetch phone for {place_id}: {e}")

        places.append({
            "id": place_id,
            "name": place.get("name"),
            "address": place.get("vicinity"),
            "open_now": place.get("opening_hours", {}).get("open_now"),
            "location": place.get("geometry", {}).get("location"),
            "phone": phone
        })



    return JSONResponse(content=places)
