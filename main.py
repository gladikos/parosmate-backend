from fastapi import FastAPI, UploadFile, File, Form, APIRouter
from pydantic import BaseModel
import os
import requests
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scrape_ktel import update_knowledge_file_basic_summary
from pathlib import Path

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
router = APIRouter()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_paros_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY")  # Make sure it's in your .env file
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Paros,GR&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("cod") != 200:
            return None
        weather = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        return f"The current weather in Paros is {weather} with a temperature of {temp}°C."
    except Exception as e:
        return "Weather information is currently unavailable."


class Query(BaseModel):
    question: str

@app.post("/ask")
async def ask_question(question: str = Form(...), file: UploadFile = File(None)):
    print(f"Received question: {question}")
    file_text = ""

    if file:
        contents = await file.read()
        print(f"Received file: {file.filename}, size: {len(contents)} bytes")
        file_text = contents.decode("utf-8", errors="ignore")[:1000]  # limit for prompt

        # Optional: Save the file for debugging
        with open(f"uploaded_{file.filename}", "wb") as f:
            f.write(contents)

    try:
        BASE_DIR = Path(__file__).resolve().parent
        KNOWLEDGE_PATH = BASE_DIR / "paros_knowledge.txt"

        print(f"🟡 Checking for knowledge file at: {KNOWLEDGE_PATH}")
        print(f"📂 Directory contents: {[p.name for p in BASE_DIR.iterdir()]}")
        print(f"📄 File exists? {KNOWLEDGE_PATH.exists()}")
        with open("paros_knowledge.txt", "r", encoding="utf-8") as f:
            paros_knowledge = f.read()[:10000]  # limit for prompt size
    except FileNotFoundError:
        paros_knowledge = ""

    # Construct the prompt
    prompt = f"{question}"
    # Detect weather-related question
    if "weather" in question.lower():
        weather_info = get_paros_weather()
        if weather_info:
            return JSONResponse(content={"answer": weather_info})
    if file_text:
        prompt += f"\n\nThe user also uploaded a file with the following contents:\n{file_text}"

    # system_prompt = "You are ParosGPT, an assistant specialized in the island of Paros, Greece."
    # if paros_knowledge:
    #     system_prompt += f"\nUse the following knowledge base to answer questions when possible:\n{paros_knowledge}"

    # Construct prompt to prioritize knowledge
    system_prompt = (
        "You are a friendly, hyper-local, expert travel assistant named ParosGPT for the island of Paros, Greece. "
        "Always answer based on the information provided below. "
        "Use a fun but professional tone. "
        "If the provided content doesn't include the answer, you may use general knowledge.\n\n"
        f"{paros_knowledge}"
    )

    # Send to GPT
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        # model="gpt-4o",
        messages=[
            {
                "role": "system", 
                "content": system_prompt
            },
            {"role": "user", "content": prompt}
        ]
    )

    answer = response.choices[0].message.content.strip()
    return JSONResponse(content={"answer": answer})

class ItineraryRequest(BaseModel):
    firstName: str
    lastName: str
    arrivalDate: str
    departureDate: str
    numPeople: int
    travelType: str
    pace: str
    accessibility: str
    interests: str

@app.post("/generate-itinerary")
async def generate_itinerary(request: ItineraryRequest):
    prompt = (
        f"Create a travel itinerary for a group of {request.numPeople} people. "
        f"The customer's full name is {request.firstName} {request.lastName}. "
        f"They will arrive on {request.arrivalDate} and depart on {request.departureDate}. "
        f"They are traveling as {request.travelType} and prefer a {request.pace} pace. "
        f"They have {request.accessibility} accessibility. "
        f"Their interests include: {request.interests}. "
        f"Please generate a personalized, engaging and practical day-by-day travel itinerary."
        # f"Make sure to start each day exactly like this example: **Day 1 - dd/mm/yyyy."
    )

    response = client.chat.completions.create(
        # model="gpt-3.5-turbo",
        model="gpt-4o",
        messages=[
            {"role": "system", 
             "content": "You are a friendly, hyper-local AI travel concierge named ParosMate."
                        "You only suggest things that exist on the island of Paros, Greece."
                        "Always generate a day-by-day itinerary that includes Morning, Afternoon, and Evening segments."
                        "Always start the day with ### in front of Day, and finish it with :. Keep this consistent."
                        "Prioritize variety, accessibility, and personalization. Highlight local names and special hidden gems."
                        "Use a fun but professional tone. Be concise and practical, not poetic."
            },
            {"role": "user", "content": prompt}
        ]
    )
    print(request.numPeople, request.firstName, request.lastName, request.arrivalDate, request.departureDate, request.travelType, request.pace, request.interests)
    return {"itinerary": response.choices[0].message.content}

@app.post("/map_explorer")
async def map_explorer(activity: str = Form(...)):
    system_prompt = (
        "You are a helpful travel assistant specialized in Paros, Greece. "
        "Given an activity type (like beaches, eating, drinking, etc.), "
        "suggest exactly 10 places in Paros. "
        "Each suggestion must be in the following format, **on its own line**:\n\n"
        "Name - Short description (latitude, longitude)\n\n"
        "Only return the list, no introduction or closing sentence."
    )

    user_prompt = f"Suggest 10 places in Paros for the activity: {activity}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    return {"answer": response.choices[0].message.content}

class ReviewRequest(BaseModel):
    place: str
    type: str

@app.post("/reviews")
async def get_review_summary(data: ReviewRequest):
    prompt = (
        f"You are an expert review summarizer. Summarize user reviews for '{data.place}', a '{data.type}' in Paros, from Google and TripAdvisor.\n\n"
        # "Search for the place and find any information you can from Google and TripAdvisor to summarize them.\n"
        "Return ONLY a JSON object in the following format:\n"
        "{\n"
        '  "pros": ["(explanative phrase)", "(explanative phrase)", "..."],\n'
        '  "cons": ["(explanative phrase)", "(explanative phrase)", "..."],\n'
        '  "rating": float between 0 and 5 coming from TripAdvisor,\n'
        '  "summary": "a short paragraph (5–6 lines) summarizing the above"\n'
        "}\n\n"
        "NO markdown, no comments, no explanations — just the raw JSON object."
    )

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    content = completion.choices[0].message.content.strip()
    print("LLM Output:", content)

    # Try to parse the JSON from GPT
    import json, re
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: remove markdown code block if present
        cleaned = re.sub(r"^```json|```$", "", content, flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)

    return {
        "pros": parsed.get("pros", []),
        "cons": parsed.get("cons", []),
        "summary": parsed.get("summary", ""),
        "rating": round(float(parsed.get("rating", 4.3)), 1)
    }


LAT, LON = 37.084, 25.150

@app.get("/weather/current")
def get_current_weather():
    API_KEY = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
    res = requests.get(url)
    return JSONResponse(content=res.json())

@app.get("/weather/forecast")
def get_forecast_weather():
    API_KEY = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
    res = requests.get(url)
    return JSONResponse(content=res.json())

@app.get("/update_bus_data")
def update_bus_data():
    try:
        update_knowledge_file_basic_summary()
        return {"status": "success", "message": "paros_knowledge.txt updated with latest bus data."}
    except Exception as e:
        return {"status": "error", "message": str(e)}