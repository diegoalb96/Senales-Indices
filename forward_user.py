import os, base64, asyncio, pathlib
from telethon import TelegramClient, events
from telethon.errors import ChatWriteForbiddenError, ChatForwardsRestrictedError
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

import re

def clean_text(text: str) -> str:
    """
    Limpia cabeceras como 'SYNTHETIC SHARK' al inicio del mensaje.
    También quita el emoji 🔔 si está delante.
    Puedes configurar cabeceras extra con CLEAN_PREFIXES (separadas por coma).
    """
    prefixes = [s.strip() for s in os.environ.get("CLEAN_PREFIXES", "").split(",") if s.strip()]

    # Si no defines CLEAN_PREFIXES, aplica por defecto a 'SYNTHETIC SHARK'
    if not prefixes:
        prefixes = ["SYNTHETIC SHARK"]

    # Construimos patrones: inicio de texto, opcional emoji / símbolo + espacios, cabecera, salto(s) de línea
    patterns = [rf'^\s*(?:[^\w\s]|\uFE0F)?\s*{re.escape(p)}\s*\n+' for p in prefixes]

    cleaned = text
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

SESSION_NAME = os.environ.get("SESSION_NAME", "forwarder")
SESSION_FILE = f"{SESSION_NAME}.session"

STRING_SESSION = os.environ.get("STRING_SESSION")

TG_SESSION_BASE64 = os.environ.get("TG_SESSION_BASE64")
if not TG_SESSION_BASE64:
    parts = []
    for i in range(1, 10):
        v = os.environ.get(f"TG_SESSION_B64_P{i}")
        if v: parts.append(v)
    if parts:
        TG_SESSION_BASE64 = "".join(parts)

if TG_SESSION_BASE64 and not pathlib.Path(SESSION_FILE).exists():
    try:
        with open(SESSION_FILE, "wb") as f:
            f.write(base64.b64decode(TG_SESSION_BASE64))
    except Exception as e:
        print("⚠️ No se pudo reconstruir el archivo .session:", repr(e))

def parse_entity(v: str):
    v = v.strip()
    if v.startswith("-100"):
        return int(v)
    return v

SOURCE = parse_entity(os.environ["SOURCE_CHANNEL"])
TARGET = parse_entity(os.environ["TARGET_CHANNEL"])

FORWARD_MODE = os.environ.get("FORWARD_MODE", "forward").lower()
BACKFILL_LAST = int(os.environ.get("BACKFILL_LAST", "0"))

if STRING_SESSION:
    session_arg = StringSession(STRING_SESSION)
else:
    session_arg = SESSION_NAME

client = TelegramClient(session_arg, API_ID, API_HASH)

def build_private_link(msg_id: int):
    if isinstance(SOURCE, int) and str(SOURCE).startswith("-100"):
        return f"https://t.me/c/{str(SOURCE)[4:]}/{msg_id}"
    return None

async def repost_text_only(msg):
    text = (getattr(msg, "text", None) or getattr(msg, "message", None) or "") or (getattr(msg, "caption", None) or "")
    text = clean_text(text)
    if not text:
        print("⚠️ Solo multimedia y protegido: no se puede replicar.")
        return
    link = build_private_link(msg.id)
    if link:
        text = f"{text}\n\n[Mensaje original]({link})"
    await client.send_message(TARGET, text, link_preview=False)
    print(f"📝 Reposteado como TEXTO id={msg.id}")

async def manual_copy(msg):
    text = (getattr(msg, "text", None) or getattr(msg, "message", None) or "") or (getattr(msg, "caption", None) or "")
    text = clean_text(text)
    if getattr(msg, "media", None):
        try:
            path = await msg.download_media()
            await client.send_file(TARGET, path, caption=(text or None))
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
            print(f"📎 Copiado como archivo id={msg.id}")
        except Exception:
            await repost_text_only(msg)
    else:
        if text:
            await client.send_message(TARGET, text, link_preview=False)
            print(f"📝 Copiado como texto id={msg.id}")
        else:
            print(f"⚠️ Mensaje vacío/no copiable id={msg.id}")

async def safe_forward(msg):
    try:
        if FORWARD_MODE == "copy":
            await manual_copy(msg)
        else:
            await client.forward_messages(TARGET, msg)
            print(f"➡️ Reenviado id={msg.id}")
    except ChatForwardsRestrictedError:
        await repost_text_only(msg)
    except ChatWriteForbiddenError:
        print("❌ No tengo permiso para escribir en el DESTINO. Hazte admin.")
    except Exception as e:
        print("❌ Error reenviando:", repr(e))

@client.on(events.NewMessage(chats=SOURCE))
async def handler(event):
    if event.message and event.message.action:
        return
    await safe_forward(event.message)

async def backfill_if_needed():
    if BACKFILL_LAST > 0:
        print(f"🔁 Copiando últimos {BACKFILL_LAST} mensajes…")
        async for m in client.iter_messages(SOURCE, limit=BACKFILL_LAST, reverse=True):
            if m and not m.action:
                await safe_forward(m)
                await asyncio.sleep(0.25)
        print("✅ Backfill completado.")

async def main():
    await client.start()
    await backfill_if_needed()
    print("🚀 Forwarder listo. Escuchando mensajes nuevos…")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
