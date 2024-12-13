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

async def manage_task(update: Update, context: CallbackContext) -> None:
    """Handle task commands."""
    # Handle task status
    if len(context.args) == 1 and context.args[0].lower() == "status":
        if current_session["session_name"] and current_session["end_time"]:
            if datetime.now() < current_session["end_time"]:
                remaining_time = int((current_session["end_time"] - datetime.now()).total_seconds())

                if remaining_time > 3600:
                    hours = remaining_time // 3600
                    minutes = (remaining_time % 3600) // 60
                    seconds = remaining_time % 60
                    time_left = f"{hours} hr {minutes} min {seconds} sec"
                elif remaining_time > 60:
                    minutes = remaining_time // 60
                    seconds = remaining_time % 60
                    time_left = f"{minutes} min {seconds} sec"
                else:
                    time_left = f"{remaining_time} sec"

                await update.message.reply_text(
                    f"Task '{current_session['session_name']}' is active. Remaining time: {time_left}."
                )
            else:
                expired_task = current_session["session_name"]
                current_session["session_name"] = None
                current_session["end_time"] = None
                await update.message.reply_text(f"Task '{expired_task}' expired.")
                print(f"Task '{expired_task}' expired.")
            return
        else:
            await update.message.reply_text(
                "No active task. Use /taskatron <task_name> <task_time> <unit (sec/mins/hr)> to start a new task."
            )
            return

    # Handle task clear
    if len(context.args) == 1 and context.args[0].lower() == "clear":
        if current_session["session_name"]:
            cleared_task = current_session["session_name"]
            current_session["session_name"] = None
            current_session["end_time"] = None
            await update.message.reply_text(
                f"Task '{cleared_task}' has been cleared."
            )
            print(f"Task '{cleared_task}' cleared.")
        else:
            await update.message.reply_text("No active task to clear.")
        return

    # Handle starting a new task
    if len(context.args) != 3:
        await update.message.reply_text(
            "Usage: /taskatron <task_name> <task_time> <unit (sec/mins/hr)>\n"
            "or use /taskatron status to check the current task.\n"
            "or use /taskatron clear to clear the task."
        )
        return

    try:
        task_name = context.args[0]
        task_time = int(context.args[1])
        time_unit = context.args[2].lower()

        # Convert time to seconds based on the unit
        if time_unit == "sec":
            task_duration = task_time
        elif time_unit == "mins":
            task_duration = task_time * 60
        elif time_unit == "hr":
            task_duration = task_time * 3600
        else:
            await update.message.reply_text("Invalid time unit. Use 'sec', 'mins', or 'hr'.")
            return

        if current_session["session_name"] is None or datetime.now() > current_session["end_time"]:
            current_session["session_name"] = task_name
            current_session["end_time"] = datetime.now() + timedelta(seconds=task_duration)

            await update.message.reply_text(
                f"Task '{task_name}' started for {task_time} {time_unit}."
            )

            # Wait for task expiry
            asyncio.create_task(task_timer(task_name, task_duration, update))

        else:
            await update.message.reply_text(
                f"Another task '{current_session['session_name']}' is already running. Use /taskatron status to check."
            )

    except ValueError:
        await update.message.reply_text("Invalid task time. Please use a number for time.")

async def task_timer(task_name: str, task_time: int, update: Update):
    """Handles the task timeout in the background."""
    await asyncio.sleep(task_time)  # Wait until the task time expires
    # Expire task only if it's the current task
    if current_session["session_name"] == task_name:
        print(f"Task '{task_name}' expired.")
        current_session["session_name"] = None
        current_session["end_time"] = None
        await update.message.reply_text(f"Task '{task_name}' has expired.")

async def show_help(update: Update, context: CallbackContext) -> None:
    """Handle the /help command."""
    help_text = (
        "*Taskatron Commands*\n\n"
        "/taskatron <Name> <Time> <Unit (sec/mins/hr)>\n"
        "- Starts a new task with the given name and duration.\n\n"
        "/taskatron status\n"
        "- Checks the status of the current task, including the remaining time.\n\n"
        "/taskatron clear\n"
        "- Clears the current task if one is active.\n\n"
        "/help\n"
        "- Displays this help message with information about all commands."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

def main():
    """Main function to set up and run the bot."""
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("taskatron", manage_task))
    application.add_handler(CommandHandler("help", show_help))

    # Run polling
    application.run_polling()

if __name__ == "__main__":
    main()
