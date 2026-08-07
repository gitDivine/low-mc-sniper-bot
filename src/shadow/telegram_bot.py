"""
Telegram Bot Integration for Shadow Mode Runner.
Handles startup alerts, hourly heartbeats, interactive buttons,
and on-demand CSV data file delivery directly inside Telegram.
"""
import asyncio
import html
import logging
from pathlib import Path
from typing import Any, Optional
import httpx

from config.settings import settings

logger = logging.getLogger("LowMCSniper.TelegramBot")


class TelegramNotifier:
    """Async Telegram notification and command listener service."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        self.chat_id = chat_id or getattr(settings, "TELEGRAM_CHAT_ID", None)
        self.enabled = bool(self.bot_token and self.chat_id)
        self.offset = 0

        if self.enabled:
            logger.info("Telegram Notifier initialized successfully.")
        else:
            logger.info("Telegram Notifier disabled (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not provided).")

    @property
    def base_url(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(self, text: str, reply_markup: Optional[dict[str, Any]] = None) -> bool:
        """Sends a text message to Telegram with optional inline keyboard buttons."""
        if not self.enabled:
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    async def send_document(self, file_path: Path, caption: str = "") -> bool:
        """Uploads a file (CSV/JSON) directly to Telegram chat."""
        if not self.enabled or not file_path.exists():
            return False

        url = f"{self.base_url}/sendDocument"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(file_path, "rb") as f:
                    files = {"document": (file_path.name, f, "text/csv")}
                    data = {"chat_id": self.chat_id, "caption": caption}
                    res = await client.post(url, data=data, files=files)
                    return res.status_code == 200
        except Exception as e:
            logger.error(f"Error sending Telegram document {file_path}: {e}")
            return False

    def get_inline_keyboard(self) -> dict[str, Any]:
        """Generates inline action buttons for quick data retrieval in Telegram."""
        return {
            "inline_keyboard": [
                [
                    {"text": "📊 Get CSV Data", "callback_data": "get_csv"},
                    {"text": "📈 View Report", "callback_data": "get_report"},
                ],
                [
                    {"text": "🔄 Check Status", "callback_data": "get_status"},
                ]
            ]
        }

    async def send_startup_notification(self, network: str) -> None:
        """Sends startup notification when the bot begins running."""
        msg = (
            f"🚀 <b>Low-MC Sniper Shadow Runner Active!</b>\n\n"
            f"<b>Network:</b> {network.upper()}\n"
            f"<b>Status:</b> Live & Monitoring\n"
            f"<b>Interval:</b> Every 30s polling + T0 RPC Gate Checks\n\n"
            f"<i>You will receive hourly heartbeats. Tap below anytime to fetch data!</i>"
        )
        await self.send_message(msg, reply_markup=self.get_inline_keyboard())

    async def send_hourly_heartbeat(self, pending_count: int, resolved_count: int, report_text: str) -> None:
        """Sends hourly heartbeat message to confirm bot is active."""
        safe_report = html.escape(report_text[:800])
        msg = (
            f"💓 <b>Shadow Runner Heartbeat</b>\n\n"
            f"<b>Status:</b> ONLINE\n"
            f"<b>Pending T0 Tokens:</b> {pending_count}\n"
            f"<b>Resolved Outcomes:</b> {resolved_count}\n\n"
            f"<pre>{safe_report}</pre>"
        )
        await self.send_message(msg, reply_markup=self.get_inline_keyboard())

    async def handle_update(self, update: dict[str, Any], runner: Any) -> None:
        """Processes incoming messages and button clicks from the user in Telegram."""
        # Handle Callback Queries (Button Clicks)
        callback = update.get("callback_query")
        if callback:
            cb_data = callback.get("data", "")
            cb_id = callback.get("id")

            # Acknowledge button tap
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(f"{self.base_url}/answerCallbackQuery", json={"callback_query_id": cb_id})
            except Exception:
                pass

            if cb_data == "get_csv":
                csv_file = runner.resolved_tokens_csv
                if csv_file.exists() and runner.resolved_tokens:
                    await self.send_document(csv_file, caption=f"📊 Resolved dataset ({len(runner.resolved_tokens)} tokens)")
                else:
                    pending_file = runner.pending_tokens_file
                    if pending_file.exists():
                        await self.send_document(pending_file, caption=f"⏳ Pending T0 dataset ({len(runner.pending_tokens)} tokens)")
                    else:
                        await self.send_message("⚠️ No data files generated yet. Keep the runner active!")

            elif cb_data == "get_report":
                report = runner.generate_report()
                safe_report = html.escape(report)
                await self.send_message(f"📈 <b>Live Calibration Report</b>\n\n<pre>{safe_report}</pre>", reply_markup=self.get_inline_keyboard())

            elif cb_data == "get_status":
                status_text = (
                    f"🔄 <b>Shadow Runner Status</b>\n\n"
                    f"<b>Network:</b> {runner.network.upper()}\n"
                    f"<b>Pending Queue:</b> {len(runner.pending_tokens)} tokens\n"
                    f"<b>Resolved Outcomes:</b> {len(runner.resolved_tokens)} tokens\n"
                    f"<b>Seen Pools:</b> {len(runner.seen_pools)} pools"
                )
                await self.send_message(status_text, reply_markup=self.get_inline_keyboard())
            return

        # Handle Text Commands (/getdata, /status, /report, /help)
        msg = update.get("message")
        if not msg:
            return

        text = msg.get("text", "").strip().lower()
        if text in ("/data", "/getdata", "/csv"):
            csv_file = runner.resolved_tokens_csv
            if csv_file.exists() and runner.resolved_tokens:
                await self.send_document(csv_file, caption=f"📊 Resolved dataset ({len(runner.resolved_tokens)} tokens)")
            else:
                await self.send_document(runner.pending_tokens_file, caption=f"⏳ Pending T0 dataset ({len(runner.pending_tokens)} tokens)")

        elif text in ("/status", "/report", "/start", "/help"):
            report = runner.generate_report()
            await self.send_message(f"<pre>{report}</pre>", reply_markup=self.get_inline_keyboard())

    async def poll_listener_loop(self, runner: Any) -> None:
        """Background long-polling loop to listen for user command/button interactions on Telegram."""
        if not self.enabled:
            return

        logger.info("Telegram listener loop started. Listening for commands and button taps...")
        while True:
            try:
                url = f"{self.base_url}/getUpdates"
                params = {"offset": self.offset, "timeout": 20}
                async with httpx.AsyncClient(timeout=25.0) as client:
                    res = await client.get(url, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        updates = data.get("result", [])
                        for update in updates:
                            self.offset = update["update_id"] + 1
                            await self.handle_update(update, runner)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Telegram poll update error (retrying): {e}")
                await asyncio.sleep(5)

            await asyncio.sleep(1)
