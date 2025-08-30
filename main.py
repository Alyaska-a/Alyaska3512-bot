import os, time, logging, asyncio
from functools import wraps
from typing import Callable, Awaitable

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from modules.web import web_search, google_search, bing_search, wiki_summary
from modules.quantum import run_preset_circuit, run_openqasm, backends_info
from modules.llm import ask_once, chat_reply, reset_chat, llm_status

BOT_NAME = os.getenv("BOT_NAME", "LockedQuantumBot")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

SECRET_LOGIN = os.getenv("SECRET_LOGIN", "")
SECRET_PASSWORD = os.getenv("SECRET_PASSWORD", "")
LOGIN_TTL_HOURS = int(os.getenv("LOGIN_TTL_HOURS", "12"))

if not BOT_TOKEN or OWNER_ID == 0 or not SECRET_LOGIN or not SECRET_PASSWORD:
    raise SystemExit("Missing required env: BOT_TOKEN, OWNER_ID, SECRET_LOGIN, SECRET_PASSWORD")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(BOT_NAME)

def redact(text: str) -> str:
    for key in ["BOT_TOKEN","OPENAI_API_KEY","ANTHROPIC_API_KEY","IBM_QUANTUM_TOKEN","SECRET_PASSWORD","SECRET_LOGIN","GOOGLE_CSE_KEY","BING_KEY"]:
        v = os.getenv(key)
        if v:
            text = text.replace(v, f"[{key}_REDACTED]")
    return text

# ===== Access Control (2-step) =====
session = {"stage": 0, "logged": False, "login_ts": 0}
# stage: 0 = not started, 1 = login OK, waiting password, 2 = fully logged

def _is_owner(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == OWNER_ID

def owner_only(fn: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable]):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_owner(update):
            return
        return await fn(update, context)
    return wrapper

def require_login(fn: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable]):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_owner(update):
            return
        # TTL auto logout
        ttl = LOGIN_TTL_HOURS * 3600
        if session["logged"] and (time.time() - session["login_ts"] > ttl):
            session.update({"stage": 0, "logged": False})
        if not session["logged"]:
            await update.effective_message.reply_text("🚫 Доступ закрыт. Шаги входа: `/login <логин>` → `/pass <пароль>`", parse_mode=ParseMode.MARKDOWN)
            return
        return await fn(update, context)
    return wrapper

@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🔐 {BOT_NAME} — приватный бот V3.\n"
        "Вход: `/login <логин>` → затем `/pass <пароль>`\n\n"
        "Команды:\n"
        "• /status — статус интеграций\n"
        "• /changelogin <новый>, /changepass <новый>\n"
        "• /ask <вопрос>\n"
        "• /chat <сообщение> — диалог; /reset — сброс\n"
        "• /web <запрос>, /google <запрос>, /bing <запрос>, /wiki <термин>\n"
        "• /quantum devices | preset <bell|ghz|qft> [qubits] | run <openqasm>\n"
        "• /logout — выйти",
        parse_mode=ParseMode.MARKDOWN
    )

@owner_only
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /login <логин>")
        return
    if args[0] == SECRET_LOGIN:
        session["stage"] = 1
        await update.message.reply_text("✅ Логин принят. Теперь введи `/pass <пароль>`")
    else:
        await update.message.reply_text("❌ Неверный логин.")

@owner_only
async def passwd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if session["stage"] != 1:
        await update.message.reply_text("Сначала введи логин: /login <логин>")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /pass <пароль>")
        return
    if args[0] == SECRET_PASSWORD:
        session.update({"stage": 2, "logged": True, "login_ts": time.time()})
        await update.message.reply_text("🔓 Доступ разрешён.")
    else:
        await update.message.reply_text("❌ Неверный пароль.")

@owner_only
async def changelogin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not session["logged"]:
        await update.message.reply_text("Сначала войди.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /changelogin <новый_логин>")
        return
    global SECRET_LOGIN
    SECRET_LOGIN = context.args[0]
    session.update({"stage": 0, "logged": False})
    await update.message.reply_text("🔑 Логин изменён. Выполни новый вход.")

@owner_only
async def changepass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not session["logged"]:
        await update.message.reply_text("Сначала войди.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /changepass <новый_пароль>")
        return
    global SECRET_PASSWORD
    SECRET_PASSWORD = context.args[0]
    session.update({"stage": 0, "logged": False})
    await update.message.reply_text("🔑 Пароль изменён. Выполни новый вход.")

@owner_only
async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session.update({"stage": 0, "logged": False})
    await update.message.reply_text("👋 Сессия завершена.")

@require_login
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = llm_status() + "\n" + backends_info()
    await update.message.reply_text(txt)

@require_login
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /ask <вопрос>")
        return
    prompt = " ".join(context.args)
    try:
        ans = await ask_once(prompt)
    except Exception as e:
        log.exception("ask_once failed: %s", redact(str(e)))
        ans = "⚠️ Ошибка LLM."
    await update.message.reply_text(ans)

@require_login
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /chat <сообщение>")
        return
    msg = " ".join(context.args)
    try:
        ans = await chat_reply(msg)
    except Exception as e:
        log.exception("chat failed: %s", redact(str(e)))
        ans = "⚠️ Ошибка LLM."
    await update.message.reply_text(ans)

@require_login
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_chat()
    await update.message.reply_text("🧹 Контекст очищен.")

@require_login
async def web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /web <запрос>")
        return
    q = " ".join(context.args)
    try:
        res = await web_search(q)
    except Exception as e:
        log.exception("web_search error: %s", redact(str(e)))
        res = "⚠️ Ошибка веб-поиска."
    await update.message.reply_text(res, disable_web_page_preview=True)

@require_login
async def google(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /google <запрос>")
        return
    q = " ".join(context.args)
    await update.message.reply_text(await google_search(q), disable_web_page_preview=True)

@require_login
async def bing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /bing <запрос>")
        return
    q = " ".join(context.args)
    await update.message.reply_text(await bing_search(q), disable_web_page_preview=True)

@require_login
async def wiki(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /wiki <термин>")
        return
    q = " ".join(context.args)
    await update.message.reply_text(await wiki_summary(q), disable_web_page_preview=True)

@require_login
async def quantum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /quantum devices | preset <bell|ghz|qft> [qubits] | run <openqasm>")
        return
    sub = context.args[0].lower()
    if sub == "devices":
        await update.message.reply_text(backends_info())
    elif sub == "preset":
        if len(context.args) < 2:
            await update.message.reply_text("Укажи тип: bell|ghz|qft")
            return
        preset = context.args[1]
        qubits = int(context.args[2]) if len(context.args) > 2 else (2 if preset=='bell' else 3)
        await update.message.reply_text(await run_preset_circuit(preset, qubits))
    elif sub == "run":
        qasm = " ".join(context.args[1:])
        if not qasm.strip():
            await update.message.reply_text("Пришли OpenQASM 3.0 после `run`.")
            return
        await update.message.reply_text(await run_openqasm(qasm))
    else:
        await update.message.reply_text("Неизвестная подкоманда.")

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_owner(update):
        await update.message.reply_text("Неизвестная команда. Введите /start")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("pass", passwd))
    app.add_handler(CommandHandler("changelogin", changelogin))
    app.add_handler(CommandHandler("changepass", changepass))
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("chat", chat))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("web", web))
    app.add_handler(CommandHandler("google", google))
    app.add_handler(CommandHandler("bing", bing))
    app.add_handler(CommandHandler("wiki", wiki))
    app.add_handler(CommandHandler("quantum", quantum))
    app.add_handler(MessageHandler(filters.ALL, fallback))
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    asyncio.run(asyncio.to_thread(main))
