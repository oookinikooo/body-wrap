from aiogram import Dispatcher
from src.utils.middlewares import PrivateChatMiddleware

from . import moderator, user


def attach_handlers(dp: Dispatcher):
    dp.message.outer_middleware(PrivateChatMiddleware())
    dp.callback_query.outer_middleware(PrivateChatMiddleware())

    dp.include_routers(moderator.router(), user.router())
