import subprocess

# Run the Flask app
flask_process = subprocess.Popen(['python', 'app.py'])

# Run the Discord bot
bot_process = subprocess.Popen(['python', 'bot.py'])

# Wait for both processes to complete
flask_process.wait()
bot_process.wait()
