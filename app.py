from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

genai.configure(api_key='AIzaSyClx4HUQc2X3rCCx5rEvmNJSWokpK_id2g')

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]

central_history = []

class ChatBot:
    def __init__(self, name, personality, description, image_filename):
        self.name = name
        self.personality = personality
        self.description = description
        self.image_filename = image_filename
        self.muted = False  # Initialize the muted attribute
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            safety_settings=safety_settings,
            generation_config=generation_config,
            system_instruction=f'''
            You will be roleplaying as a character called <name>{{{name}}}</name>. Here are details about this character:
            <personality>{{{personality}}}</personality>
            <description>{{{description}}}</description>
            The setup for our conversation is:
            <scenario>{{You are in a conversation with the user and some other friends. You have met each other after a long time and are catching up.}}</scenario>
            Your goal is to embody this character and engage in a natural conversation based on the provided scenario. To do this effectively:
            1) Stay in character as described in your character description at all times.
            2) Deeply understand and capture the essence of the character's personality traits like <personality>. Let these traits shape your language, tone, opinions and decision-making.
            3) Respond to both the user and other characters, ensuring your replies contribute meaningfully to the conversation. Engage actively and creatively to make the conversation interesting and coherent.
            4) Incorporate relevant details from the character's <description> into your responses where appropriate.
            5) Pay close attention to the provided <scenario> and have your responses make sense in that context. Do not ignore or contradict the setup of the scene you were given.
            6) Respond in a conversational way that continues the natural flow of dialogue. Ask questions, make comments, and express thoughts/opinions as your character would.
            7) Use the provided <examples> as a model for the character's "voice" and manner of interacting.
            Remember to remain fully in character throughout our conversation. Do not break character by commenting on your role or the instructions at any point. Simply respond with what your character would say or do based on the information provided about them. Do not write anything else. Do not include any additional text or meta-comments.'''
        )

    def respond(self):
        if self.muted:
            return f"{self.name} is muted and did not respond."
        response = self.model.generate_content(central_history)
        if not response._result.candidates:
            return "Error: No response generated."
        central_history.append({"role": "user", "parts": [f'{self.name} says: {response.text}']})
        return response.text

    def toggle_mute(self):
        self.muted = not self.muted

    def to_dict(self):
        return {
            "name": self.name,
            "personality": self.personality,
            "description": self.description,
            "image_filename": self.image_filename,
            "muted": self.muted  # Include the muted status
        }

bots = {}
current_bot = None

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/create_bot', methods=['GET', 'POST'])
def create_bot():
    if request.method == 'POST':
        name = request.form['name']
        personality = request.form['personality']
        description = request.form['description']
        image = request.files['image']
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        new_bot = ChatBot(name, personality, description, image_filename)
        bots[name] = new_bot
        return redirect(url_for('home'))
    return render_template('create_bot.html')

@app.route('/chat')
def chat():
    bots_dict = [bot.to_dict() for bot in bots.values()]
    return render_template('chat.html', bots=bots_dict)

@app.route('/select_bot', methods=['POST'])
def select_bot():
    global current_bot
    data = request.json
    bot_name = data['bot_name']
    if bot_name in bots:
        current_bot = bots[bot_name]
        return jsonify({"message": f"Bot {bot_name} selected", "current_bot": bot_name}), 200
    else:
        return jsonify({"message": f"Bot {bot_name} not found"}), 404

@app.route('/toggle_mute', methods=['POST'])
def toggle_mute():
    data = request.json
    bot_name = data['bot_name']
    if bot_name in bots:
        bots[bot_name].toggle_mute()
        return jsonify({"message": f"Bot {bot_name} mute status changed", "muted": bots[bot_name].muted}), 200
    else:
        return jsonify({"message": f"Bot {bot_name} not found"}), 404

@app.route('/send_message', methods=['POST'])
def send_message():
    global current_bot
    if current_bot is None:
        return jsonify({"message": "No bot selected"}), 400

    data = request.json
    message = data['message']
    central_history.append({"role": "user", "parts": [f'User says: {message}']})
    responses = {bot_name: bot.respond() for bot_name, bot in bots.items()}
    return jsonify(responses), 200

if __name__ == '__main__':
    app.run(debug=True)
