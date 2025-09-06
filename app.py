from flask import Flask, render_template, request, jsonify, session
import datetime
import os
import socket
import platform
import wikipedia
import requests
import json
import random
import difflib
from bs4 import BeautifulSoup
from urllib.parse import quote_plus


# --- Flask app ---
app = Flask(__name__)
app.secret_key = os.urandom(24)  # session handling

# --- Smalltalk responses ---
smalltalk_responses = {
    "hello": ["Hi there 👋🏽", "Hello! How’s your day going?", "Hey! 🙂", "Yo! What’s up?", "Greetings 🌿", "Hi hi 😁"],
    "hii": ["Whats Up 😃", "Hello! How’s your day going? 😎", "Hey! 🙂"],
    "i am": ["That’s Great😃", "Really 😃"],
    "how are you": ["I’m doing great, thanks for asking! 💫", "All good here 😄", "Feeling awesome today 🚀"],
    "what is your name": ["I’m Mini magna 🤎", "They call me Mini magna 🌿"],
    "who are you": ["I'm Zana your Property process assistant 🙂", "I’m Zana 🪴 Nice to meet you"],
    "who created you": ["🥳 Hamilton Mwangi 🎊"],
    "who is your creator": ["🥳 Hamilton Mwangi 🎊"],
    "what can you do": ["Tell time ⏰, date 📅, search videos on YouTube 🎵, help with property registration 🏡 and verification 📝"],
    "thank you": ["Anytime 🤗", "You’re most welcome 💯", "No worries! 😎", "Happy to help 🌸", "Glad I could assist 😄"],
    "good morning": ["Morning 🌞", "Rise and shine ✨", "Top of the morning to you ☕", "Good vibes only today 😁"],
    "good night": ["Good night 🌙", "Sweet dreams ✨", "Sleep well 😴", "Catch you tomorrow 🌌"],
    "bye": ["See you later 👋🏽", "Take care 🌿", "Goodbye for now ✨", "Catch you soon 🚀"],
    "lol": ["😂", "🤣 You got me", "That’s funny 😅", "Haha, true one!"],
    "bored": ["Want me to tell you something random? 🤔", "We could play 20 questions 🎲", "How about a fun fact? 📚"],
    "fun fact": ["Did you know? Honey never spoils 🍯", "Octopuses have three hearts 🐙", "Bananas are berries, but strawberries aren’t 🍌🍓"],
    "weather": ["I’m not a weather app, but I bet it’s sunny somewhere 🌞", "Rain or shine, I’m here 🌧🌞"],
    "joke": [
        "Why don’t skeletons fight? They don’t have the guts 😂",
        "Parallel lines have so much in common… too bad they’ll never meet 😅",
        "Why did the computer go to the doctor? It caught a virus 🤖🤒"
    ]
}

# --- Simple preference profile ---
PROFILE_FILE = "user_profile.json"

def load_profile():
    try:
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"tone": "friendly", "depth": "detailed", "likes_emojis": True, "topics": {}}

def save_profile(profile):
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=4)

def update_profile(user_input):
    profile = load_profile()
    ul = user_input.lower()
    if "analytical" in ul: profile["tone"] = "analytical"
    elif "friendly" in ul: profile["tone"] = "friendly"
    elif "playful" in ul: profile["tone"] = "playful"
    if "no emoji" in ul: profile["likes_emojis"] = False
    elif "use emoji" in ul: profile["likes_emojis"] = True
    save_profile(profile)

# --- Smalltalk (with fuzzy) ---
def get_smalltalk_response(user_message):
    m = user_message.lower().strip()
    if m in smalltalk_responses:
        return random.choice(smalltalk_responses[m])
    closest = difflib.get_close_matches(m, smalltalk_responses.keys(), n=1, cutoff=0.6)
    if closest:
        return random.choice(smalltalk_responses[closest[0]])
    return None

# --- Utility commands ---
def magna_time(profile):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    tone = profile.get("tone", "friendly")
    if tone == "friendly": return f"⏰ It’s {now}, hope you’re doing great 😄"
    if tone == "analytical": return f"System time: {now}"
    return f"Tick-tock ⏰—it’s {now} 😏"

def magna_date(profile):
    today = datetime.datetime.now().strftime("%A, %d %B %Y")
    tone = profile.get("tone", "friendly")
    use_emojis = profile.get("likes_emojis", True)
    if tone == "playful": return f"📅 Drum roll… it’s {today}! 🎉" if use_emojis else f"It’s {today}!"
    if tone == "analytical": return f"Date: {today}"
    return f"📅 Today is {today}" if use_emojis else f"Today is {today}"

def magna_system_info():
    user_name = None
    try:
        user_name = os.getlogin()
    except Exception:
        user_name = "unknown"
    return f"System: {platform.system()} {platform.release()} | User: {user_name}"

def magna_open_file(user_input):
    # Windows-only helper scanning a Desktop path (adjust to your machine)
    triggers = ["open file", "launch file", "start file"]
    if any(t in user_input.lower() for t in triggers):
        filename = user_input
        for t in triggers: filename = filename.replace(t, "").strip()
        search_root = os.path.expanduser("~/Desktop")
        for root, _, files in os.walk(search_root):
            for f in files:
                if filename.lower() == f.lower():
                    try:
                        os.startfile(os.path.join(root, f))
                        return f"Opening {f}..."
                    except Exception:
                        return "Couldn’t open that file on this system."
        return "File not found!"
    return None

# --- Music / YouTube embed ---
def rava_play_song(song):
    if song:
        query = quote_plus(song)
        embed_url = f"https://www.youtube.com/embed?listType=search&list={query}&autoplay=1"
        return {
            "type": "video",
            "message": f"Playing '{song}' 🎵",
            "url": embed_url
        }
    return {"type": "text", "message": "Please tell me the name of the song to play."}
    
# --- Wikipedia / Google quick lookups ---
def rava_lookup(query, profile):
    responses = []

    # Google
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        response = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(response.text, "html.parser")
        el = soup.find("div", class_="BNeawe")
        snippet = el.text.strip() if el else None
        if snippet:
            responses.append(format_lookup_response("google", query, snippet, profile))
    except Exception:
        responses.append("⚠ Google search failed.")

    # Wikipedia
    try:
        summary = wikipedia.summary(query, sentences=2, auto_suggest=True, redirect=True)
        responses.append(format_lookup_response("wikipedia", query, summary, profile))
    except wikipedia.DisambiguationError as e:
        options = ", ".join(e.options[:5])
        responses.append(f"Wikipedia has multiple entries for {query}: {options}")
    except wikipedia.PageError:
        responses.append(f"Wikipedia has no page for '{query}' 😅")
    except Exception:
        responses.append("⚠ Wikipedia lookup failed.")

    return "\n\n".join(responses)

search_state = {}

def rava_search_flow(user_message, user_id="4"):
    profile = load_profile()

    # Cancel flow
    if user_message.strip().lower() in ["cancel", "exit", "stop"]:
        search_state.pop(user_id, None)
        return "❌ Search cancelled."

    state = search_state.get(user_id, {"step": None})

    # Step 1: trigger
    if state["step"] is None:
        if user_message.lower() != "search":
            return None
        state["step"] = "query"
        search_state[user_id] = state
        return "🔎 What would you like me to search?"

    # Step 2: handle query
    if state["step"] == "query":
        query = user_message.strip()
        if not query:
            return "Please type something to search 🙂"
        # Do combined lookup
        result = rava_lookup(query, profile)
        search_state.pop(user_id, None)
        return result

def format_lookup_response(source, query, text, profile):
    """Format responses naturally depending on tone + source."""
    tone = profile.get("tone", "friendly")
    use_emojis = profile.get("likes_emojis", True)

    if source == "google":
        if tone == "playful":
            return f"🔎 Google says this about {query}: {text} 😏" if use_emojis else f"Google says: {text}"
        elif tone == "analytical":
            return f"📊 From Google search on '{query}': {text}"
        else:
            return f"I looked it up on Google: {text}" + (" 🌐" if use_emojis else "")

    elif source == "wikipedia":
        if tone == "playful":
            return f"✨ Fun fact about {query}: {text} 😉" if use_emojis else f"Fun fact about {query}: {text}"
        elif tone == "analytical":
            return f"📖 According to Wikipedia, here’s the summary on '{query}': {text}"
        else:
            return f"Here’s what I found on {query}: {text}" + (" 🌿" if use_emojis else "")

    return text

# --- Property flows (state machines) ---
registration_state = {}
verification_state = {}
deed_state = {}

def magna_register_property(user_message, user_id="1"):
    # cancel
    if user_message.strip().lower() in ["cancel", "exit", "stop"]:
        registration_state.pop(user_id, None)
        return "❌ Current Registration session cancelled."

    state = registration_state.get(user_id, {"step": None, "data": {}})
    # trigger
    if state["step"] is None:
        if user_message.lower() != "register property":
            return "Command not recognized. Try 'register property'."
        state["step"] = "parcel"
        registration_state[user_id] = state
        return "Enter Parcel Number:"

    if state["step"] == "parcel":
        if not user_message.strip():
            return "Parcel number is required. Enter Parcel Number:"
        state["data"]["parcel_number"] = user_message.strip()
        state["step"] = "title"
        registration_state[user_id] = state
        return "Enter Title Deed Number:"

    if state["step"] == "title":
        if not user_message.strip():
            return "Title deed is required. Enter Title Deed Number:"
        state["data"]["title_deed"] = user_message.strip()
        state["step"] = "email"
        registration_state[user_id] = state
        return "Enter Email for Alerts:"

    if state["step"] == "email":
        if not user_message.strip():
            return "Email is required. Enter Email:"
        state["data"]["email"] = user_message.strip()
        state["step"] = "phone"
        registration_state[user_id] = state
        return "Enter Phone for SMS Alerts (optional):"

    if state["step"] == "phone":
        state["data"]["phone"] = user_message.strip() if user_message.strip() else None
        registration_state.pop(user_id, None)
        data = state["data"]
        return f"✅ Property registered successfully:\n- Parcel: {data['parcel_number']}\n- Title: {data['title_deed']}\n- Email: {data['email']}\n- Phone: {data['phone'] or '—'}"

def magna_verify_land(user_message, user_id="2"):
    if user_message.strip().lower() in ["cancel", "exit", "stop"]:
        verification_state.pop(user_id, None)
        return "❌ Current verification session cancelled."

    verify_cmds = ["confirm", "for sale", "verify", "verification", "verify land", "land verification"]
    state = verification_state.get(user_id, {"step": None, "data": {}})

    if state["step"] is None:
        if user_message.lower() not in [c.lower() for c in verify_cmds]:
            return "Command not recognized. Try 'verify land'."
        state["step"] = "parcel"
        verification_state[user_id] = state
        return "Enter Parcel Number:"

    if state["step"] == "parcel":
        if not user_message.strip():
            return "Parcel number is required. Exiting verification."
        state["data"]["parcel_number"] = user_message.strip()
        state["step"] = "owner"
        verification_state[user_id] = state
        return "Enter Owner Name (Optional, press Enter to skip):"

    if state["step"] == "owner":
        owner_name = user_message.strip() if user_message.strip() else None
        state["data"]["owner_name"] = owner_name
        state["step"] = "location"
        verification_state[user_id] = state
        return "Enter Location (Nairobi, Mombasa, Kisumu, Nakuru):"

    if state["step"] == "location":
        loc = user_message.strip().lower()
        valid = ["nairobi", "mombasa", "kisumu", "nakuru"]
        if loc not in valid:
            return f"Invalid location. Choose from: {', '.join(valid)}"
        state["data"]["location"] = loc
        state["step"] = "method"
        verification_state[user_id] = state
        return "Choose Verification Method: 'quick' (Free) or 'detailed' (KSH 500):"

    if state["step"] == "method":
        method = user_message.strip().lower()
        if method not in ["quick", "detailed"]:
            return "Invalid method. Enter 'quick' or 'detailed'."
        state["data"]["verification_method"] = method
        state["step"] = "terms"
        verification_state[user_id] = state
        return "Do you agree to the terms and conditions? (yes/no)"

    if state["step"] == "terms":
        ans = user_message.strip().lower()
        if ans not in ["yes", "y"]:
            verification_state.pop(user_id, None)
            return "You must agree to the terms. Verification canceled."
        verification_state.pop(user_id, None)
        return f"✅ Land verification submitted successfully:\n{state['data']}"

def magna_deed_search(user_message, user_id="3"):
    if user_id not in deed_state:
        deed_state[user_id] = {"step": None, "data": {}}

    # start
    state = deed_state[user_id]
    if state["step"] is None:
        state["step"] = "number"
        return "Enter Title Deed Number (e.g., TN12345678):"

    if state["step"] == "number":
        deed_number = user_message.strip().upper()
        if deed_number.lower() in ["cancel", "exit", "stop"]:
            deed_state.pop(user_id, None)
            return "❌ Current session cancelled."
        if not deed_number.startswith("TN") or not deed_number[2:].isdigit() or len(deed_number) != 10:
            return "❌ Invalid Title Deed Number. Format: TN12345678"
        state["data"]["deed_number"] = deed_number
        state["step"] = "location"
        return "Enter Location (Nairobi, Mombasa, Kisumu, Nakuru):"

    if state["step"] == "location":
        loc = user_message.strip().lower()
        valid = ["nairobi", "mombasa", "kisumu", "nakuru"]
        if loc not in valid:
            return f"❌ Invalid location. Choose from: {', '.join(valid)}"
        state["data"]["location"] = loc
        state["step"] = "purpose"
        return "Enter Purpose of Search (purchase, loan, legal, other):"

    if state["step"] == "purpose":
        purpose = user_message.strip().lower()
        valid = ["purchase", "loan", "legal", "other"]
        if purpose not in valid:
            return f"❌ Invalid purpose. Choose from: {', '.join(valid)}"
        state["data"]["purpose"] = purpose
        deed_state.pop(user_id, None)
        d = state["data"]
        return f"✅ Title Deed Search Completed:\n- Number: {d['deed_number']}\n- Location: {d['location'].title()}\n- Purpose: {d['purpose'].title()}"

# --- Main response router (when not in a flow) ---
def base_response(user_input):
    profile = load_profile()
    update_profile(user_input)

    # Smalltalk
    st = get_smalltalk_response(user_input)
    if st: return st

    ul = user_input.lower()

    # Utility commands
    if "time" in ul: return magna_time(profile)
    if "date" in ul: return magna_date(profile)
    if "system info" in ul: return magna_system_info()
    if any(w in ul for w in ["open file", "launch file", "start file"]):
        return magna_open_file(user_input)
    if ul.startswith("wiki"):
        return magna_wikipedia_search(ul.replace("wiki", "", 1).strip(), profile)
    if ul.startswith("google"):
        return magna_google_search(ul.replace("google", "", 1).strip(), profile)

    return "Hmm 🤔 I’m still learning. Try a command like 'time', 'date', 'register property', 'verify land', 'deed search', 'play'."

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = (data.get("message") or "").strip()

    # --- Global cancel clears flows ---
    if user_message.lower() in ["cancel", "exit", "stop"]:
        registration_state.clear()
        verification_state.clear()
        deed_state.clear()
        session["play_mode"] = False
        return jsonify({"type": "text", "message": "All clear 👍🏻"})

    # --- Initialize play mode ---
    if "play_mode" not in session:
        session["play_mode"] = False

    # --- Continue flows first ---
    if "1" in registration_state and registration_state["1"].get("step"):
        return jsonify({"type": "text", "message": magna_register_property(user_message, user_id="1")})
    if "2" in verification_state and verification_state["2"].get("step"):
        return jsonify({"type": "text", "message": magna_verify_land(user_message, user_id="2")})
    if "3" in deed_state and deed_state["3"].get("step"):
        return jsonify({"type": "text", "message": magna_deed_search(user_message, user_id="3")})
    if "4" in search_state and search_state["4"].get("step"):
        return jsonify({"type": "text", "message": rava_search_flow(user_message, user_id="4")})       

    # --- Start new flows ---
    if user_message.lower() == "register property":
        registration_state["1"] = {"step": None, "data": {}}
        return jsonify({"type": "text", "message": magna_register_property(user_message, user_id="1")})
    if user_message.lower() in ["verify land", "verify", "verification"]:
        verification_state["2"] = {"step": None, "data": {}}
        return jsonify({"type": "text", "message": magna_verify_land(user_message, user_id="2")})
    if user_message.lower() == "deed search":
        deed_state["3"] = {"step": None, "data": {}}
        return jsonify({"type": "text", "message": magna_deed_search(user_message, user_id="3")})
    if user_message.lower() == "search":
        search_state["4"] = {"step": None}
        return jsonify({"type": "text", "message": rava_search_flow(user_message, user_id="4")})

    # --- Play mode trigger ---
    if user_message.lower() == "play":
        session["play_mode"] = True
        suggestions = ["Shape of You", "Blinding Lights", "Levitating", "Someone You Loved"]
        return jsonify({
            "type": "text",
            "message": f"🎵 Please tell me the name of the song to play. Here are some suggestions: {', '.join(suggestions)}"
        })

    # --- Play mode active (song) ---
    if session["play_mode"]:
        song = user_message
        session["play_mode"] = False
        return jsonify(rava_play_song(song))

    # --- Base response ---
    reply_text = base_response(user_message)
    if isinstance(reply_text, dict):
        return jsonify(reply_text)
    return jsonify({"type": "text", "message": reply_text})

if __name__ == "__main__":
    app.run(debug=True)