import os, base64, asyncio, pathlib
from telethon import TelegramClient, events
from telethon.errors import ChatWriteForbiddenError, ChatForwardsRestrictedError
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

SESSION_NAME = os.environ.get("SESSION_NAME", "forwarder")
SESSION_FILE = f"{SESSION_NAME}.session"

TG_SESSION_BASE64 = os.environ.get("TG_SESSION_BASE64")
if TG_SESSION_BASE64 and not pathlib.Path(SESSION_FILE).exists():
    with open(SESSION_FILE, "wb") as f:
        f.write(base64.b64decode(TG_SESSION_BASE64))

def parse_entity(v: str):
    v = v.strip()
    if v.startswith("-100"):
        return int(v)
    return v

SOURCE = parse_entity(os.environ["SOURCE_CHANNEL"])
TARGET = parse_entity(os.environ["TARGET_CHANNEL"])

FORWARD_MODE = os.environ.get("FORWARD_MODE", "forward").lower()  # forward|copy
BACKFILL_LAST = int(os.environ.get("BACKFILL_LAST", "0"))

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

def build_private_link(msg_id: int):
    # t.me/c/<id_sin_-100>/<msg_id>
    if isinstance(SOURCE, int) and str(SOURCE).startswith("-100"):
        return f"https://t.me/c/{str(SOURCE)[4:]}/{msg_id}"
    return None

async def repost_text_only(msg):
    text = (getattr(msg, "text", None) or getattr(msg, "message", None) or "") or (getattr(msg, "caption", None) or "")
    if not text:
        print("⚠️ Solo media y protegido: no se puede replicar.")
        return
    link = build_private_link(msg.id)
    if link:
        text = f"{text}\n\n[Mensaje original]({link})"
    await client.send_message(TARGET, text, link_preview=False)
    print(f"📝 Reposteado como TEXTO id={msg.id}")

async def manual_copy(msg):
    text = (getattr(msg, "text", None) or getattr(msg, "message", None) or "") or (getattr(msg, "caption", None) or "")
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
            try:
                _ = msg.copy_to
                await msg.copy_to(TARGET)  # type: ignore[attr-defined]
                print(f"➡️ Copiado (copy_to) id={msg.id}")
            except AttributeError:
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
