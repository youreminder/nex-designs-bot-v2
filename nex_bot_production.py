"""
NEX DESIGNS PRODUCTION BOT - v4
Complete Solution for 24/7 Cloud Hosting
"""

import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, JobQueue
)
import sqlite3
from pathlib import Path

# ============== CONFIGURATION ==============
BOT_TOKEN = "8616061025:AAE1Zo_gtnFRP0zSQNV00B7a-jg5a4fFBV4"
ADMIN_ID = 1019993930
CHANNEL_ID = -1003965622578

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_FILE = "nex_designs.db"

def init_database():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        service TEXT,
        requirements TEXT,
        timestamp DATETIME,
        status TEXT DEFAULT 'pending'
    )''')
    conn.commit()
    conn.close()

def save_order(user_id, username, service, requirements):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute('''INSERT INTO orders (user_id, username, service, requirements, timestamp, status)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (user_id, username, service, requirements, datetime.now().strftime("%Y-%m-%d %H:%M"), "pending"))
    conn.commit()
    order_id = c.lastrowid
    conn.close()
    return order_id

def get_pending_orders():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE status='pending'")
    orders = c.fetchall()
    conn.close()
    return orders

def update_order_status(order_id, status):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

SERVICES = {
    "poster": {"name": "📢 Social Media Poster", "price": "$5-$15", "time": "24 hrs"},
    "logo": {"name": "✏️ Logo Design", "price": "$20-$50", "time": "48 hrs"},
    "banner": {"name": "🖼️ Banner / Cover", "price": "$8-$20", "time": "24 hrs"},
    "card": {"name": "💼 Business Card", "price": "$10-$25", "time": "24 hrs"},
    "flyer": {"name": "📄 Flyer / Brochure", "price": "$10-$30", "time": "48 hrs"},
    "package": {"name": "📦 Full Brand Package", "price": "$80-$150", "time": "5 days"},
}

DAILY_POSTS = [
    "🎨 *Monday Motivation*\n\nYour brand is the first impression.\nMake it unforgettable.\n\n✅ Order now: @Nex_designs_bot",
    "💡 *Did You Know?*\n\nA professional logo increases trust by 70%.\n\n🔥 Starting from $5\n📩 @Nex_designs_bot",
    "📢 *What We Offer*\n\n🖼️ Posters · 🎯 Logos · 📌 Banners\n\n📩 @Nex_designs_bot",
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎨 Services", callback_data="services")],
        [InlineKeyboardButton("📩 Order", callback_data="order")],
        [InlineKeyboardButton("📞 Contact", callback_data="contact")],
    ]
    await update.message.reply_text(
        "👋 Welcome to Nex Designs!\n\nWe create professional posters, logos, and banners.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "services":
        text = "Services:\n\n"
        keyboard = []
        for key, svc in SERVICES.items():
            text += f"{svc['name']}: {svc['price']}\n"
            keyboard.append([InlineKeyboardButton(f"Order {svc['name']}", callback_data=f"order_{key}")])
        keyboard.append([InlineKeyboardButton("Back", callback_data="home")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("order"):
        context.user_data["ordering"] = True
        await query.edit_message_text("Describe your project:")

    elif data == "contact":
        await query.edit_message_text("Contact: @Nex_designs\nResponse time: 2 hours")

    elif data == "home":
        keyboard = [
            [InlineKeyboardButton("🎨 Services", callback_data="services")],
            [InlineKeyboardButton("📩 Order", callback_data="order")],
            [InlineKeyboardButton("📞 Contact", callback_data="contact")],
        ]
        await query.edit_message_text("Choose:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if context.user_data.get("ordering"):
        order_id = save_order(user.id, user.username or user.first_name, "Custom", text)
        await update.message.reply_text(f"✅ Order #{order_id} received! We'll reply within 2 hours.")
        context.user_data["ordering"] = False

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚨 NEW ORDER #{order_id}\n@{user.username or user.first_name}\n\n{text}"
        )

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("/orders - view\n/complete 1 - mark done\n/post msg - post")

async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    orders = get_pending_orders()
    for o in orders[-5:]:
        await update.message.reply_text(f"Order {o[0]}: @{o[2]}\n{o[4]}")

async def complete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        return
    order_id = int(context.args[0])
    update_order_status(order_id, "completed")
    await update.message.reply_text(f"✅ Order {order_id} complete!")

async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args)
    await context.bot.send_message(CHANNEL_ID, msg)
    await update.message.reply_text("✅ Posted!")

def main():
    init_database()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(CommandHandler("complete", complete_cmd))
    app.add_handler(CommandHandler("post", post_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot running!")
    app.run_polling()

if __name__ == "__main__":
    main()
