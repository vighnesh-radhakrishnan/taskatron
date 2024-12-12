import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Session management dictionary
current_session = {
    "session_name": None,
    "end_time": None
}


async def start(update: Update, context: CallbackContext) -> None:
    """Handle the /start command."""
    await update.message.reply_text("Hello! I am NotifyBuddy. How can I assist you today?")


async def manage_session(update: Update, context: CallbackContext) -> None:
    """Handle session commands."""
    # Handle session status
    if len(context.args) == 1 and context.args[0].lower() == "status":
        if current_session["session_name"] and current_session["end_time"]:
            if datetime.now() < current_session["end_time"]:
                remaining_time = int((current_session["end_time"] - datetime.now()).total_seconds())
                await update.message.reply_text(
                    f"Session '{current_session['session_name']}' is active. Remaining time: {remaining_time} seconds."
                )
            else:
                expired_session = current_session["session_name"]
                current_session["session_name"] = None
                current_session["end_time"] = None
                await update.message.reply_text(f"Session '{expired_session}' expired.")
                print(f"Session '{expired_session}' expired.")
            return

    # Handle session clear
    if len(context.args) == 1 and context.args[0].lower() == "clear":
        if current_session["session_name"]:
            cleared_session = current_session["session_name"]
            current_session["session_name"] = None
            current_session["end_time"] = None
            await update.message.reply_text(
                f"Session '{cleared_session}' has been cleared."
            )
            print(f"Session '{cleared_session}' cleared.")
        else:
            await update.message.reply_text("No active session to clear.")
        return

    # Handle starting a new session
    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /session <session_name> <session_time (seconds)>\n"
            "or use /session status to check the current session.\n"
            "or use /session clear to clear the session."
        )
        return

    try:
        session_name = context.args[0]
        session_time = int(context.args[1])

        if current_session["session_name"] is None or datetime.now() > current_session["end_time"]:
            current_session["session_name"] = session_name
            current_session["end_time"] = datetime.now() + timedelta(seconds=session_time)

            await update.message.reply_text(
                f"Session '{session_name}' started for {session_time} seconds."
            )

            # Wait for session expiry
            asyncio.create_task(session_timer(session_name, session_time, update))

        else:
            await update.message.reply_text(
                f"Another session '{current_session['session_name']}' is already running. Use /session status to check."
            )

    except ValueError:
        await update.message.reply_text("Invalid session time. Please use a number in seconds.")


async def session_timer(session_name: str, session_time: int, update: Update):
    """Handles the session timeout in the background."""
    await asyncio.sleep(session_time)  # Wait until the session time expires
    # Expire session only if it's the current session
    if current_session["session_name"] == session_name:
        print(f"Session '{session_name}' expired.")
        current_session["session_name"] = None
        current_session["end_time"] = None
        await update.message.reply_text(f"Session '{session_name}' has expired.")


def main():
    """Main function to set up and run the bot."""
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("session", manage_session))

    # Run polling
    application.run_polling()


if __name__ == "__main__":
    main()
