from aiogram.filters import Command
from aiogram_dialog import setup_dialogs, BgManagerFactory
from aiogram import Dispatcher, Router

from internal import interface


def NewTg(
        dp: Dispatcher,
        command_controller: interface.ICommandController,
        main_menu_dialog: interface.IMainMenuDialog,
        active_release_dialog: interface.IActiveReleaseDialog,
        successful_releases_dialog: interface.ISuccessfulReleasesDialog,
        failed_releases_dialog: interface.IFailedReleasesDialog,
) -> BgManagerFactory:
    include_command_handlers(
        dp,
        command_controller
    )
    dialog_bg_factory = include_dialogs(
        dp,
        main_menu_dialog,
        active_release_dialog,
        successful_releases_dialog,
        failed_releases_dialog
    )

    return dialog_bg_factory


def include_tg_middleware(
        dp: Dispatcher,
        tg_middleware: interface.ITelegramMiddleware,
):
    dp.update.middleware(tg_middleware.trace_middleware01)
    dp.update.middleware(tg_middleware.metric_middleware02)
    dp.update.middleware(tg_middleware.logger_middleware03)


def include_command_handlers(
        dp: Dispatcher,
        command_controller: interface.ICommandController,
):
    dp.message.register(
        command_controller.start_handler,
        Command("start")
    )


def include_dialogs(
        dp: Dispatcher,
        main_menu_dialog: interface.IMainMenuDialog,
        active_release_dialog: interface.IActiveReleaseDialog,
        successful_releases_dialog: interface.ISuccessfulReleasesDialog,
        failed_releases_dialog: interface.IFailedReleasesDialog,
) -> BgManagerFactory:
    dialog_router = Router()
    dialog_router.include_routers(
        main_menu_dialog.get_dialog(),
        active_release_dialog.get_dialog(),
        successful_releases_dialog.get_dialog(),
        failed_releases_dialog.get_dialog()
    )

    dp.include_routers(dialog_router)

    dialog_bg_factory = setup_dialogs(dp)

    return dialog_bg_factory
