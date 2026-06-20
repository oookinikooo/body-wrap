import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.enums.chat_type import ChatType
from aiogram.types import CallbackQuery, Message
from src.config import config
from src.services.user import Users

from .tools import notify_admin_about_new_user

logger = logging.getLogger("middleware")


class PrivateChatMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id

        chat = event.chat if isinstance(event, Message) else event.message.chat
        if chat.type != ChatType.PRIVATE:
            logger.info(f"User #{user_id} call bot not in private chat")
            return
        
        if user_id in config.admin_ids:
            return await handler(event, data)
        else:
            user = await Users().get(user_id)
            if not user:
                await Users().add(user_id, event.from_user.full_name)

                user = await Users().get(user_id)
                if user:
                    await notify_admin_about_new_user(event.bot, user)

            if user and user.is_active:
                data["user"] = user
                return await handler(event, data)
