# complimentBot.py

# Have openAI refer to the user by their first name repeatedly.

import logging
import os
import asyncio
from io import BytesIO

from telegram import (
    Update,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI
from dotenv import load_dotenv
import complimentUserDatabase as database
# Removed gTTS import
# from gtts import gTTS

# Import ElevenLabs
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Load environment variables from .env file
load_dotenv()

# Enable detailed logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Change to INFO or WARNING in production
)
logger = logging.getLogger(__name__)

# Load environment variables or set your keys here
TELEGRAM_BOT_TOKEN = os.getenv('COMPLIMENT_BOT_TOKEN') or 'YOUR_TELEGRAM_BOT_TOKEN'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or 'YOUR_OPENAI_API_KEY'
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") or 'YOUR_ELEVENLABS_API_KEY'

# Check if API keys are set
if not TELEGRAM_BOT_TOKEN:
    logger.error("COMPLIMENT_BOT_TOKEN is not set.")
    exit(1)

if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY is not set.")
    exit(1)

if not ELEVENLABS_API_KEY:
    logger.error("ELEVENLABS_API_KEY is not set.")
    exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize ElevenLabs client
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Initialize the database
database.initialize_database()

# Define constants
FREE_INTERACTIONS = 10
CREDIT_COST_PER_INTERACTION = 1  # 1 Credit per interaction

# Store the compliments without names for privacy
compliments = {
    "personality": [
        "Your love for life is contagious. Simply being near you makes others happier. Your presence brings smiles.",
        "You're such a joy to be around. Always ready with a smile and a fun comment.",
        "You have the best laugh and are one of the most genuine people."
    ],
    "creativity": [
        "Your wit, passion, positivity, and sheer boundless creativity are inspiring.",
        "This compliment hotline is a brilliant example of your creative thinking.",
        "Thank you for your giggle and your unique sense of humor."
    ],
    "appearance": [
        "Your nose crinkles in the most adorable way when you tell a joke!",
        "You radiate light around you; your glow is warm and kind.",
        "Your spontaneous dancing makes souls smile."
    ],
    "general": [
        "You always know just what to say.",
        "You're always generous and kind to everyone you meet.",
        "I always learn something new when I speak with you."
    ],
}

# Define the custom menu keyboard
def get_main_menu_keyboard():
    """Returns the main menu keyboard."""
    keyboard = [
        ['😊 Personality', '🎨 Creativity'],
        ['💃 Physical Appearance', '🌟 General Awesomeness'],
        ['🏠 Home', '📚 Help'],
        ['💳 Balance'],
        ['🎁 Free Credits', '🔊 Audio On/Off']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# Define menu options
MENU_OPTIONS = [
    '😊 Personality', '🎨 Creativity', '💃 Physical Appearance', '🌟 General Awesomeness',
    '🏠 Home', '📚 Help', '💳 Balance', '🎁 Free Credits', '🔊 Audio On/Off'
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with the main menu when the /start command is issued."""
    try:
        user_id = update.effective_user.id
        user = database.get_user(user_id)
        free_left = max(FREE_INTERACTIONS - user['free_interactions_used'], 0)
        credits = user['credits']

        welcome_text = (
            f"Hello {update.effective_user.first_name}! Welcome to the Compliment Hotline! 😍\n\n"
            f"Choose a category below to receive a heartfelt compliment.\n\n"
            f"You have {free_left} free interactions left.\n"
            f"You currently have {credits} Credits."
        )

        await update.message.reply_text(welcome_text, reply_markup=get_main_menu_keyboard())
        logger.debug(f"Sent welcome message to user {user_id} with main menu.")
    except Exception as e:
        logger.exception(f"Error in start handler for user {update.effective_user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the /help command is issued."""
    try:
        help_text = (
            "Welcome to the Compliment Hotline! Choose a category from the menu to receive a compliment.\n\n"
            "You can also control me by using these commands:\n"
            "/start - Welcome message with main menu\n"
            "/help - This help message\n"
            "/audio - Toggle audio responses on/off\n"
            "/balance - Check your current balance\n\n"
            "By default, I reply with text. Use /audio to receive voice messages."
        )
        await update.message.reply_text(help_text, reply_markup=get_main_menu_keyboard())
        logger.debug("Sent help message to user.")
    except Exception as e:
        logger.exception(f"Error in help_command handler for user {update.effective_user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred while fetching help information.", reply_markup=get_main_menu_keyboard())

async def toggle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle audio responses for the user."""
    try:
        user_data = context.user_data
        audio_enabled = user_data.get('audio_enabled', False)
        user_data['audio_enabled'] = not audio_enabled
        status = "enabled" if user_data['audio_enabled'] else "disabled"
        await update.message.reply_text(f"Audio responses have been {status}.", reply_markup=get_main_menu_keyboard())
        logger.debug(f"Audio responses have been {status} for user {update.effective_user.id}.")
    except Exception as e:
        logger.exception(f"Error in toggle_audio handler for user {update.effective_user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred while toggling audio.", reply_markup=get_main_menu_keyboard())

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's current Credit balance and free interactions left."""
    try:
        user_id = update.effective_user.id
        user = database.get_user(user_id)
        credits = user['credits']
        free_left = max(FREE_INTERACTIONS - user['free_interactions_used'], 0)

        balance_text = (
            f"You have {free_left} free interactions left.\n"
            f"You currently have {credits} Credits."
        )
        await update.message.reply_text(balance_text, reply_markup=get_main_menu_keyboard())
        logger.debug(f"Displayed balance to user {user_id}.")
    except Exception as e:
        logger.exception(f"Error in balance handler for user {update.effective_user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred while fetching your balance.", reply_markup=get_main_menu_keyboard())

def generate_openai_response(user_id: int, user_text: str, category: str) -> str:
    """Generate a response from OpenAI's ChatCompletion API."""
    logger.debug(f"Generating OpenAI response for user {user_id} with message: {user_text}")
    try:
        # Prepare the inspiration text
        inspiration_texts = compliments.get(category, [])
        inspiration = "\n".join([f"- {c}" for c in inspiration_texts])

        prompt = (
            "Using the following compliments as inspiration, write a new heartfelt compliment "
            f"focused on {category.replace('_', ' ')}:\n"
            f"{inspiration}\n\n"
            f"New compliment:"
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Replace with your preferred model
            messages=[
                {"role": "system", "content": "You are a master at giving amazing compliments that people love and cherish."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7,
        )
        # Extract and return the assistant's reply
        assistant_reply = response.choices[0].message.content.strip()
        logger.debug(f"OpenAI response for user {user_id}: {assistant_reply}")
        return assistant_reply
    except Exception as e:
        logger.exception(f"Error communicating with OpenAI API for user {user_id}: {e}")
        return "Sorry, I couldn't process that."

def text_to_speech_stream(text: str) -> BytesIO:
    """
    Converts text to speech using ElevenLabs and returns the audio data as a byte stream.
    """
    try:
        # Perform the text-to-speech conversion
        response = elevenlabs_client.text_to_speech.convert(
            voice_id="nsQAxyXwUKBvqtEK9MfK",  # Denzel pre-made voice
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )

        # Create a BytesIO object to hold audio data
        audio_stream = BytesIO()

        # Write each chunk of audio data to the stream
        for chunk in response:
            if chunk:
                audio_stream.write(chunk)

        # Reset stream position to the beginning
        audio_stream.seek(0)

        # Return the stream for further use
        return audio_stream
    except Exception as e:
        logger.exception(f"Error in text_to_speech_stream: {e}")
        return None

async def generate_compliment(update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str) -> None:
    """Generate a compliment based on the selected category."""
    try:
        user_id = update.effective_user.id
        logger.debug(f"Generating compliment for user {user_id} in category: {category_key}")

        user = database.get_user(user_id)
        logger.debug(f"User data: {user}")

        # Check if user has free interactions left
        if user['free_interactions_used'] < FREE_INTERACTIONS:
            # Increment free interactions used
            database.increment_free_interactions(user_id)
            logger.debug(f"User {user_id} has free interactions remaining.")
        else:
            # Check if user has enough Credits
            if user['credits'] >= CREDIT_COST_PER_INTERACTION:
                # Consume Credits
                success = database.consume_credit(user_id)
                if not success:
                    await update.message.reply_text("An error occurred while consuming a Credit. Please try again.", reply_markup=get_main_menu_keyboard())
                    return
                logger.debug(f"User {user_id} consumed {CREDIT_COST_PER_INTERACTION} Credit(s). Remaining credits: {user['credits'] - CREDIT_COST_PER_INTERACTION}")
            else:
                await update.message.reply_text(
                    "You have used all your free interactions and have no Credits left.",
                    reply_markup=get_main_menu_keyboard()
                )
                logger.debug(f"User {user_id} has no Credits left.")
                return

        # Generate response from OpenAI
        response_text = await asyncio.get_event_loop().run_in_executor(None, generate_openai_response, user_id, "", category_key)

        # Check if OpenAI returned an error message
        if response_text == "Sorry, I couldn't process that.":
            await update.message.reply_text(response_text, reply_markup=get_main_menu_keyboard())
            logger.debug(f"Sent error message to user {user_id}.")
            return

        # Split the response into chunks to adhere to Telegram's message limits (4096 characters)
        message_chunks = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]

        # Check if user has enabled audio responses
        if context.user_data.get('audio_enabled', False):
            try:
                # Use ElevenLabs for text-to-speech
                audio_bytes = text_to_speech_stream(response_text)
                if audio_bytes is None:
                    raise Exception("Failed to generate audio stream.")

                # Send the audio as an audio file on Telegram
                await update.message.reply_audio(audio=audio_bytes)
                logger.debug(f"Sent audio response to user {user_id} using ElevenLabs.")
            except Exception as e:
                logger.exception(f"Error generating or sending audio response to user {user_id}: {e}")
                await update.message.reply_text("Sorry, I couldn't generate an audio response.", reply_markup=get_main_menu_keyboard())
        else:
            for chunk in message_chunks:
                await update.message.reply_text(chunk, reply_markup=get_main_menu_keyboard())
                logger.debug(f"Sent text response chunk to user {user_id}.")
    except Exception as e:
        logger.exception(f"Error in generate_compliment handler for user {update.effective_user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred while generating your compliment.", reply_markup=get_main_menu_keyboard())

async def reset_interactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset the user's free interactions used."""
    try:
        user_id = update.effective_user.id
        database.update_user(user_id, free_interactions_used=0)
        await update.message.reply_text("Your free interactions have been reset to 10.", reply_markup=get_main_menu_keyboard())
        logger.debug(f"Reset free interactions for user {user_id}.")
    except Exception as e:
        logger.exception(f"Error in reset_interactions handler for user {update.effective_user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred while resetting your interactions.", reply_markup=get_main_menu_keyboard())

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle menu button presses."""
    try:
        user_text = update.message.text
        user_id = update.effective_user.id
        logger.debug(f"Received menu button press from user {user_id}: {user_text}")

        if user_text == '🏠 Home':
            await start(update, context)
        elif user_text == '📚 Help':
            await help_command(update, context)
        elif user_text == '💳 Balance':
            await balance(update, context)
        elif user_text == '🎁 Free Credits':
            await reset_interactions(update, context)
        elif user_text == '🔊 Audio On/Off':
            await toggle_audio(update, context)
        elif user_text in ['😊 Personality', '🎨 Creativity', '💃 Physical Appearance', '🌟 General Awesomeness']:
            # Remove emoji to get the category
            category = user_text.split(' ', 1)[1].lower().replace(' ', '_')
            await generate_compliment(update, context, category)
        else:
            # Handle unexpected inputs
            await update.message.reply_text("Please choose an option from the menu below.", reply_markup=get_main_menu_keyboard())
            logger.debug(f"User {user_id} sent an unexpected input: {user_text}")
    except Exception as e:
        logger.exception(f"Error in menu_handler for user {update.effective_user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred while processing your menu selection.", reply_markup=get_main_menu_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle messages not covered by the menu options."""
    try:
        await update.message.reply_text("Please select a compliment category from the menu below.", reply_markup=get_main_menu_keyboard())
    except Exception as e:
        logger.exception(f"Error in handle_message handler for user {update.effective_user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred.", reply_markup=get_main_menu_keyboard())

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all exceptions."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # Notify the user about the error
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "An unexpected error occurred. Please try again later."
            )
        except Exception as e:
            logger.exception(f"Failed to send error message to user: {e}")

def main() -> None:
    """Start the bot."""
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Define menu options regex filter
    menu_filter = filters.Regex(f"^({'|'.join(MENU_OPTIONS)})$")

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("audio", toggle_audio))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("reset", reset_interactions))  # Optional command

    # Register message handlers
    application.add_handler(MessageHandler(menu_filter, menu_handler))  # Handle menu button presses
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~menu_filter, handle_message))  # Handle unexpected messages

    # Register the error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
