import os
import telegram
import openai
import asyncio
import requests
import json
import uuid
import pydub
import sqlite3
import time
import pytz
import datetime
import cProfile
import pstats
import random
import yfinance as yf
from functools import wraps
from collections import defaultdict
from telegram.ext import ContextTypes,Application, MessageHandler, filters
from telegram.constants import ChatAction
from pathlib import Path
from telegram import Update, Voice
from pyairtable import Api, Base, Table

# Define the timezone to use for the schedule
timezone = pytz.timezone('Europe/Paris')


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

# Connexion à l'API OpenAI
openai.api_key = "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"

# Bot Token
# MICHEL(LE)
# bot_token = '6292150121:AAFrHcOBW8uqnJVOAJWOxw4bRQhOqD9XEtk'
# Teilo
bot_token = '6186110392:AAFKCmlMli616SDk7xWHDRDefVq_k3Lo4GQ'

# OPENWEATHERMAP API
openweathermap_api = '53224c91f12b6562f311d7faaa7a7c95'

# Connexion au bot Telegram
bot = telegram.Bot(token=bot_token)

# Airtable token
airtable_token = 'pat4NuCc5dQ3aNs61.f35eaaa736f4dbde4b0ab9a03248ef7675b8436ca93e992d29eebf8ab3839e2e'
airtable_api_key = 'key4qXiE1LBxWosV6'
# Michel(le) BaseID
base_id = 'apptYSl5IM46hP1jo'

table = Table(airtable_api_key, base_id, 'user_ids')
table.all()

# Chatbot handle
chatbot_handle = '@Michel_le_robot'

# Create a dictionary to store the chat history
chat_history = defaultdict(list)

AUDIOS_DIR = "audios"

# Max number of chat history to keep for each chat_id
MAX_HISTORY = 5

# Voice
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

# Generate the response the bot will send to the user
def generate_bot_response(user_input, chat_id):

    history = chat_history[chat_id][-MAX_HISTORY:]  # Get the latest chat history for this chat_id
    
    command_handlers = {
        '/help': handle_help_command,
        # Add more commands here as needed
        '/start': handle_start_command,
        '/jul': handle_jul_command
    }
    
    # Call the appropriate handler function based on the command entered by the user
    if user_input.split()[0] in command_handlers:
        handler = command_handlers[user_input.split()[0]]
        message = handler(user_input, history)
        
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

def handle_jul_command(user_input, history):
    user_input = "Donne moi une citation de JUL et précise le nom du son."
    
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

    # Return the bot's response
    return message

async def handle_help_command(user_input, history):
    # Provide some help text to the user
    message = "Voici une liste de commandes que je comprends :\n/meteo <ville> - obtenir la météo actuelle et les prévisions pour une ville donnée\n/aide - afficher cette aide"
    # Save the command to the chat history
    history.append(("user", user_input))
    # Save the help message to the chat history
    history.append(("bot", message))
    return message

async def handle_start_command(user_input, update, history):
    # Get the user ID from the update object
    user_id = str(update.effective_user.id)

    # Add the user ID to the database
    if not check_user_id(user_id):
        add_user_id(user_id)

    # Provide some help text to the user
    message = "Hello/Bonjour (:\n Vous pouvez envoyer 100 messages (texte ou vocaux) gratuitement chaque mois. \n Pour augmenter cette limite merci de contacter @teilomillet."
    # Save the command to the chat history
    history.append(("user", user_input))
    # Save the help message to the chat history
    history.append(("bot", message))
    return message

async def handle_message(update, context):
    """Handle an incoming message."""
    message = update.message
    chat_id = update.message.chat_id
    user_id = json.dumps(update.message.from_user.id)
    username = json.dumps(update.message.from_user.username)
    first_name = json.dumps(update.message.from_user.first_name)
    last_name = json.dumps(update.message.from_user.last_name)

    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # Reset message count on the first day of each month
    if datetime.datetime.now().day == 1 and message_count != 0:
        record_id = records[0]['id']
        table.update(record_id, {'message_count': 0})
        message_count = 0

    # Ignore messages from bots
    if update.message.from_user.is_bot:
        return

    # Check if the user_id exists in the table
    records = table.all(formula=f"user_id = '{user_id}'")
    if len(records) == 0:
        # If the user_id doesn't exist, create a new record
        table.create({
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'user_type': 'basic'
        })
    else:
        record = records[0]
        message_count = record.get('fields', {}).get('message_count', 0) + 1
        table.update(record['id'], {'message_count': message_count})

        # Check if user message count has exceeded the limit
        user_type = record.get('fields', {}).get('user_type', 'basic')
        message_limits = {
            'basic': 100,
            'personal': 300,
            'pro': 600
            
        }
        if message_count >= message_limits[user_type]:
            if message_count == message_limits[user_type]:
                await message.reply_text(f"Vous avez envoyé {message_count} messages ce mois. Contactez @teilomillet pour augmenter votre limite mensuelle.")
            else:
                # Stop the bot from replying if message count has exceeded the limit
                return


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

# list of words for 'Le savais tu..'
random_words = [
                'le sport', 'la Nature', 'la physique', 'les mathématiques', 'la technologie', 'la science', 
                'la culture', "l'art", 'le cinema', 'la géographie', "l'histoire", "la musique", "la musique francaise", 
                "le vin", "le fromage", "les découvertes", "un fait important", "l'histoire de france", 'le design', 'le mobilier', 
                "l'astronomie", "l'astrologie", "la santé", "l'environnement", "l'économie", "la médecine", "l'espace", "l'Antiquité",
                "le Moyen-Age", "L'age de pierre", "L'empire romain", "les plantes", "les oiseaux", "les animaux", "Les civilisations anciennes",
                "les jeux vidéo", "la sociologie", "un explorateur", "la culture populaire", "une célébrité", 'la mythologie', 'la psychologie', 
                'les légendes', "l'océanographie", "les métaux précieux", "la chimie", "un inventeur", "les relations internationales"
]

# list of questions for 'Le savais tu ...'
random_questions = [
                'Apprend moi quelque chose', "Donne moi un 'fun-fact'",
                "Raconte moi une anecdote intéressante", "Dis-moi quelque chose d'instructif",
                "Partage une information curieuse", "Donne-moi un fait intéressant",
                "Enseigne-moi quelque chose d'intéressant", "Apprend moi quelque chose d'inattendu",
                "Apprend moi quelque chose d'étonnant", "Raconte moi une anecdote insoupçonnée",
                "Donne-moi un fait surprenant", "Dis-moi quelque chose d'inespéré",
                "Raconte-moi une histoire inouïe", "Raconte moi une anecdote comique",
                "Donne-moi un fait comique", 
]

# Schedule phase
async def schedule_phase(context):
    # Get all registered users from the Airtable database
    users = table.all()

    # Create an empty list to store the messages
    messages = []

    # Random choice of words
    random_word = random.choice(random_words)

    # Random choice of question
    random_question = random.choice(random_questions)

    # Iterate over each user and send the prompt to OpenAI
    for user in users:
        chat_id = user['fields']['user_id']
        history = chat_history[chat_id][-MAX_HISTORY:]
        # user_input = f"Donne moi une citation de JUL."
        user_input = f"{random_question} sur {random_word} s'il te plait, répond directement par :'Le savais-tu ...'." # Change this to the prompt you want to send to OpenAI
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
                temperature=1,
                max_tokens=500,
                frequency_penalty=0.0,
                presence_penalty=0.8,
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

        # Append the chat_id and message as a tuple to the messages list
        messages.append((chat_id, message))

    # Send the messages to users
    for chat_id, message in messages:
        await context.bot.send_message(chat_id=chat_id, text=message)

interval = 50400
# 24h - 86400
# 14h - 50400

# Define a function to start the bot and handle incoming updates
def main():
    # Create the directory
    create_dir_if_not_exists(AUDIOS_DIR)

    # Create an updater object
    updater = Application.builder().token(bot_token).build()

    # Add a handler for handling user messages
    updater.add_handler(MessageHandler(filters.ALL, handle_message))

    # Create a JobQueue
    job_queue = updater.job_queue

    # Schedule the schedule_phase function to run every 24 hours
    job_queue.run_repeating(schedule_phase, interval=interval, first=datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))

    # Start the bot and run the dispatcher until the bot is stopped
    updater.run_polling()

if __name__ == "__main__":
   main()