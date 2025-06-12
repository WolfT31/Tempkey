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
JSON_FILE = os.path.join(REPO_PATH, "Tempkey.json")  # Renamed from users.json
GITHUB_REPO_URL = f"https://{GITHUB_TOKEN}@github.com/WolfT31/Tempkey.json.git"

# Load user list from the Tempkey.json file
def load_users():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            return json.load(f).get("users", [])
    return []

# Save updated user list and push changes to GitHub
def save_users(users):
    with open(JSON_FILE, "w") as f:
        json.dump({"users": users}, f, indent=2)

    repo = Repo(REPO_PATH)
    repo.git.add("Tempkey.json")  # Updated
    repo.index.commit("Update users")
    origin = repo.remote(name="origin")
    origin.set_url(GITHUB_REPO_URL)
    origin.push()

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Send your device ID or use /add /remove /check /list commands."
    )

# /add <id>,<username>,<password>,<expire>,<allowoffline>
# Admin-only command to add new user
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
        # Parse input
        data = " ".join(context.args).strip()
        parts = data.split(",")

        if len(parts) != 5:
            raise ValueError("Invalid format. Use: /add <id>,<username>,<password>,<expire>,<allowoffline>")

        device_id, username, password, expire, allowoffline = [p.strip() for p in parts]
        allowoffline = allowoffline.lower() == "true"

        # Validate expiration date format
        datetime.strptime(expire, "%Y-%m-%d")

        users = load_users()

        # Check for duplicate ID
        if any(user["id"] == device_id for user in users):
            await update.message.reply_text("✅ This device ID already exists.")
            return

        # Add new user entry
        users.append({
            "id": device_id,
            "username": username,
            "password": password,
            "expire": expire,
            "allowoffline": allowoffline
        })

        # Save to file and push to GitHub
        save_users(users)

        # Send success message
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

# /remove <id> — Admin command to remove a user by ID
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

# /check <id> — Check if a device ID exists
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

# /list — Admin-only list of all approved users
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

# Handle plain text messages as potential device IDs
async def handle_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_id = update.message.text.strip()
    users = load_users()

    for user in users:
        if user["id"] == device_id:
            await update.message.reply_text("✅ Your device ID is already approved.")
            return

    await update.message.reply_text("❌ Your device ID is not approved.")

# Main entry point to run the bot
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command and message handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_id))
    app.add_handler(CommandHandler("remove", remove_id))
    app.add_handler(CommandHandler("check", check_id))
    app.add_handler(CommandHandler("list", list_ids))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_device_id))

    print("🤖 Bot is running...")
    await app.run_polling()

# Run the bot using asyncio
if __name__ == "__main__":
    import asyncio
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.get_event_loop().run_until_complete(main())