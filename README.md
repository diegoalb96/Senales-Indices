# Telegram Forwarder (usuario personal) — v2

- Reenvía o copia mensajes de un canal/grupo a otro con tu cuenta personal.
- Si el origen tiene 'Restringir guardar contenido', republica **solo el TEXTO** con enlace al original (los medios protegidos no pueden copiarse).

## Pasos rápidos
1) `pip install -r requirements.txt`
2) Copia `.env.example` a `.env` y pon tus valores (`API_ID`, `API_HASH`, `SOURCE_CHANNEL`, `TARGET_CHANNEL`, etc.).
3) `python forward_user.py` (login con tu número).
4) Opcional: `BACKFILL_LAST=5` para traer los últimos N al iniciar.
5) Para Railway: convierte `forwarder.session` a Base64 y pega en `TG_SESSION_BASE64`.
