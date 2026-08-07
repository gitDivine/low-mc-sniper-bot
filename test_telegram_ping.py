import asyncio
import httpx

bot_token = "8468608767:AAGlVNKWcrB59Ldh86Q_OMhFaRrcVRVEOE8"
chat_id = "5815606172"

async def test():
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🚀 <b>Low-MC Sniper Bot Telegram Connection Verified!</b>\n\nYour shadow runner is connected and ready.",
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "📊 Get CSV Data", "callback_data": "get_csv"}, {"text": "📈 View Report", "callback_data": "get_report"}]
            ]
        }
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload)
        print("Status code:", res.status_code)
        print("Response:", res.text)

asyncio.run(test())
