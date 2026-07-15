from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
import logging
import database as db
from config import CHANNELS, ADMIN_CHAT_ID
from keyboards import main_menu_kb, subscribe_kb, site_kb

router = Router()

WELCOME_TEXT = (
    "👋 Добро пожаловать!\n\n"
    "Чтобы пользоваться ботом, подпишитесь на наши каналы ниже, "
    "затем нажмите «Подтвердить»."
)


async def _is_subscribed(bot: Bot, user_id: int) -> bool:
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch["chat_id"], user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception as e:
            err_text = str(e)
            if "member list is inaccessible" in err_text:
                # Известное ограничение Telegram Bot API для некоторых каналов —
                # бот технически не может проверить статус, пропускаем.
                logging.warning(f"Проверка подписки недоступна для {ch['chat_id']} (ограничение Telegram API), пропускаем.")
                continue
            # Другая ошибка (неверный chat_id, канал не найден и т.д.) — считаем не подписан.
            logging.warning(f"Не удалось проверить подписку на {ch['chat_id']}: {e}")
            return False
    return True


async def _greet(message: Message, bot: Bot):
    is_new = await db.ensure_user(message.from_user.id, message.from_user.username)
    if await db.is_banned(message.from_user.id):
        await message.answer("⛔ Вы заблокированы за нарушение правил. Обратитесь в поддержку.")
        return
    await message.answer(WELCOME_TEXT, reply_markup=subscribe_kb())
    if is_new and ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"🆕 Новый пользователь: {message.from_user.id} (@{message.from_user.username})",
            )
        except Exception:
            pass


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    await _greet(message, bot)


@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery, bot: Bot):
    if await _is_subscribed(bot, callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer(
            "✅ Подписка подтверждена! Добро пожаловать в меню.",
            reply_markup=main_menu_kb(),
        )
        await callback.message.answer("🌐 Наш сайт:", reply_markup=site_kb())
    else:
        await callback.answer("❌ Вы подписались не на все каналы!", show_alert=True)
