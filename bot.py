# ============================================================
#  BOT DE TELEGRAM CON CLAUDE — compatible Python 3.14
# ============================================================

import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

from anthropic import Anthropic
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

cliente_claude = Anthropic(api_key=ANTHROPIC_API_KEY)

historiales = {}

PERSONALIDAD = """
Eres un asistente personal útil, directo y claro.
Respondes en español siempre.
Eres conciso: no das respuestas largas si no son necesarias.
Si no sabes algo, lo dices claramente.
"""

MAX_MENSAJES_HISTORIAL = 20


async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    nombre  = update.effective_user.first_name
    historiales[user_id] = []
    await update.message.reply_text(
        f"¡Hola {nombre}! Soy tu asistente personal con IA.\n\n"
        "Puedes preguntarme lo que quieras.\n\n"
        "Comandos:\n"
        "/start — reinicia la conversación\n"
        "/borrar — borra el historial\n"
        "/ayuda — muestra esta ayuda"
    )

async def comando_borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    historiales[update.effective_user.id] = []
    await update.message.reply_text("✅ Historial borrado. Empezamos desde cero.")

async def comando_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Escríbeme cualquier mensaje y te respondo.\n\n"
        "/start — nueva conversación\n"
        "/borrar — borra el contexto\n"
        "/ayuda — este mensaje"
    )

async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id         = update.effective_user.id
    mensaje_usuario = update.message.text

    if user_id not in historiales:
        historiales[user_id] = []

    historiales[user_id].append({"role": "user", "content": mensaje_usuario})

    if len(historiales[user_id]) > MAX_MENSAJES_HISTORIAL:
        historiales[user_id] = historiales[user_id][-MAX_MENSAJES_HISTORIAL:]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        respuesta = cliente_claude.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=PERSONALIDAD,
            messages=historiales[user_id]
        )
        texto_respuesta = respuesta.content[0].text
        historiales[user_id].append({"role": "assistant", "content": texto_respuesta})
        await update.message.reply_text(texto_respuesta)

    except Exception as error:
        logger.error(f"Error: {error}")
        await update.message.reply_text("❌ Error al procesar tu mensaje. Inténtalo de nuevo.")


async def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ Falta TELEGRAM_TOKEN en el archivo .env")
    if not ANTHROPIC_API_KEY:
        raise ValueError("❌ Falta ANTHROPIC_API_KEY en el archivo .env")

    print("🤖 Arrancando el bot...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",  comando_start))
    app.add_handler(CommandHandler("borrar", comando_borrar))
    app.add_handler(CommandHandler("ayuda",  comando_ayuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))

    print("✅ Bot en marcha. Escribe /start en Telegram para empezar.")
    print("   Pulsa Ctrl+C para detenerlo.")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    # Mantiene el bot corriendo hasta que pulses Ctrl+C
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
