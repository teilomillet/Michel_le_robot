import telegram
import openai
from telegram.ext import Updater, MessageHandler, Filters

# Connexion à l'API OpenAI
openai.api_key = "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"

# Connexion au bot Telegram
bot = telegram.Bot(token='6292150121:AAFrHcOBW8uqnJVOAJWOxw4bRQhOqD9XEtk')

# Fonction de réponse
def generate_response(user_input):
    # prompt="The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.\n\nHuman: Hello, who are you?\nA: I am an AI created by OpenAI. How can I help you today?\nHuman: " + user_input + "\nAI:",
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
        {"role": "system", "content": "You are Michel(le), a helpful, creative and clever assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        {"role": "user", "content": user_input + ' please.'}
        ],
        temperature=0.8,
        max_tokens=150,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.6,
        stop=None
)
    message = completions['choices'][0]['message']['content']
    return message.strip() 

# Fonction de gestionnaire de message
def handle_message(update, context):
    user_input = update.message.text
    response = generate_response(user_input)
    update.message.reply_text(response)

# create a new function to send a single message to the user
def send_single_message(chat_id, message_text):
    bot.send_message(chat_id=chat_id, text=message_text)

# generate a response to a single user input and send it to the user
def generate_and_send_response(user_input, chat_id):
    response = generate_response(user_input)
    send_single_message(chat_id, response)

# Création de l'objet Updater
updater = Updater(token='6292150121:AAFrHcOBW8uqnJVOAJWOxw4bRQhOqD9XEtk', use_context=True)

# Création du gestionnaire de message et association à l'Updater
message_handler = MessageHandler(Filters.text, handle_message)
updater.dispatcher.add_handler(message_handler)

# Démarrage du bot
updater.start_polling()
updater.idle()