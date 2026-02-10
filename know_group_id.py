# from telegram import Update
# from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# # Function to handle the /start command
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     group_id = update.message.chat.id  # Get the group ID
#     await update.message.reply_text(f'Group ID: {group_id}')

# # Main function to set up the bot
# def main():
#     # Replace with your bot's token
#     token = '7721307120:AAEeouDOnAngXavaB55p3iRYa9ufFAOJDX8'
    
#     # Create the Application
#     app = ApplicationBuilder().token(token).build()

#     # Add the /start command handler
#     app.add_handler(CommandHandler("start", start))
 
#     # Start polling
#     app.run_polling()

# if __name__ == "__main__":
#     main()
