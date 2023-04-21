import os
import telegram
import openai
import asyncio
import requests
import json
import uuid
import pydub
import yfinance as yf
from functools import wraps
from collections import defaultdict
from telegram.ext import Application, MessageHandler, filters
from pathlib import Path
from telegram import Update, Voice
from telegram.ext import CallbackContext

# Connexion à l'API OpenAI
openai.api_key = "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"

# bot token
bot_token = '6292150121:AAFrHcOBW8uqnJVOAJWOxw4bRQhOqD9XEtk'

# OPENWEATHERMAP API
openweathermap_api = '53224c91f12b6562f311d7faaa7a7c95'

# Connexion au bot Telegram
bot = telegram.Bot(token=bot_token)

# Chatbot handle
chatbot_handle = '@Michel_le_robot'

# Create a dictionary to store the chat history
chat_history = defaultdict(list)

AUDIOS_DIR = "audios"

# Max number of chat history to keep for each chat_id
MAX_HISTORY = 5

def create_dir_if_not_exists(dir):
    if (not os.path.exists(dir)):
        os.mkdir(dir)

def generate_unique_name():
    uuid_value = uuid.uuid4()
    return f"{str(uuid_value)}"

def convert_speech_to_text(audio_filepath):
    with open(audio_filepath, "rb") as audio:
        transcript = openai.Audio.transcribe("whisper-1", audio)
        return transcript["text"]

async def download_voice_as_ogg(voice):
    voice_file = await voice.get_file()
    ogg_filepath = os.path.join(AUDIOS_DIR, f"{generate_unique_name()}.ogg")
    await voice_file.download_to_drive(ogg_filepath)
    return ogg_filepath

def convert_ogg_to_mp3(ogg_filepath):
    mp3_filepath = os.path.join(AUDIOS_DIR, f"{generate_unique_name()}.mp3")
    audio = pydub.AudioSegment.from_file(ogg_filepath, format="ogg")
    audio.export(mp3_filepath, format="mp3")
    return mp3_filepath

async def handle_voice(update: telegram.Update,
                       context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    ogg_filepath = await download_voice_as_ogg(update.message.voice)
    mp3_filepath = convert_ogg_to_mp3(ogg_filepath)
    transcripted_text = convert_speech_to_text(mp3_filepath)
    answer = generate_bot_response(transcripted_text)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)
    os.remove(ogg_filepath)
    os.remove(mp3_filepath)

def generate_bot_response(user_input, chat_id):

    history = chat_history[chat_id][-MAX_HISTORY:]  # Get the latest chat history for this chat_id
    
    command_handlers = {
        '/meteo': handle_meteo_command,
        '/help': handle_help_command,
        '/stock': handle_stock_command,
        # Add more commands here as needed
    }
    
    # Call the appropriate handler function based on the command entered by the user
    if user_input.split()[0] in command_handlers:
        handler = command_handlers[user_input.split()[0]]
        message = handler(user_input, history)

    elif len(history) > 1 and 'Quelle ville ?' in history[-1][1]:
        # Check if the bot has sent a prompt for the city name in the previous message
        # Extract the city from the user_input
        city = user_input
        # Call the OpenWeatherMap API to get the current weather and forecast for the city
        response = requests.get(f'http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid='+openweathermap_api)
        data = json.loads(response.text)
        if data['cod'] == '404':
            message = f"Je n'ai pas trouvé la météo pour la ville de {city}. Pouvez-vous vérifier l'orthographe ou essayer une autre ville ?"
        else:
            current_temp = data['main']['temp']
            current_desc = data['weather'][0]['description']
            forecast_response = requests.get(f'http://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&appid='+openweathermap_api)
            forecast_data = json.loads(forecast_response.text)
            forecast = forecast_data['list'][0]['weather'][0]['description']
            message = f"La température actuelle à {city} est de {current_temp}°C avec des {current_desc}. La prévision pour les prochaines 4 heures est {forecast}."
        # Save the user's input to the chat history
        history.append(("user", user_input))
        # Save the bot's response to the chat history
        history.append(("bot", message))

    elif len(history) > 1 and 'Quelle action (ticker) ?' in history[-1][1]:
        # Get the stock symbol from the user's response
        stock_symbol = user_input.upper()
        # Get the latest price of the stock
        try:
            stock = yf.Ticker(stock_symbol)
            latest_price = stock.history(period="1d")['Close'][0]
            message = f"The latest price of {stock.info['longName']} ({stock_symbol}) is {latest_price:.2f} USD."
        except:
            message = f"Sorry, {stock_symbol} is not recognized. Please try another stock symbol."
        # Save the user's input and the bot's response to the chat history
        history.append(("user", user_input))
        history.append(("bot", message))
        
    else:  
        try:
            completions = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                # Append the previous responses to the prompt
                messages=[
                    {"role": "system", "content": "You are Michel(le), a french helpful, creative, clever and funny assistant."},
                    *[
                        {"role": "user", "content": content} if role == "user" else {"role": "assistant", "content": content} 
                        for role, content in history
                    ],
                    # Append the user's latest message to the prompt
                    {"role": "user", "content": user_input + ' please.'}
                ],
                temperature=0.8,
                max_tokens=500,
                frequency_penalty=0.0,
                presence_penalty=0.6,
                stop=None
            )
            message = completions['choices'][0]['message']['content']
        except:
            message = "Je suis désolé, une erreur s'est produite lors de l'appel à l'API OpenAI. Pouvez-vous réessayer plus tard ?"
    
     # Append the latest user input and bot response to the chat history
    history.append(("user", user_input))
    history.append(("bot", message))

    # Update the chat history for this chat_id
    chat_history[chat_id] = history[-MAX_HISTORY:]

    # Return the bot's response
    return message

async def handle_meteo_command(user_input, history):
    # Send a prompt to ask the user for the city name
    message = 'Quelle ville ?'
    # Save the command to the chat history
    history.append(("user", user_input))
    # Save the prompt to the chat history
    history.append(("bot", message))
    return message

async def handle_stock_command(user_input, history):
    # Send a prompt to ask the user for the city name
    message = 'Quelle action (ticker) ?'
    message += '\nVoici quelques exemples d\'actions : ' + '\nCAC40 : ^FCHI,\nCASINO : CO.PA,\nSALESFORCE: CRM'  + '\n'
    # Save the command to the chat history
    history.append(("user", user_input))
    # Save the prompt to the chat history
    history.append(("bot", message))
    return message

async def handle_help_command(user_input, history):
    # Provide some help text to the user
    message = "Voici une liste de commandes que je comprends :\n/meteo <ville> - obtenir la météo actuelle et les prévisions pour une ville donnée\n/aide - afficher cette aide"
    # Save the command to the chat history
    history.append(("user", user_input))
    # Save the help message to the chat history
    history.append(("bot", message))
    return message


async def handle_message(update, context):
    """Handle an incoming message."""
    message = update.message
    chat_id = update.message.chat_id
    if message.voice:
        ogg_filepath = await download_voice_as_ogg(update.message.voice)
        mp3_filepath = convert_ogg_to_mp3(ogg_filepath)
        transcripted_text = convert_speech_to_text(mp3_filepath)
        answer = generate_bot_response(transcripted_text, chat_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)
        os.remove(ogg_filepath)
        os.remove(mp3_filepath)
    elif message.text:
        await message.reply_text(generate_bot_response(message.text, chat_id))


# Define a function to start the bot and handle incoming updates
def main():
    # Create an updater object
    updater= Application.builder().token(bot_token).build()

       # Add a handler for handling user messages
    updater.add_handler(MessageHandler(filters.ALL, handle_message))

    # Start the bot and run the dispatcher until the bot is stopped
    updater.run_polling()

if __name__ == "__main__":
    asyncio(main())