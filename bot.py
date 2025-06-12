# Import required libraries
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

# Load environment variables from .env file
load_dotenv()

# Set up tokens and admin ID from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Set file paths and GitHub repo URL
REPO_PATH = os.path.abspath(os.path.dirname(__file__))
JSON_FILE = os.path.join(REPO_PATH, "Tempkey.json")
GITHUB_REPO_URL = f"https://{GITHUB_TOKEN}@github.com/WolfT31/Tempkey.git"

# ✅ FIXED: Load user list safely
import base64
import requests

# ✅ Save updated user list and push changes to GitHub via API
def save_users(users):
    json_data = json.dumps({"users": users}, indent=2)

    # GitHub Repo Info
    owner = "WolfT31"
    repo = "Tempkey"
    file_path = "Tempkey.json"
    branch = "main"
    token = GITHUB_TOKEN

    # GitHub API endpoint to get file SHA
    get_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Get the SHA of the existing file (needed for updating)
    response = requests.get(get_url, headers=headers)
    if response.status_code != 200:
        print("❌ Failed to get file SHA:", response.text)
        return

    sha = response.json().get("sha")
    if not sha:
        print("❌ SHA not found in response.")
        return

    # Prepare the updated content
    data = {
        "message": "Update Tempkey.json via Telegram bot",
        "content": base64.b64encode(json_data.encode()).decode(),
        "branch": branch,
        "sha": sha
    }

    # Push the update via PUT request
    put_response = requests.put(get_url, headers=headers, json=data)
    if put_response.status_code == 200:
        print("✅ Tempkey.json updated on GitHub.")
    else:
        print("❌ GitHub update failed:", put_response.text)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Send your device ID or use /add /remove /check /list commands."
    )

# /add <id>,<username>,<password>,<expire>,<allowoffline>
async def add_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n`/add <id>,<username>,<password>,<expire>,<allowoffline>`",
            parse_mode="Markdown"
        )
        return

    try:
        data = " ".join(context.args).strip()
        parts = data.split(",")

        if len(parts) != 5:
            raise ValueError("Invalid format. Use: /add <id>,<username>,<password>,<expire>,<allowoffline>")

        device_id, username, password, expire, allowoffline = [p.strip() for p in parts]
        allowoffline = allowoffline.lower() == "true"
        datetime.strptime(expire, "%Y-%m-%d")  # validate date

        users = load_users()
        if any(user["id"] == device_id for user in users):
            await update.message.reply_text("✅ This device ID already exists.")
            return

        users.append({
            "id": device_id,
            "username": username,
            "password": password,
            "expire": expire,
            "allowoffline": allowoffline
        })

        save_users(users)

        await update.message.reply_text(
            f"✅ [Database Operation Success]\n"
            f"🆔 UserID: `{device_id}`\n"
            f"📛 Name: `{username}`\n"
            f"🔕 Password: `{password}`\n"
            f"🆒 Expire: `{expire}`\n"
            f"👨‍💻 AdminID: `{ADMIN_ID}`\n"
            f"📊 Credit: *Coded by Mr Wolf*",
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# /remove <id>
async def remove_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove <device_id>")
        return

    device_id = context.args[0].strip()
    users = load_users()
    new_users = [user for user in users if user["id"] != device_id]

    if len(new_users) == len(users):
        await update.message.reply_text("❌ Device ID not found.")
    else:
        save_users(new_users)
        await update.message.reply_text(f"✅ Device ID `{device_id}` has been removed.")

# /check <id>
async def check_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /check <device_id>")
        return

    device_id = context.args[0].strip()
    users = load_users()

    for user in users:
        if user["id"] == device_id:
            await update.message.reply_text(
                f"✅ Found:\nUsername: {user['username']}\nPassword: {user['password']}\nExpire: {user['expire']}"
            )
            return

    await update.message.reply_text("❌ Device ID is NOT approved.")

# /list
async def list_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    users = load_users()
    if users:
        reply = "📋 Approved Users:\n" + "\n".join(
            [f"{u['id']} - {u['username']} ({u['expire']})" for u in users]
        )
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("No approved IDs yet.")

# Handle plain text
async def handle_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_id = update.message.text.strip()
    users = load_users()

    for user in users:
        if user["id"] == device_id:
            await update.message.reply_text("✅ Your device ID is already approved.")
            return

    await update.message.reply_text("❌ Your device ID is not approved.")

# Bot logic
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_id))
    app.add_handler(CommandHandler("remove", remove_id))
    app.add_handler(CommandHandler("check", check_id))
    app.add_handler(CommandHandler("list", list_ids))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_device_id))

    print("🤖 Bot is running...")
    await app.run_polling()

# Dummy web server for Render
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_web).start()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.get_event_loop().run_until_complete(main())
