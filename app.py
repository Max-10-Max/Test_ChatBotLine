from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, MessageEvent, TextMessage, RichMenu, RichMenuArea, URIAction, QuickReply, QuickReplyButton, MessageAction
import json
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)

# LINE Messaging API
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# Load schedule with error handling
try:
    with open("schedule.json", "r") as f:
        schedule_data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    schedule_data = []  # Initialize with an empty list if the file is missing or empty

# Initialize scheduler
scheduler = BackgroundScheduler()

# Function to send reminders
def send_reminders():
    now = datetime.now()
    for event in schedule_data:
        event_time = datetime.strptime(event["time"], "%Y-%m-%d %H:%M")
        if now >= event_time and now <= event_time + timedelta(minutes=1):  # Check within the next minute
            line_bot_api.push_message(
                event["user_id"],
                TextSendMessage(text=f"Reminder: {event['title']} is happening now! ({event['time']})")
            )

# Schedule the job every minute
scheduler.add_job(send_reminders, 'interval', minutes=1)
scheduler.start()

@app.route("/callback", methods=["POST"])
def callback():
    # Get request header and body
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# Function to create Rich Menu
def create_rich_menu():
    # Create Rich Menu
    rich_menu = RichMenu(
        size={"width": 2500, "height": 1686},
        selected=False,
        name="Identity Selection",
        chat_bar_text="Tap to select identity",
        areas=[
            RichMenuArea(
                bounds={"x": 0, "y": 0, "width": 2500, "height": 1686},
                action=URIAction(label="Start Identity Selection", uri="line://app/your_deep_link_here")
            )
        ]
    )
    rich_menu_id = line_bot_api.create_rich_menu(rich_menu)

    # Upload an image for the Rich Menu
    with open("rich_menu_image.jpg", "rb") as f:
        line_bot_api.set_rich_menu_image(rich_menu_id, "image/jpeg")

    # Set Rich Menu alias
    line_bot_api.set_rich_menu_alias(rich_menu_id, "identity_selection_alias")
    return rich_menu_id

# Create the rich menu when the app starts
create_rich_menu()

# Handle messages
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    message_text = event.message.text

    if message_text.lower() == "max":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="สุดหล่อ")
        )
        return

    if message_text.lower() == "m":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="MAX")
        )
        return
    
    if message_text.lower() == "d":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="เดียร์ เองจ้า")
        )
        return

    if message_text.lower() == "identity":
        # Ask for identity selection with Quick Reply
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="Please choose your role:",
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(action=MessageAction(label="STUDENT", text="STUDENT")),
                        QuickReplyButton(action=MessageAction(label="INSTRUCTOR", text="INSTRUCTOR")),
                        QuickReplyButton(action=MessageAction(label="GENERAL", text="GENERAL")),
                        QuickReplyButton(action=MessageAction(label="STAFF", text="STAFF")),
                        QuickReplyButton(action=MessageAction(label="ANONYMOUS", text="ANONYMOUS"))
                    ]
                )
            )
        )

    if message_text.lower().startswith("add schedule"):
        _, title, date, time = message_text.split("|")
        new_event = {
            "title": title.strip(),
            "time": f"{date.strip()} {time.strip()}",
            "user_id": user_id
        }
        schedule_data.append(new_event)
        with open("schedule.json", "w") as f:
            json.dump(schedule_data, f, indent=4)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="✅ Schedule added successfully!")
        )


@app.route('/')
def home():
    return "Welcome to the home page!"

if __name__ == "__main__":
    app.run(debug=True)
