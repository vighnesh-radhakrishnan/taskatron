import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from dotenv import load_dotenv 

load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_TOKEN")


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Hello! I am NotifyBuddy. How can I assist you today, tomorrow?")


# Main function to run the bot
def main():
    # Create the application using the token
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))

    # Start polling
    application.run_polling()


if __name__ == "__main__":
    main()
