from datetime import datetime
import urllib.request
from plugins.base_plugin.base_plugin import BasePlugin
from openai import OpenAI
from PIL import Image
from io import BytesIO
import requests
import logging

logger = logging.getLogger(__name__)

IMAGE_MODELS = ["dall-e-3", "dall-e-2"]
DEFAULT_IMAGE_MODEL = "dall-e-3"

IMAGE_QUALITIES = ["hd", "standard"]
DEFAULT_IMAGE_QUALITY = "standard"
class AIImage2(BasePlugin):
    def generate_image(self, settings, device_config):

        api_key = device_config.load_env_key("OPEN_AI_SECRET")
        if not api_key:
            raise RuntimeError("OPEN AI API Key not configured.")

        text_prompt = settings.get("inputText", "")
        today = datetime.today().strftime('%A, %B %d, %Y')
        text_prompt = text_prompt.replace("$TODAY",today)
	
        image_model = settings.get('imageModel', DEFAULT_IMAGE_MODEL)
        if image_model not in IMAGE_MODELS:
            image_model = DEFAULT_IMAGE_MODEL
        image_quality = settings.get('quality', DEFAULT_IMAGE_QUALITY)
        if image_quality not in IMAGE_QUALITIES:
            image_quality = DEFAULT_IMAGE_QUALITY
        randomize_prompt = settings.get('randomizePrompt') == 'true'

        image = None
        try:
            ai_client = OpenAI(api_key = api_key)
            if randomize_prompt:
                # text_prompt = AIImage2.fetch_image_prompt(ai_client, text_prompt)
                text_prompt = AIImage2.get_event(ai_client)
                AIImage2.send_message(device_config, text_prompt)
            image = AIImage2.fetch_image(
                ai_client,
                text_prompt,
                model=image_model,
                quality=image_quality,
                orientation=device_config.get_config("orientation")
            )
        except Exception as e:
            logger.error(f"Failed to make Open AI request: {str(e)}")
            raise RuntimeError("Open AI request failure, please check logs.")
        return image
    
    @staticmethod
    def send_message(device_config, message):
        bot_token = device_config.load_env_key("TELEGRAM_BOT_TOKEN")
        chat_id = device_config.load_env_key("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            logger.error("Telegram bot token or chat ID not configured.")
            return
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message
        }
        try:
            requests.post(url, data=data)
        except Exception as e:
            logger.error(f"Failed to send message to Telegram: {str(e)}")



    @staticmethod
    def fetch_image(ai_client, prompt, model="dalle-e-3", quality="standard", orientation="horizontal"):
        logger.info(f"Generating image for prompt: {prompt}, model: {model}, quality: {quality}")
        prompt += (
            ". The image should fully occupy the entire canvas without any frames, "
            "borders, or cropped areas. No blank spaces or artificial framing."
        )
        prompt += (
            "Focus on simplicity, bold shapes, and strong contrast to enhance clarity "
            "and visual appeal. Avoid excessive detail or complex gradients, ensuring "
            "the design works well with flat, vibrant colors."
        )
        prompt += (
            "the image should contain the date or the event or the person depicted in the image"
        )
        args = {
            "model": model,
            "prompt": prompt,
            "size": "1024x1024",
            "quality": "standard"
        }
        if model == "dall-e-3":
            args["size"] = "1792x1024" if orientation == "horizontal" else "1024x1792"
            args["quality"] = quality

        response = ai_client.images.generate(**args)
        image_url = response.data[0].url
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))

        return img

    @staticmethod
    def fetch_image_prompt(ai_client, from_prompt=None):
        logger.info(f"Getting random image prompt...")

        system_content = (
            "You are a creative assistant generating extremely random and unique image prompts. "
            "Avoid common themes. Focus on unexpected, unconventional, and bizarre combinations "
            "of art style, medium, subjects, time periods, and moods. No repetition. Prompts "
            "should be 20 words or less and specify random artist, movie, tv show or time period "
            "for the theme. Do not provide any headers or repeat the request, just provide the "
            "updated prompt in your response."
        )
        user_content = (
            "Give me a completely random image prompt, something unexpected and creative! "
            "Let's see what your AI mind can cook up!"
        )
        if from_prompt and from_prompt.strip():
            system_content = (
                "You are a creative assistant specializing in generating highly descriptive "
                "and unique prompts for creating images. When given a short or simple image "
                "description, your job is to rewrite it into a more detailed, imaginative, "
                "and descriptive version that captures the essence of the original while "
                "making it unique and vivid. Avoid adding irrelevant details but feel free "
                "to include creative and visual enhancements. Avoid common themes. Focus on "
                "unexpected, unconventional, and bizarre combinations of art style, medium, "
                "subjects, time periods, and moods. Do not provide any headers or repeat the "
                "request, just provide your updated prompt in the response. Prompts "
                "should be 20 words or less and specify random artist, movie, tv show or time "
                "period for the theme."
            )
            user_content = (
                f"Original prompt: \"{from_prompt}\"\n"
                "Rewrite it to make it more detailed, imaginative, and unique while staying "
                "true to the original idea. Include vivid imagery and descriptive details. "
                "Avoid changing the subject of the prompt."
            )

        # Make the API call
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            temperature=1
        )

        prompt = response.choices[0].message.content.strip()
        logger.info(f"Generated random image prompt: {prompt}")
        return prompt

    @staticmethod
    def get_event(ai_client):
        logger.info(f"Getting today data prompt...")
        today = datetime.today().strftime('%A, %B %d, %Y')
        system_content = (
            "You are a creative assistant generating extremely random and unique image prompts. "
            "Topics in order of importance: mathematics, science, music, national holidays, historical events, birthdays, world events"
            "Do not provide any headers or repeat the request, just provide the prompt in your response."
            "You want to convay positive feelings and emotions in the image"
            "so you avoid dark or negative themes."
        )
        user_content = (
            f"Today is {today}, pick a random event from the following topics: mathematics, science, music, national holidays, historical events, birthdays, world events"
            "Generate an image prompt based on the event you choose."
            "The image should be wide and horizontal, with a resolution of 1792x1024."
        )

        # Make the API call
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            temperature=0.9
        )

        prompt = response.choices[0].message.content.strip()
        logger.info(f"Generated random image prompt: {prompt}")
        return prompt