import os, asyncio, subprocess, signal, uuid, time, json, threading
from pathlib import Path
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

# --- Fake Web Server for Render (VERY IMPORTANT) ---
app_web = Flask(__name__)
@app_web.route('/')
def home():
    return "HostBot is ONLINE ✅"
@app_web.route('/ping')
def ping():
    return "pong"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()
# ----------------------------------------------------

TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
BASE = Path("hosted_bots")
BASE.mkdir(exist_ok=True)
DB_FILE = Path("hosted_db.json")

WAITING_FILE, WAITING_TOKEN, WAITING_NAME = range(3)

def load_db():
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text())
    return {}
def save_db(db):
    DB_FILE.write_text(json.dumps(db, indent=2))

processes = {}

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Host New Bot", callback_data="host")],
        [InlineKeyboardButton("📦 My Hosted Bots", callback_data="mybots")],
        [InlineKeyboardButton("❓ How it works", callback_data="help")],
    ])

def bot_controls(bot_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Start", callback_data=f"start:{bot_id}"),
         InlineKeyboardButton("⏹️ Stop", callback_data=f"stop:{bot_id}")],
        [InlineKeyboardButton("🔄 Restart", callback_data=f"restart:{bot_id}"),
         InlineKeyboardButton("🗑️ Delete", callback_data=f"delete:{bot_id}")],
        [InlineKeyboardButton("📋 Logs", callback_data=f"logs:{bot_id}"),
         InlineKeyboardButton("📊 Status", callback_data=f"status:{bot_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="mybots")],
    ])

def run_bot_file(bot_id, file_path, token=""):
    env = os.environ.copy()
    if token: env["BOT_TOKEN"] = token
    log_file = open(BASE / f"{bot_id}.log", "a")
    proc = subprocess.Popen(["python", str(file_path)], stdout=log_file, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    processes[bot_id] = proc
    return proc

def stop_process(bot_id):
    proc = processes.get(bot_id)
    if proc and proc.poll() is None:
        try: os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except: proc.terminate()
    processes.pop(bot_id, None)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 *Welcome to HostBot!*\n\nI can host YOUR bot — FREE, 24/7.\n\nJust upload your `.py` file.", parse_mode="Markdown", reply_markup=main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    user_id = str(q.from_user.id)
    db = load_db()
    user_bots = db.get(user_id, {})
    if data == "host":
        await q.message.reply_text("📤 Send me your bot's `.py` file now.", parse_mode="Markdown")
        return WAITING_FILE
    if data == "help":
        await q.message.reply_text("❓ 1️⃣ Tap Host New Bot\n2️⃣ Upload .py file\n3️⃣ Give name\n4️⃣ Send Token\n5️⃣ Bot goes ONLINE ✅", parse_mode="Markdown", reply_markup=main_menu())
    if data == "mybots":
        if not user_bots:
            await q.message.reply_text("📦 No hosted bots yet.", reply_markup=main_menu()); return
        text = "📦 *Your Hosted Bots:*\n\n"
        kb = []
        for bid, info in user_bots.items():
            proc = processes.get(bid)
            alive = proc and proc.poll() is None
            status = "🟢 ONLINE" if alive else "🔴 OFFLINE"
            text += f"• *{info['name']}* — {status}\n"
            kb.append([InlineKeyboardButton(f"{info['name']} — {status}", callback_data=f"manage:{bid}")])
        kb.append([InlineKeyboardButton("⬅️ Menu", callback_data="menu")])
        await q.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    if data == "menu":
        await q.message.reply_text("Choose:", reply_markup=main_menu())
    if data.startswith("manage:"):
        bid = data.split(":")[1]; info = user_bots.get(bid)
        if not info: return
        proc = processes.get(bid); alive = proc and proc.poll() is None
        await q.message.reply_text(f"🤖 *{info['name']}*\nStatus: {'🟢 ONLINE' if alive else '🔴 OFFLINE'}\nFile: `{info['file']}`", parse_mode="Markdown", reply_markup=bot_controls(bid))
    if data.startswith("start:"):
        bid = data.split(":")[1]; info = user_bots.get(bid)
        if info and bid not in processes:
            run_bot_file(bid, BASE / info['file'], info.get('token',''))
            await q.message.reply_text(f"✅ *{info['name']}* started! 🟢", parse_mode="Markdown", reply_markup=bot_controls(bid))
        else: await q.message.reply_text("⚠️ Already running.")
    if data.startswith("stop:"):
        bid = data.split(":")[1]; stop_process(bid)
        await q.message.reply_text("⏹️ Bot stopped.", reply_markup=bot_controls(bid))
    if data.startswith("restart:"):
        bid = data.split(":")[1]; info = user_bots.get(bid); stop_process(bid); await asyncio.sleep(1); run_bot_file(bid, BASE / info['file'], info.get('token',''))
        await q.message.reply_text(f"🔄 *{info['name']}* restarted! 🟢", parse_mode="Markdown", reply_markup=bot_controls(bid))
    if data.startswith("delete:"):
        bid = data.split(":")[1]; stop_process(bid); user_bots.pop(bid, None); db[user_id]=user_bots; save_db(db)
        await q.message.reply_text("🗑️ Deleted.", reply_markup=main_menu())
    if data.startswith("status:"):
        bid = data.split(":")[1]; info = user_bots.get(bid); proc = processes.get(bid); alive = proc and proc.poll() is None
        await q.message.reply_text(f"📊 *{info['name']}*\nStatus: {'🟢 ONLINE' if alive else '🔴 OFFLINE'}", parse_mode="Markdown", reply_markup=bot_controls(bid))
    if data.startswith("logs:"):
        bid = data.split(":")[1]; log_path = BASE / f"{bid}.log"
        logs = log_path.read_text()[-2000:] if log_path.exists() else "No logs yet."
        await q.message.reply_text(f"📋 *Logs:*\n```\n{logs}\n```", parse_mode="Markdown", reply_markup=bot_controls(bid))

async def host_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📤 Send me your bot's `.py` file now.")
    return WAITING_FILE
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".py"):
        await update.message.reply_text("❌ Send a `.py` file only."); return WAITING_FILE
    file = await doc.get_file(); bot_id = str(uuid.uuid4())[:8]
    save_path = BASE / f"{bot_id}_{doc.file_name}"
    await file.download_to_drive(save_path)
    context.user_data["pending_file"]=str(save_path); context.user_data["pending_bot_id"]=bot_id
    await update.message.reply_text(f"✅ Received `{doc.file_name}`\n\nNow send a *name* for your bot.", parse_mode="Markdown")
    return WAITING_NAME
async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pending_name"]=update.message.text.strip()
    await update.message.reply_text("🔑 Now send your bot's *Token*\n\nOr send /skip", parse_mode="Markdown")
    return WAITING_TOKEN
async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    if token == "/skip": token = ""
    return await finish_hosting(update, context, token)
async def finish_hosting(update, context, token):
    user_id=str(update.effective_user.id); bot_id=context.user_data["pending_bot_id"]; file_path=context.user_data["pending_file"]; name=context.user_data["pending_name"]
    db=load_db(); db.setdefault(user_id,{})[bot_id]={"name":name,"file":Path(file_path).name,"token":token,"started":time.strftime("%Y-%m-%d %H:%M")}; save_db(db)
    run_bot_file(bot_id, file_path, token)
    await update.message.reply_text(f"🎉 *SUCCESS! Bot is LIVE!*\n\n🤖 *{name}*\n🟢 ONLINE\n🆔 `{bot_id}`", parse_mode="Markdown", reply_markup=bot_controls(bot_id))
    return ConversationHandler.END
async def mybots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use buttons from /start")
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=main_menu()); return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("host", host_cmd), CallbackQueryHandler(button_handler, pattern="^host$")],
        states={WAITING_FILE:[MessageHandler(filters.Document.ALL, receive_file)], WAITING_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)], WAITING_TOKEN:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token)]},
        fallbacks=[CommandHandler("cancel", cancel)], allow_reentry=True)
    app.add_handler(CommandHandler("start", start)); app.add_handler(CommandHandler("mybots", mybots_cmd)); app.add_handler(conv); app.add_handler(CallbackQueryHandler(button_handler))
    print("HostBot running..."); app.run_polling()
if __name__ == "__main__":
    main()
