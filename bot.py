import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from git import Repo
from dotenv import load_dotenv
from flask import Flask
import threading
import asyncio

# ======================
# CONFIGURATION SETUP
# ======================
load_dotenv()  # Load .env file

# Get credentials from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# File paths setup
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(REPO_PATH, "Tempkey.json")
GITHUB_REPO_URL = f"https://{GITHUB_TOKEN}@github.com/WolfT31/Tempkey.git"

# ======================
# FLASK WEB SERVER (For hosting platforms)
# ======================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🔰 Telegram Bot is Active | Status: ONLINE"

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# ======================
# GIT FUNCTIONS (Auto-sync to GitHub)
# ======================
def load_users():
    try:
        with open(JSON_FILE, 'r') as file:
            return json.load(file).get("users", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def git_sync(commit_msg="Updated user data"):
    try:
        repo = Repo(REPO_PATH)
        repo.git.add(JSON_FILE)
        repo.index.commit(commit_msg)
        origin = repo.remote(name='origin')
        origin.push()
        print("✅ Changes synced to GitHub")
    except Exception as e:
        print(f"⚠️ Git Error: {e}")
        # Initialize repo if doesn't exist
        if "GitCommandNotFound" in str(e):
            repo = Repo.init(REPO_PATH)
            origin = repo.create_remote('origin', GITHUB_REPO_URL)
            git_sync("Initial commit")

def save_users(users):
    with open(JSON_FILE, 'w') as file:
        json.dump({"users": users}, file, indent=4)
    git_sync()  # Auto-commit after save

# ======================
# TELEGRAM BOT COMMANDS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌟 Welcome! Use:\n"
        "/add <id>,<user>,<pass>,<expire>,<offline>\n"
        "/remove <id>\n"
        "/check <id>\n"
        "/list"
    )

async def add_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Admin Only")
        return

    try:
        # Parse command
        parts = " ".join(context.args).split(",")
        if len(parts) != 5:
            raise ValueError("Format: /add id,user,pass,YYYY-MM-DD,true/false")
        
        device_id, username, password, expire, allow_offline = [p.strip() for p in parts]
        allow_offline = allow_offline.lower() == "true"
        datetime.strptime(expire, "%Y-%m-%d")  # Validate date

        # Add new user
        users = load_users()
        if any(u["id"] == device_id for u in users):
            await update.message.reply_text("⚠️ ID Exists")
            return

        users.append({
            "id": device_id,
            "username": username,
            "password": password,
            "expire": expire,
            "allowoffline": allow_offline
        })
        save_users(users)

        await update.message.reply_text(
            f"✅ Added Successfully!\n"
            f"ID: {device_id}\nUser: {username}\n"
            f"Exp: {expire}\nOffline: {'Yes' if allow_offline else 'No'}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# (Include your other commands: remove_id, check_id, list_ids here with similar improvements)

# ======================
# BOT SETUP & STARTUP
# ======================
async def run_bot():
    # Initialize files if missing
    if not os.path.exists(JSON_FILE):
        save_users([])
    
    # Setup bot commands
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_id))
    # Add other handlers here...

    print("🤖 Bot Started")
    await app.run_polling()

if __name__ == "__main__":
    # Start Flask web server in background
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Run bot with error handling
    try:
        asyncio.run(run_bot())
    except Exception as e:
        print(f"🔴 Bot crashed: {e}")
