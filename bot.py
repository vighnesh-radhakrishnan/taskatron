from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext


API_TOKEN = "7712239658:AAHex1fmbzRkqslEAnNrkmgxEbtKE5wG6TE"

# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Hello! I am NotifyBuddy. How can I assist you today??")


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
