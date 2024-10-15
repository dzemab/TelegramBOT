import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation state
COMPLAINT_DESCRIPTION = 1

# Maximum number of messages per minute
MAX_MESSAGES_PER_MINUTE = 5

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user = update.message.from_user
    await update.message.reply_text(
        f"Здравствуйте, {user.first_name}! Добро пожаловать в бот для подачи заявок. "
        "Пожалуйста, предоставьте описание вашей жалобы."
    )
    context.user_data['open_complaint'] = True
    if 'spam_count' not in context.user_data:
        context.user_data['spam_count'] = 0
        context.user_data['spam_time'] = update.message.date.timestamp()
    return COMPLAINT_DESCRIPTION

async def complaint_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    complaint_description_text = update.message.text
    context.user_data['complaint_description'] = complaint_description_text

    # Generate the ticket ID
    ticket_id = f"#{len(context.user_data['complaint_description']):04}"

    # Get the username or user ID
    username = user.username or str(user.id)

    # Forward the message to the specific group using its group ID
    group_id = "-1002291300240"
    await context.bot.send_message(
        chat_id=group_id,
        text=f"Новая заявка:\n\nНомер заявки: {ticket_id}\n\nИмя пользователя/ID: @{username}\n\nID чата: {update.effective_chat.id}\n\nОписание жалобы: {context.user_data['complaint_description']}"
    )

    await update.message.reply_text(
        f"Спасибо за подачу жалобы. Ваш номер заявки - {ticket_id}. Мы скоро свяжемся с вами."
    )
    context.user_data['open_complaint'] = False
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Подача жалобы отменена."
    )
    context.user_data['open_complaint'] = False
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        if 'spam_count' not in context.user_data:
            context.user_data['spam_count'] = 0
            context.user_data['spam_time'] = update.message.date.timestamp()
            context.user_data['open_complaint'] = False

        current_time = update.message.date.timestamp()
        if current_time - context.user_data['spam_time'] < 60:
            context.user_data['spam_count'] += 1
            if context.user_data['spam_count'] > MAX_MESSAGES_PER_MINUTE:
                await update.message.reply_text("Вы отправили слишком много сообщений за минуту. Пожалуйста, подождите.")
                return
        else:
            context.user_data['spam_count'] = 1
            context.user_data['spam_time'] = current_time

        if context.user_data['open_complaint']:
            await complaint_description(update, context)
        else:
            await start(update, context)
    else:
        await handle_reply(update, context)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = update.message.reply_to_message
    if reply and reply.text and reply.text.startswith("Новая заявка:"):
        lines = reply.text.split('\n')
        chat_id_line = next((line for line in lines if line.startswith("ID чата:")), None)
        ticket_id_line = next((line for line in lines if line.startswith("Номер заявки:")), None)
        if chat_id_line and ticket_id_line:
            chat_id = chat_id_line.split(': ')[1]
            ticket_id = ticket_id_line.split(': ')[1]
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Ответ сотрудника на вашу заявку {ticket_id}:\n\n{update.message.text}"
                )
                await update.message.reply_text("Ответ отправлен пользователю.")
            except Exception as e:
                await update.message.reply_text(f"Ошибка отправки ответа пользователю: {str(e)}")
        else:
            await update.message.reply_text("Не удалось найти ID чата или номер заявки в заявке.")

def main():
    application = Application.builder().token("7556358742:AAExdTtV4gYfOurv5YRSYEaIftZS5gGKAGk").build()

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            COMPLAINT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_description)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conversation_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
