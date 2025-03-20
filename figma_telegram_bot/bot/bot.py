import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

from figma_telegram_bot.config.settings import (
    TELEGRAM_BOT_TOKEN,
    CHECK_INTERVAL,
    AUTO_SUBSCRIBE_COMMENTS,
)
from figma_telegram_bot.figma_api.client import FigmaClient
from figma_telegram_bot.utils.version_tracker import FigmaVersionTracker
from figma_telegram_bot.utils.comment_tracker import FigmaCommentTracker
from figma_telegram_bot.utils.subscription_manager import SubscriptionManager

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация клиентов и трекеров
figma_client = FigmaClient()
version_tracker = FigmaVersionTracker()
comment_tracker = FigmaCommentTracker()
subscription_manager = SubscriptionManager()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        "👋 Привет! Я бот для отслеживания изменений в файлах Figma.\n\n"
        "Что я умею:\n"
        "• Отслеживать изменения версий файлов Figma\n"
        "• Уведомлять вас при обновлении файлов\n"
        "• Уведомлять о новых комментариях\n\n"
        "Команды:\n"
        "/start - Показать это сообщение\n"
        "/subscribe <file_key> - Подписаться на обновления файла\n"
        "/unsubscribe <file_key> - Отписаться от обновлений файла\n"
        "/comments_on <file_key> - Подписаться на комментарии файла\n"
        "/comments_off <file_key> - Отписаться от комментариев файла\n"
        "/reset_comments <file_key> - Сбросить отслеживание комментариев\n"
        "/list - Показать список отслеживаемых файлов\n"
        "/help - Показать справку"
    )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подписка на обновления файла"""
    chat_id = update.effective_chat.id

    # Проверка аргументов
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Пожалуйста, укажите ключ файла Figma.\n"
            "Например: /subscribe abcXYZ123\n\n"
            "Ключ можно найти в URL файла Figma:\n"
            "https://www.figma.com/file/<file_key>/..."
        )
        return

    file_key = context.args[0]

    # Проверка доступности файла
    try:
        file_info = figma_client.get_file(file_key)
        if "error" in file_info:
            await update.message.reply_text(
                f"❌ Ошибка доступа к файлу: {file_info['error']}"
            )
            return
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return

    # Добавляем файл для отслеживания
    version_tracker.add_file_to_track(file_key)

    # Добавляем подписку пользователя
    subscription_manager.add_file_subscription(chat_id, file_key)

    # Формируем сообщение подтверждения
    file_name = file_info.get("name", "Файл Figma")
    message = (
        f"✅ Вы успешно подписались на обновления файла:\n"
        f"«{file_name}»\n\n"
        f"Текущая версия: {version_tracker.versions.get(file_key, 'Неизвестно')}"
    )

    # Если включена автоматическая подписка на комментарии, подписываем пользователя
    if AUTO_SUBSCRIBE_COMMENTS:
        # Добавляем файл для отслеживания комментариев
        comment_tracker.add_file_to_track(file_key)

        # Добавляем подписку пользователя на комментарии
        subscription_manager.add_comment_subscription(chat_id, file_key)

        # Получаем текущее количество комментариев
        current_comments = figma_client.get_file_comments(file_key)

        message += (
            f"\n\n💬 Вы также подписаны на комментарии этого файла.\n"
            f"Текущее количество комментариев: {len(current_comments)}"
        )
    else:
        message += (
            f"\n\nЧтобы получать уведомления о новых комментариях, используйте команду:\n"
            f"/comments_on {file_key}"
        )

    # Отправляем подтверждение
    await update.message.reply_text(message)


async def comments_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подписка на комментарии файла"""
    chat_id = update.effective_chat.id

    # Проверка аргументов
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Пожалуйста, укажите ключ файла Figma.\n"
            "Например: /comments_on abcXYZ123\n\n"
            "Ключ можно найти в URL файла Figma:\n"
            "https://www.figma.com/file/<file_key>/..."
        )
        return

    file_key = context.args[0]

    # Проверка доступности файла
    try:
        file_info = figma_client.get_file(file_key)
        if "error" in file_info:
            await update.message.reply_text(
                f"❌ Ошибка доступа к файлу: {file_info['error']}"
            )
            return
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return

    # Добавляем файл для отслеживания комментариев
    comment_tracker.add_file_to_track(file_key)

    # Добавляем подписку пользователя на комментарии
    subscription_manager.add_comment_subscription(chat_id, file_key)

    # Отправляем подтверждение
    file_name = file_info.get("name", "Файл Figma")

    # Получаем текущее количество комментариев
    current_comments = figma_client.get_file_comments(file_key)

    await update.message.reply_text(
        f"✅ Вы успешно подписались на комментарии файла:\n"
        f"«{file_name}»\n\n"
        f"Текущее количество комментариев: {len(current_comments)}\n"
        f"Вы будете получать уведомления о новых комментариях."
    )


async def reset_comments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сброс отслеживания комментариев файла"""
    chat_id = update.effective_chat.id

    # Проверка аргументов
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Пожалуйста, укажите ключ файла Figma.\n"
            "Например: /reset_comments abcXYZ123\n\n"
            "Эта команда позволяет получить уведомления о всех существующих комментариях файла."
        )
        return

    file_key = context.args[0]

    # Проверяем, подписан ли пользователь на комментарии этого файла
    if not subscription_manager.is_user_subscribed_to_comments(chat_id, file_key):
        await update.message.reply_text(
            "❌ Вы не подписаны на комментарии этого файла.\n"
            "Сначала подпишитесь с помощью команды:\n"
            f"/comments_on {file_key}"
        )
        return

    # Сбрасываем отслеживание комментариев для файла
    if comment_tracker.reset_comments_for_file(file_key):
        await update.message.reply_text(
            "✅ Отслеживание комментариев для файла сброшено.\n"
            "При следующей проверке вы получите уведомления о всех существующих комментариях."
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при сбросе отслеживания комментариев.\n"
            "Пожалуйста, попробуйте отписаться и подписаться заново с помощью команд:\n"
            f"/comments_off {file_key}\n"
            f"/comments_on {file_key}"
        )


async def comments_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отписка от комментариев файла"""
    chat_id = update.effective_chat.id

    # Проверка аргументов
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Пожалуйста, укажите ключ файла Figma.\n"
            "Например: /comments_off abcXYZ123\n\n"
            "Или используйте /list для просмотра списка подписок."
        )
        return

    file_key = context.args[0]

    # Проверяем, подписан ли пользователь на комментарии этого файла
    if not subscription_manager.is_user_subscribed_to_comments(chat_id, file_key):
        await update.message.reply_text(
            "❌ Вы не подписаны на комментарии этого файла."
        )
        return

    # Удаляем подписку
    subscription_manager.remove_comment_subscription(chat_id, file_key)

    # Если на комментарии файла больше никто не подписан, можно удалить его из отслеживания
    if not subscription_manager.has_any_comment_subscribers(file_key):
        comment_tracker.remove_file_from_track(file_key)

    # Отправляем подтверждение
    await update.message.reply_text("✅ Вы успешно отписались от комментариев файла.")


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отписка от обновлений файла"""
    chat_id = update.effective_chat.id

    # Проверка аргументов
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Пожалуйста, укажите ключ файла Figma.\n"
            "Например: /unsubscribe abcXYZ123\n\n"
            "Или используйте /list для просмотра списка подписок."
        )
        return

    file_key = context.args[0]

    # Проверяем, подписан ли пользователь на этот файл
    if not subscription_manager.is_user_subscribed_to_file(chat_id, file_key):
        await update.message.reply_text("❌ Вы не подписаны на обновления этого файла.")
        return

    # Удаляем подписку
    subscription_manager.remove_file_subscription(chat_id, file_key)

    # Если на файл больше никто не подписан, можно удалить его из отслеживания
    if not subscription_manager.has_any_file_subscribers(file_key):
        version_tracker.remove_file_from_track(file_key)

    # Также отписываем от комментариев, если пользователь был подписан
    if subscription_manager.is_user_subscribed_to_comments(chat_id, file_key):
        subscription_manager.remove_comment_subscription(chat_id, file_key)

        # Если на комментарии файла больше никто не подписан, удаляем из отслеживания
        if not subscription_manager.has_any_comment_subscribers(file_key):
            comment_tracker.remove_file_from_track(file_key)

    # Отправляем подтверждение
    await update.message.reply_text(
        "✅ Вы успешно отписались от обновлений файла и его комментариев."
    )


async def list_subscriptions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Показать список подписок пользователя"""
    chat_id = update.effective_chat.id

    # Получаем подписки пользователя
    file_subscriptions_keys = subscription_manager.get_user_file_subscriptions(chat_id)
    comment_subscriptions_keys = subscription_manager.get_user_comment_subscriptions(
        chat_id
    )

    # Проверяем, есть ли у пользователя подписки
    if not file_subscriptions_keys and not comment_subscriptions_keys:
        await update.message.reply_text("У вас нет активных подписок на файлы Figma.")
        return

    # Формируем список подписок на обновления файлов
    file_subscriptions = []

    if file_subscriptions_keys:
        for file_key in file_subscriptions_keys:
            # Получаем информацию о файле
            try:
                file_info = figma_client.get_file(file_key)
                file_name = file_info.get("name", "Неизвестно")
                version = version_tracker.versions.get(file_key, "Неизвестно")

                # Проверяем подписку на комментарии
                comments_status = (
                    "✅"
                    if subscription_manager.is_user_subscribed_to_comments(
                        chat_id, file_key
                    )
                    else "❌"
                )

                file_subscriptions.append(
                    f"• {file_name}\n  Ключ: {file_key}\n  Версия: {version}\n  Комментарии: {comments_status}"
                )
            except Exception:
                file_subscriptions.append(
                    f"• Ключ: {file_key}\n  Версия: {version_tracker.versions.get(file_key, 'Неизвестно')}"
                )

    # Формируем список подписок только на комментарии файлов (если есть такие)
    comment_only_subscriptions = []

    if comment_subscriptions_keys:
        for file_key in comment_subscriptions_keys:
            # Пропускаем файлы, на которые уже подписаны на обновления
            if file_key in file_subscriptions_keys:
                continue

            # Получаем информацию о файле
            try:
                file_info = figma_client.get_file(file_key)
                file_name = file_info.get("name", "Неизвестно")

                comment_only_subscriptions.append(
                    f"• {file_name}\n  Ключ: {file_key}\n  Только комментарии: ✅"
                )
            except Exception:
                comment_only_subscriptions.append(
                    f"• Ключ: {file_key}\n  Только комментарии: ✅"
                )

    # Формируем сообщение
    message_parts = []

    if file_subscriptions:
        message_parts.append(
            "🔔 Ваши подписки на обновления файлов Figma:\n\n"
            + "\n\n".join(file_subscriptions)
        )

    if comment_only_subscriptions:
        message_parts.append(
            "💬 Ваши подписки только на комментарии файлов Figma:\n\n"
            + "\n\n".join(comment_only_subscriptions)
        )

    # Отправляем список
    await update.message.reply_text("\n\n".join(message_parts))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать справку"""
    await update.message.reply_text(
        "📚 Справка по командам:\n\n"
        "/start - Начать работу с ботом\n"
        "/subscribe <file_key> - Подписаться на обновления файла\n"
        "/unsubscribe <file_key> - Отписаться от обновлений файла\n"
        "/comments_on <file_key> - Подписаться на комментарии файла\n"
        "/comments_off <file_key> - Отписаться от комментариев файла\n"
        "/reset_comments <file_key> - Сбросить отслеживание комментариев\n"
        "/list - Показать список отслеживаемых файлов\n"
        "/help - Показать эту справку\n\n"
        "Как найти ключ файла Figma:\n"
        "1. Откройте файл в Figma\n"
        "2. Скопируйте часть URL после '/file/'\n"
        "3. Например, из ссылки https://www.figma.com/file/abcXYZ123/Project-Name\n"
        "   ключ файла: abcXYZ123"
    )


async def check_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка обновлений файлов и отправка уведомлений"""
    logger.info("Запуск проверки обновлений файлов...")

    # Получаем список обновленных файлов
    updated_files = version_tracker.check_all_updates()

    if not updated_files:
        logger.info("Обновлений версий файлов не обнаружено.")
    else:
        # Для каждого обновленного файла находим подписчиков и отправляем уведомления
        for file_update in updated_files:
            file_key = file_update["file_key"]
            old_version = file_update["old_version"]
            new_version = file_update["new_version"]

            # Получаем информацию о файле
            try:
                file_info = figma_client.get_file(file_key)
                file_name = file_info.get("name", "Файл Figma")

                # Получаем список последних версий
                versions_info = figma_client.get_file_versions(file_key)
                latest_version_info = versions_info[0] if versions_info else None

                # Формируем сообщение
                message = (
                    f"🔄 Обнаружено обновление файла Figma!\n\n"
                    f"📝 Название: {file_name}\n"
                    f"🔑 Ключ: {file_key}\n"
                    f"📊 Версия: {old_version} → {new_version}\n"
                )

                # Добавляем информацию о последнем обновлении, если доступна
                if latest_version_info:
                    user = latest_version_info.get("user", {}).get(
                        "handle", "Неизвестно"
                    )
                    label = latest_version_info.get("label", "Без описания")
                    created_at = latest_version_info.get("created_at", "")

                    message += (
                        f"\n📌 Последнее обновление:\n"
                        f"👤 Автор: {user}\n"
                        f"🏷️ Описание: {label}\n"
                        f"🕒 Дата: {created_at}\n"
                    )

                # Создаем кнопку для перехода к файлу
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Открыть в Figma",
                            url=f"https://www.figma.com/file/{file_key}",
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Получаем список подписчиков файла
                subscribers = subscription_manager.get_file_subscribers(file_key)
                logger.info(
                    f"Отправка уведомлений о обновлении файла {file_name} {len(subscribers)} подписчикам"
                )

                # Отправляем уведомления подписчикам
                for chat_id in subscribers:
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id, text=message, reply_markup=reply_markup
                        )
                        logger.info(
                            f"Отправлено уведомление о обновлении файла пользователю {chat_id}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Ошибка при отправке уведомления пользователю {chat_id}: {e}"
                        )

            except Exception as e:
                logger.error(f"Ошибка при обработке обновления файла {file_key}: {e}")

    # Проверяем новые комментарии
    logger.info("Запуск проверки новых комментариев...")
    new_comments_by_file = comment_tracker.check_all_comments()

    if not new_comments_by_file:
        logger.info("Новых комментариев не обнаружено.")
    else:
        # Для каждого файла с новыми комментариями находим подписчиков и отправляем уведомления
        for file_key, new_comments in new_comments_by_file.items():
            # Получаем информацию о файле
            try:
                file_info = figma_client.get_file(file_key)
                file_name = file_info.get("name", "Файл Figma")
                logger.info(
                    f"Отправка уведомлений о {len(new_comments)} новых комментариях в файле {file_name}"
                )

                # Получаем список подписчиков комментариев файла
                subscribers = subscription_manager.get_comment_subscribers(file_key)
                logger.info(
                    f"Отправка уведомлений о комментариях {len(subscribers)} подписчикам"
                )

                # Отправляем уведомления подписчикам о каждом новом комментарии
                for chat_id in subscribers:
                    for comment in new_comments:
                        try:
                            # Получаем информацию о комментарии
                            comment_id = comment.get("id", "")
                            comment_text = comment.get("message", "")
                            user_handle = comment.get("user", {}).get(
                                "handle", "Неизвестно"
                            )
                            created_at = comment.get("created_at", "")

                            # Формируем сообщение
                            message = (
                                f"💬 Новый комментарий в файле Figma!\n\n"
                                f"📝 Файл: {file_name}\n"
                                f"👤 Автор: {user_handle}\n"
                                f"🕒 Дата: {created_at}\n\n"
                                f"📄 Комментарий: \n{comment_text}"
                            )

                            # Создаем кнопку для перехода к файлу
                            keyboard = [
                                [
                                    InlineKeyboardButton(
                                        "Открыть в Figma",
                                        url=f"https://www.figma.com/file/{file_key}?node-id={comment.get('client_meta', {}).get('node_id', '')}&t={comment_id}",
                                    )
                                ]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)

                            # Отправляем уведомление
                            await context.bot.send_message(
                                chat_id=chat_id, text=message, reply_markup=reply_markup
                            )

                            logger.info(
                                f"Отправлено уведомление о комментарии {comment_id} пользователю {chat_id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Ошибка при отправке уведомления о комментарии пользователю {chat_id}: {e}"
                            )

            except Exception as e:
                logger.error(f"Ошибка при обработке комментариев файла {file_key}: {e}")


def run_bot() -> None:
    """Запуск Telegram бота"""
    # Создаем приложение бота
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("comments_on", comments_on))
    application.add_handler(CommandHandler("comments_off", comments_off))
    application.add_handler(CommandHandler("reset_comments", reset_comments))
    application.add_handler(CommandHandler("list", list_subscriptions))
    application.add_handler(CommandHandler("help", help_command))

    # Добавляем обработчик для обновлений по расписанию
    job_queue = application.job_queue
    job_queue.run_repeating(check_updates, interval=CHECK_INTERVAL, first=10)

    # Запускаем бота
    application.run_polling()
