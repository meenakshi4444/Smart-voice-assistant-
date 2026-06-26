import speech_recognition as sr
import webbrowser
import datetime
import pywhatkit as pk
import urllib.parse
import os
import random
import time/
import asyncio
import edge_tts
import pygame
import uuid
import psutil
import sys
import requests
from bs4 import BeautifulSoup
import platform
import tkinter as tk
from threading import Thread
import sqlite3
voice_running = False
voice_thread = None
conn = sqlite3.connect("assistant.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_text TEXT,
    response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP )
""")
conn.commit()
def save_log(user, response):
    cursor.execute(
        "INSERT INTO history (user_text, response) VALUES (?, ?)",
        (user, response)    )
    conn.commit()
import operator as op
import ast
allowed_ops = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv }
def safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op_func = allowed_ops.get(type(node.op))
        if not op_func:
            raise ValueError("Unsupported operator")
        return op_func(
            safe_eval(node.left),
            safe_eval(node.right) )
    raise ValueError("Invalid expression")
try:
    pygame.mixer.init()
except:
    print("Audio device not found")
def listen():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            set_status("Listening...")
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio = r.listen(source, timeout=3, phrase_time_limit=5)
        text = r.recognize_google(audio, language="en-in")
        set_status("Processing...")
        print("You said:", text)
        return text.lower().strip()
    except Exception as e:
        print("Listen error:", e)
        return ""
def solve_math(text):
    try:
        expr = text.lower()
        replacements = {
            "plus": "+",
            "minus": "-",
            "into": "*",
            "x": "*",
            "times": "*",
            "multiply": "*",
            "divided by": "/",
            "divide": "/" }
        for w, s in replacements.items():
            expr = expr.replace(w, s)
        expr = expr.replace("what is", "").strip()
        node = ast.parse(expr, mode="eval").body
        result = safe_eval(node)
        return f"The answer is {result}"
    except:
        return None
def set_status(text):
    if "root" not in globals():
        return  
    def update():
        status_var.set(text)
        if "Listening" in text:
            status_label.config(fg="yellow")
        elif "Speaking" in text:
            status_label.config(fg="cyan")
        elif "Stopped" in text:
            status_label.config(fg="red")
        elif "Typing" in text:
            status_label.config(fg="green")
        elif "Thinking" in text:
            status_label.config(fg="orange")
        else:
            status_label.config(fg="white")
    root.after(0, update)
def open_google(query):
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return "Here are some results from Google"
def speak(text):
    set_status("Speaking...")
    if not isinstance(text, str):
        text = str(text)
    print("Assistant:", text)
    set_status("Idle")
    async def generate():
        filename = f"voice_{uuid.uuid4().hex}.mp3"
        try:
            await edge_tts.Communicate(text, "hi-IN-MadhurNeural").save(filename)
            return filename
        except Exception as e:
            print("TTS Error:", e)
            return None
    filename = None
    try:
        filename = asyncio.run(generate())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        filename = loop.run_until_complete(generate())
    if not filename or not os.path.exists(filename):
        print("Voice generation failed")
        return
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print("Audio playback error:", e)
    try:
        os.remove(filename)
    except:
        pass
def wiki(query):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
        r = requests.get(url).json()
        return r.get("extract", None)
    except:
        return None
def clean_wiki_query(text):
    text = text.lower()
    junk = [
        "what is", "who is", "who made",
        "tell me", "explain", "about" ]
    for w in junk:
        text = text.replace(w, "")
    text = text.replace("and", " ")
    text = text.replace("?", "")
    text = " ".join(text.split()).strip()
    print("CLEANED QUERY =>", text)  # DEBUG
    return " ".join(text.split()).strip()
def get_weather(city):
    if not city:
        webbrowser.open("https://www.google.com/search?q=weather")
        return "Opening weather"
    webbrowser.open(f"https://www.google.com/search?q=weather+{city}")
    return f"Opening weather for {city}"
def clean_weather(text):
    return text.encode("latin1", "ignore").decode("utf-8", "ignore")
def extract_city(text):
    text = text.lower()
    remove_words = [
        "weather", "temperature", "how is",
        "what is", "tell me", "please", "is", "now" ]
    for w in remove_words:
        text = text.replace(w, "")
    text = text.replace("in", " ")
    city = " ".join(text.split()).strip()
    return city if city else None
def open_history_window():
    win = tk.Toplevel(root)
    win.title("Chat History")
    win.geometry("500x500")
    win.configure(bg="#121212")
    text_box = tk.Text(
        win,
        bg="#1e1e1e",
        fg="white",
        font=("Consolas", 10),
        wrap="word")
    text_box.pack(fill="both", expand=True)
    cursor.execute("SELECT user_text, response, timestamp FROM history ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    if not rows:
        text_box.insert(tk.END, "No history found")
        return   # IMPORTANT FIX
    for u, a, t in reversed(rows):
        text_box.insert(tk.END, f"{t}\nYou: {u}\nAssistant: {a}\n\n")
def open_youtube():
    webbrowser.open("https://www.youtube.com")
    return "Opening YouTube"
def detect_intent(text):
    text = text.lower()
    if "weather" in text or "temperature" in text:
        return "weather"
    if any(x in text for x in ["+", "-", "*", "/", "plus", "minus", "times", "divide"]):
        return "math"
    if "open youtube" in text:
        return "open_youtube"
    if "youtube" in text or ("play" in text and "spotify" not in text):
        return "youtube"
    if "spotify" in text:
        return "spotify"
    if "time" in text:
        return "time"
    if "date" in text or "today" in text or "day" in text:
        return "date"
    if "battery" in text or "charge" in text:
        return "battery"
    if any(x in text for x in ["what is", "who is", "who made", "tell me", "explain"]):
        return "wiki"
    if text.startswith("open"):
        return "open_app"
    if "exit" in text or "bye" in text:
        return "exit"
    return "unknown"
def youtube_action(text):
    query = text.replace("play", "").replace("on youtube", "").strip()
    if not query:
        webbrowser.open("https://youtube.com")
        return "Opening YouTube"
    try:
        pk.playonyt(query)
        return f"Playing {query}"
    except:
        webbrowser.open(f"https://youtube.com/results?search_query={query}")
        return f"Searching {query}"
def spotify_action(text):
    query = text.replace("spotify", "").replace("play", "").strip()
    if not query:
        os.system("start spotify")
        return "Opening Spotify"
    q = urllib.parse.quote(query)
    webbrowser.open(f"https://open.spotify.com/search/{q}")
    return f"Searching {query}"
def open_app(text):
    text = text.replace("open", "").strip().lower()
    apps = {
        "notepad": "notepad",
        "calculator": "calc",
        "paint": "mspaint",
        "cmd": "cmd",
        "command prompt": "cmd",
        "file explorer": "explorer",
        "explorer": "explorer",
        "settings": "ms-settings:",
        "control panel": "control",
        "word": r"C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
        "excel": r"C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
        "powerpoint": r"C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
        "chrome": r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", }
    try:
        if text in apps:
            os.startfile(apps[text])
            return f"Opening {text}"
        # fallback: try generic Windows start
        os.system(f"start {text}")
        return f"Trying to open {text}"
    except Exception as e:
        return f"Can't open {text}"
def process(text):
    intent = detect_intent(text)
    print("Intent:", intent)
    response = None
    if intent == "exit":
        speak("Goodbye")
        sys.exit()
    elif intent == "open_app":
        response = open_app(text)
    elif intent == "math":
        response = solve_math(text) or "Invalid math expression"
    elif intent == "date":
        response = datetime.datetime.now().strftime("%A, %d %B %Y")
    elif intent == "time":
        response = datetime.datetime.now().strftime("%I:%M %p")
    elif intent == "battery":
        battery = psutil.sensors_battery()
        response = f"Battery is {battery.percent}%" if battery else "Battery info not available"
    elif intent == "wiki":
        query = clean_wiki_query(text)
        # HARD GUARANTEE CLEAN
        query = query.replace("the ", "").strip()
        query = " ".join(query.split())
        print("FINAL QUERY SENT:", query)
        response = wiki(query)
        if not response:
            response = open_google(query)
        return response
    elif intent == "open_youtube":
        response = open_youtube()
    elif intent == "youtube":
        response = youtube_action(text)
    elif intent == "spotify":
        response = spotify_action(text)
    elif intent == "weather":
        city = extract_city(text)
        response = get_weather(city) if city else "Tell me a city name"
    else:
        response = "I didn't understand that"
    return response
def start_voice():
    global voice_running
    if voice_running:
        return
    voice_running = True
    set_status("Voice ON")
    def loop():
        while voice_running:
            text = listen()
            if not voice_running:
                break
            if not text:
                continue
            response = process(text)
            safe_insert(f"You: {text}")
            safe_insert(f"Assistant: {response}")
            save_log(text, response)
            Thread(target=speak, args=(response,), daemon=True).start()
    Thread(target=loop, daemon=True).start()
def stop_voice():
    global voice_running
    voice_running = False
    set_status("Voice OFF")
    try:
        pygame.mixer.music.stop()
    except:
        pass
    safe_insert("Voice stopped")
def clear_chat():
    output.config(state="normal")
    output.delete(1.0, tk.END)
    output.config(state="disabled")
themes = {
    "dark": {"bg": "#121212", "fg": "white", "box": "#1e1e1e", "button": "#333"},
    "blue": {"bg": "#0f172a", "fg": "#e2e8f0", "box": "#1e293b", "button": "#2563eb"},
    "green": {"bg": "#052e16", "fg": "#d1fae5", "box": "#14532d", "button": "#16a34a"}}
def apply_theme(name):
    theme = themes[name]
    root.configure(bg=theme["bg"])
    header.configure(bg=theme["bg"], fg=theme["fg"])
    chat_frame.configure(bg=theme["bg"])
    input_frame.configure(bg=theme["bg"])
    output.configure(bg=theme["box"], fg=theme["fg"])
    entry.configure(bg=theme["box"], fg=theme["fg"])
    btn_send.configure(bg=theme["button"], fg="white")
    btn_voice.configure(bg=theme["button"], fg="white")
    btn_stop.configure(bg=theme["button"], fg="white")
def safe_insert(text):
    def _insert():
        output.config(state="normal")
        output.insert(tk.END, str(text) + "\n")
        output.see(tk.END)
        output.config(state="disabled")
    root.after(0, _insert)
def handle_text(event=None):
    user_input = entry.get().strip()
    set_status("Typing...")
    if not user_input:
        return
    entry.delete(0, tk.END)
    def task():
        response = process(user_input)
        safe_insert(f"You: {user_input}")
        safe_insert(f"Assistant: {response}")
        save_log(user_input, response)
        speak(response)
    Thread(target=task, daemon=True).start()
root = tk.Tk()
root.title("AI Assistant")
status_var = tk.StringVar(value="Idle")
status_label = tk.Label(
    root,
    textvariable=status_var,
    font=("Segoe UI", 10),
    bg="#121212",
    fg="white" )
status_label.pack()
root.geometry("550x700")
root.configure(bg="#121212")
root.resizable(False, False)
header = tk.Label(
    root,
    text="AI ASSISTANT",
    font=("Segoe UI", 16, "bold"),
    bg="#121212",
    fg="white")
header.pack(pady=10)
chat_frame = tk.Frame(root, bg="#121212")
chat_frame.pack(fill="both", expand=True, padx=10, pady=10)
output = tk.Text(
    chat_frame,
    bg="#1e1e1e",
    fg="white",
    font=("Consolas", 10),
    wrap="word",
    state="disabled",
    bd=0,
    padx=10,
    pady=10 )
output.pack(fill="both", expand=True)
input_frame = tk.Frame(root, bg="#121212")
input_frame.pack(fill="x", padx=10, pady=10)
entry = tk.Entry(
    input_frame,
    font=("Segoe UI", 11),
    bg="#2a2a2a",
    fg="white",
    insertbackground="white",
    relief="flat")
entry.pack(fill="x", expand=True, pady=(0, 8))
entry.bind("<Return>", handle_text)
button_frame = tk.Frame(input_frame, bg="#121212")
button_frame.pack(fill="x")
tk.Button(button_frame, text="Clear", command=clear_chat).pack(side="left")
btn_send = tk.Button(
    button_frame,
    text="Send",
    command=handle_text,
    bg="#3a3a3a",
    fg="white",
    relief="flat",
    padx=10)
btn_send.pack(side="left", padx=3)
btn_history = tk.Button(
    button_frame,
    text="History",
    command=open_history_window,
    bg="#444",
    fg="white",
    relief="flat",
    padx=10)
btn_history.pack(side="left", padx=3)
btn_voice = tk.Button(
    button_frame,
    text="Start Voice",
    command=start_voice,
    bg="#3a3a3a",
    fg="white",
    relief="flat",
    padx=10)
btn_voice.pack(side="left", padx=3)
btn_stop = tk.Button(
    button_frame,
    text="Stop Voice",
    command=stop_voice,
    bg="#3a3a3a",
    fg="white",
    relief="flat",
    padx=10 )
btn_stop.pack(side="left", padx=3)
theme_var = tk.StringVar(value="dark")
theme_menu = tk.OptionMenu(
    button_frame,
    theme_var,
    *themes.keys(),
    command=apply_theme)
theme_menu.pack(side="left", padx=10)
speak("System online")
root.mainloop()