import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, ConversationHandler, filters
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Session management dictionary
current_session = {
    "session_name": None,
    "end_time": None
}

# List to manage multiple reminders
reminders = []

# States for the reminder conversation
REMINDER_DATE, REMINDER_LABEL, EDIT_REMINDER = range(3)


async def start(update: Update, context: CallbackContext) -> None:
    """Handle the /start command."""
    await update.message.reply_text("Hello! I am NotifyBuddy. How can I assist you today?")


async def manage_task(update: Update, context: CallbackContext) -> None:
    """Handle task commands."""
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

    if len(context.args) != 3:
        await update.message.reply_text(
            "Usage: /session <task_name> <task_time> <unit (sec/mins/hr)>\n"
            "or use /session status to check the current task.\n"
            "or use /session clear to clear the task."
        )
        return

    try:
        task_name = context.args[0]
        task_time = int(context.args[1])
        time_unit = context.args[2].lower()

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

            asyncio.create_task(task_timer(task_name, task_duration, update))

        else:
            await update.message.reply_text(
                f"Another task '{current_session['session_name']}' is already running. Use /session status to check."
            )
    except ValueError:
        await update.message.reply_text("Invalid task time. Please use a number for time.")


async def task_timer(task_name: str, task_time: int, update: Update):
    """Handles the task timeout in the background."""
    await asyncio.sleep(task_time)
    if current_session["session_name"] == task_name:
        print(f"Task '{task_name}' expired.")
        current_session["session_name"] = None
        current_session["end_time"] = None
        await update.message.reply_text(f"Task '{task_name}' has expired.")



async def reminder_start(update: Update, context: CallbackContext) -> int:
    """Start the reminder setup."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /reminder <date in dd/mm/yy> <time in HH:MM>\n"
            "Example: /reminder 25/12/24 14:30"
        )
        return ConversationHandler.END

    try:
        date_str = context.args[0]
        time_str = context.args[1]
        reminder_time = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%y %H:%M")

        if reminder_time <= datetime.now():
            await update.message.reply_text("The specified time must be in the future.")
            return ConversationHandler.END

        context.user_data["reminder_time"] = reminder_time
        await update.message.reply_text("What should I remind you about?")
        return REMINDER_LABEL
    except ValueError:
        await update.message.reply_text(
            "Invalid date or time format. Use dd/mm/yy for the date and HH:MM (24-hour format) for the time."
        )
        return ConversationHandler.END


async def reminder_label(update: Update, context: CallbackContext) -> int:
    """Handle the user input for reminder label."""
    reminder_time = context.user_data.get("reminder_time")
    reminder_label = update.message.text

    reminders.append({"time": reminder_time, "label": reminder_label})
    await update.message.reply_text(
        f"Reminder set for {reminder_time.strftime('%d/%m/%Y %H:%M')} with label: '{reminder_label}'."
    )

    # Pass bot and chat_id to the schedule_reminder function
    asyncio.create_task(schedule_reminder(reminder_time, reminder_label, context.bot, update.effective_chat.id))
    return ConversationHandler.END


async def schedule_reminder(reminder_time: datetime, label: str, bot, chat_id: int):
    """Schedule a reminder and send a message when the time is reached."""
    delay = (reminder_time - datetime.now()).total_seconds()
    await asyncio.sleep(delay)
    # Check if the reminder still exists
    reminder = next((r for r in reminders if r["time"] == reminder_time and r["label"] == label), None)
    if reminder:
        # Send the reminder message
        await bot.send_message(chat_id=chat_id, text=f"Reminder: {label}")
        reminders.remove(reminder)   # Remove reminder after sending

async def reminder_status(update: Update, context: CallbackContext) -> None:
    """Show the current active reminders and their designated times."""
    if not reminders:
        await update.message.reply_text("No active reminders.")
        return

    status_message = "Here are your current reminders:\n"
    for reminder in reminders:
        time_str = reminder["time"].strftime("%d/%m/%Y %H:%M")
        status_message += f"- {reminder['label']} at {time_str}\n"

    await update.message.reply_text(status_message)

async def reminder_cancel(update: Update, context: CallbackContext) -> None:
    """Cancel a specific reminder by label."""
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /reminder_cancel <reminder_name>")
        return

    reminder_label = " ".join(context.args)
    reminder = next((r for r in reminders if r["label"] == reminder_label), None)

    if reminder:
        reminders.remove(reminder)  # Remove the reminder from the list
        await update.message.reply_text(f"Reminder '{reminder_label}' has been canceled.")
    else:
        await update.message.reply_text(f"No reminder found with the label '{reminder_label}'.")


async def show_help(update: Update, context: CallbackContext) -> None:
    """Send a help message listing bot commands."""
    await update.message.reply_text(
        "Here are the available commands:\n\n"
        "/start - Start the bot\n\n"
        "/session - Manage session tasks:\n"
        "  ├ /session <name> <time> <unit> - Start a session\n"
        "  ├ /session status - View the current session tasks\n"
        "  ├ /session_edit <reminder_name> - Edit session\n"
        "  └ /session clear - Clear all session tasks\n\n"
        "/reminder - Manage reminders:\n"
        "  ├ /reminder <date> <time> - Set a reminder\n"
        "  ├ /reminder_status - View current reminders\n"
        "  ├ /reminder_cancel <name> - Cancel a reminder by name\n\n"
        "  └/reminder_edit <reminder_name> - Edit Reminder"
        "/cancel - Cancel the current operation\n"
    )

async def reminder_edit(update: Update, context: CallbackContext) -> int:
    """Start the process to edit a reminder."""
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /reminder_edit <reminder_name>")
        return ConversationHandler.END

    reminder_label = " ".join(context.args)
    reminder = next((r for r in reminders if r["label"] == reminder_label), None)

    if reminder:
        context.user_data["editing_reminder"] = reminder
        await update.message.reply_text(
            "Enter the new details for the reminder in the format: <date in dd/mm/yy> <time in HH:MM> <new_label>."
        )
        return EDIT_REMINDER
    else:
        await update.message.reply_text(f"No reminder found with the label '{reminder_label}'.")
        return ConversationHandler.END


async def edit_reminder(update: Update, context: CallbackContext) -> int:
    """Handle the user input for editing a reminder."""
    reminder = context.user_data.get("editing_reminder")
    if not reminder:
        await update.message.reply_text("No reminder to edit.")
        return ConversationHandler.END

    try:
        new_details = update.message.text.split()
        if len(new_details) < 3:
            await update.message.reply_text(
                "Invalid format. Use: <date in dd/mm/yy> <time in HH:MM> <new_label>."
            )
            return EDIT_REMINDER

        new_date = new_details[0]
        new_time = new_details[1]
        new_label = " ".join(new_details[2:])

        new_reminder_time = datetime.strptime(f"{new_date} {new_time}", "%d/%m/%y %H:%M")

        if new_reminder_time <= datetime.now():
            await update.message.reply_text("The specified time must be in the future.")
            return EDIT_REMINDER

        # Update the reminder
        reminder["time"] = new_reminder_time
        reminder["label"] = new_label

        await update.message.reply_text(
            f"Reminder updated to: '{new_label}' at {new_reminder_time.strftime('%d/%m/%Y %H:%M')}."
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "Invalid date or time format. Use dd/mm/yy for the date and HH:MM (24-hour format) for the time."
        )
        return EDIT_REMINDER


def main():
    """Main function to set up and run the bot."""
    application = ApplicationBuilder().token(API_TOKEN).build()

    reminder_handler = ConversationHandler(
        entry_points=[CommandHandler("reminder", reminder_start)],
        states={
            REMINDER_LABEL: [MessageHandler(filters.TEXT, reminder_label)],
        },
        fallbacks=[CommandHandler("cancel", reminder_cancel)],
    )
    application.add_handler(reminder_handler)



    
    application.add_handler(CommandHandler("reminder_cancel", reminder_cancel))

    application.add_handler(CommandHandler("reminder_status", reminder_status))

    edit_handler = ConversationHandler(
        entry_points=[CommandHandler("reminder_edit", reminder_edit)],
        states={
            EDIT_REMINDER: [MessageHandler(filters.TEXT, edit_reminder)],
        },
        fallbacks=[CommandHandler("cancel", reminder_cancel)],
    )
    application.add_handler(reminder_handler)
    application.add_handler(edit_handler)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("session", manage_task))
    application.add_handler(CommandHandler("help", show_help))

    application.run_polling()


if __name__ == "__main__":
    main()