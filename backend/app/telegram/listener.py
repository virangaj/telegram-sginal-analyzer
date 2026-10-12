"""
Telegram message listener for receiving signals.
"""

import asyncio
import logging
from datetime import datetime
from typing import Awaitable, Callable, Optional

from telethon import TelegramClient
from telethon.events import NewMessage
from sqlalchemy.orm import Session

from app.config import settings
from app.database.base import SessionLocal
from app.database.models import Channel, Message, ParseStatus


logger = logging.getLogger(__name__)


class TelegramListener:
    """
    Handles Telegram connection and message listening.
    """

    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.enabled_chat_ids: set[int] = set()
        self.is_listening = False
        self.listening_task: Optional[asyncio.Task] = None

        self.message_handlers: list[
            Callable[[NewMessage.Event], Awaitable[None]]
        ] = []

        # Keep references to background parsing tasks.
        # This prevents tasks from being lost and allows us
        # to wait for them during shutdown.
        self._background_tasks: set[asyncio.Task] = set()

        self._stopping = False

    async def connect(self) -> None:
        """
        Initialize and connect to Telegram.
        """

        if self.client:
            logger.warning("Telegram client is already initialized")
            return

        client = TelegramClient(
            settings.telegram_session_name,
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )
        self.client = client
        try:
            await client.connect()
        except BaseException:
            await client.disconnect()
            self.client = None
            raise
        self._stopping = False

        logger.info("Connected to Telegram")

    async def disconnect(self) -> None:
        """
        Disconnect from Telegram.

        Before disconnecting, wait for currently running
        background parsing tasks to finish.
        """

        if self._stopping:
            return

        self._stopping = True

        logger.info(
            "Stopping Telegram listener. "
            "Waiting for background tasks to finish..."
        )

        await self._drain_background_tasks()

        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from Telegram")

            self.client = None

    def register_handler(
        self,
        handler: Callable[
            [NewMessage.Event],
            Awaitable[None]
        ],
    ) -> None:
        """
        Register a handler for incoming messages.
        """

        self.message_handlers.append(handler)

        logger.info(
            "Registered Telegram message handler: %s",
            getattr(handler, "__name__", str(handler)),
        )

    async def start_listening(self) -> None:
        """
        Start listening for messages from configured channels.
        """

        if not self.client:
            raise RuntimeError(
                "Client not connected. Call connect() first."
            )

        self._stopping = False

        self.refresh_channels()
        self.is_listening = True

        @self.client.on(NewMessage())
        async def handle_message(event: NewMessage.Event):
            """
            Handle incoming Telegram messages.

            The handlers are awaited here, but parsing itself is
            handled as a background task by MessageProcessor.
            """

            if not self.accepts_channel(event.chat_id):
                return

            try:
                logger.debug(
                    "Received message from %s (message %s)",
                    event.chat_id,
                    event.message.id,
                )

                for handler in self.message_handlers:
                    try:
                        await handler(event)

                    except Exception as e:
                        logger.error(
                            "Error in message handler: %s",
                            e,
                            exc_info=True,
                        )

            except Exception as e:
                logger.error(
                    "Unexpected error handling Telegram message: %s",
                    e,
                    exc_info=True,
                )

        logger.info(
            "Telegram listener started"
        )

        logger.info(
            "Listening to Telegram channels: %s",
            sorted(self.enabled_chat_ids),
        )

        try:
            await self.client.run_until_disconnected()

        except asyncio.CancelledError:
            logger.info(
                "Telegram listener task cancelled"
            )
            raise

        finally:
            self.is_listening = False
            logger.info(
                "Telegram listener stopped"
            )

    async def ensure_listening(self) -> None:
        if not self.client or not await self.client.is_user_authorized():
            return
        if self.listening_task and not self.listening_task.done():
            return
        self.listening_task = asyncio.create_task(self.start_listening())

    async def sync_channels(self, db: Session) -> None:
        if not self.client or not await self.client.is_user_authorized():
            raise RuntimeError("Telegram authentication required")
        existing = {
            channel.external_channel_id: channel
            for channel in db.query(Channel).filter(Channel.platform == "telegram").all()
        }
        async for dialog in self.client.iter_dialogs():
            if not (dialog.is_channel or dialog.is_group):
                continue
            external_id = str(dialog.id)
            channel = existing.get(external_id)
            if channel is None:
                channel = Channel(
                    platform="telegram", external_channel_id=external_id,
                    channel_name=dialog.name or external_id,
                    enabled=dialog.id in settings.channel_ids,
                )
                db.add(channel)
                existing[external_id] = channel
            else:
                channel.channel_name = dialog.name or external_id
        db.commit()
        self.refresh_channels()

    def refresh_channels(self) -> None:
        with SessionLocal() as db:
            channels = db.query(Channel).filter(
                Channel.platform == "telegram", Channel.enabled.is_(True)
            ).all()
            self.enabled_chat_ids = {
                int(channel.external_channel_id) for channel in channels
                if not settings.telegram_auto_publish or int(channel.external_channel_id) not in settings.telegram_publish_chat_ids
            }

    def accepts_channel(self, chat_id: Optional[int]) -> bool:
        if settings.telegram_auto_publish and chat_id in settings.telegram_publish_chat_ids:
            return False
        return chat_id in self.enabled_chat_ids

    async def stop_listening(self) -> None:
        """
        Stop listening for messages.
        """

        await self.disconnect()

    def create_background_task(
        self,
        coroutine: Awaitable[None],
    ) -> asyncio.Task:
        """
        Create and track a background task.

        The task is automatically removed from the tracking set
        when it completes.
        """

        task = asyncio.create_task(coroutine)

        self._background_tasks.add(task)

        task.add_done_callback(
            self._background_tasks.discard
        )

        return task

    async def _drain_background_tasks(self) -> None:
        """
        Wait for all currently running background tasks.

        Tasks that are added while shutdown is happening are also
        handled by repeatedly checking the task set.
        """

        while self._background_tasks:

            tasks = list(self._background_tasks)

            logger.info(
                "Waiting for %d background task(s) to finish...",
                len(tasks),
            )

            results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            for result in results:
                if isinstance(result, Exception):
                    logger.error(
                        "Background task failed during shutdown: %s",
                        result,
                        exc_info=(
                            type(result),
                            result,
                            result.__traceback__,
                        ),
                    )

        logger.info(
            "All background tasks completed"
        )


_telegram_listener = TelegramListener()


def get_telegram_listener() -> TelegramListener:
    return _telegram_listener


class MessageProcessor:
    """
    Process incoming Telegram messages.

    CRITICAL:
    Messages are ALWAYS stored first, regardless of parse success.

    This allows later reprocessing when new parsers are added.
    """

    # This gets assigned by the application when the listener
    # is created. It allows MessageProcessor to create tracked
    # background tasks.
    listener: Optional[TelegramListener] = None

    @staticmethod
    async def store_raw_message(
        event: NewMessage.Event,
        db: Optional[Session] = None,
    ) -> Optional[tuple[int, str]]:
        """
        Store a raw Telegram message in the database.

        ALWAYS stores the message regardless of parse success.

        Message parse status starts as PENDING.

        Returns:
            Tuple of:
                message_id
                raw_text

            Returns None if storage fails.
        """

        session = db or SessionLocal()

        try:
            # --------------------------------------------------
            # Get existing channel
            # --------------------------------------------------

            channel = (
                session.query(Channel)
                .filter(
                    Channel.external_channel_id
                    == str(event.chat_id)
                )
                .first()
            )

            # --------------------------------------------------
            # Create channel if it doesn't exist
            # --------------------------------------------------

            if not channel:

                channel_name = getattr(
                    event.chat,
                    "title",
                    f"Channel {event.chat_id}",
                )

                channel = Channel(
                    platform="telegram",
                    external_channel_id=str(
                        event.chat_id
                    ),
                    channel_name=channel_name,
                    enabled=True,
                )

                session.add(channel)

                # Make sure channel.id is generated.
                session.flush()

                logger.info(
                    "Created new channel record: %s",
                    event.chat_id,
                )

            # --------------------------------------------------
            # Create message
            # --------------------------------------------------

            message = Message(
                channel_id=channel.id,
                external_message_id=str(
                    event.message.id
                ),
                source="telegram",
                raw_text=event.raw_text,
                received_at=(
                    event.message.date
                    or datetime.utcnow()
                ),
                parse_status=ParseStatus.PENDING,
                parse_error=None,
            )

            session.add(message)

            # --------------------------------------------------
            # Flush first
            #
            # This generates message.id without committing.
            # --------------------------------------------------

            session.flush()

            # IMPORTANT:
            #
            # Extract primitive values while the SQLAlchemy
            # session is still active.
            #
            # Do NOT return the SQLAlchemy Message object.
            #

            message_id = message.id
            raw_text = message.raw_text

            # --------------------------------------------------
            # Commit
            # --------------------------------------------------

            session.commit()

            logger.info(
                "Stored message %s from channel %s",
                message_id,
                event.chat_id,
            )

            return message_id, raw_text

        except Exception as e:

            logger.error(
                "Error storing raw message: %s",
                e,
                exc_info=True,
            )

            session.rollback()

            return None

        finally:

            # Only close sessions created by this function.
            if db is None:
                session.close()

    @staticmethod
    async def store_and_parse_message(
        event: NewMessage.Event,
    ) -> None:
        """
        Store the message first, then parse it in a background task.

        Parsing runs via asyncio.create_task so the Telegram listener
        does not wait for parser/database work.
        """

        if settings.telegram_auto_publish and event.chat_id in settings.telegram_publish_chat_ids:
            return

        result = await MessageProcessor.store_raw_message(
            event
        )

        if not result:
            logger.error(
                "Failed to store Telegram message %s",
                event.message.id,
            )
            return

        message_id, raw_text = result

        logger.debug(
            "Scheduling parsing for message %s",
            message_id,
        )

        # ------------------------------------------------------
        # Create background parsing task
        # ------------------------------------------------------

        coroutine = MessageProcessor._parse_message_task(
            message_id,
            raw_text,
        )

        if MessageProcessor.listener:
            MessageProcessor.listener.create_background_task(
                coroutine
            )
        else:
            # Fallback if listener was not registered.
            #
            # This should normally not happen if the application
            # initializes MessageProcessor correctly.
            logger.warning(
                "TelegramListener is not registered with "
                "MessageProcessor. Creating untracked task."
            )

            asyncio.create_task(coroutine)

    @staticmethod
    async def _parse_message_task(
        message_id: int,
        raw_text: str,
    ) -> None:
        """
        Background task.

        Each parsing task gets its own SQLAlchemy session.
        """

        # Import here to avoid circular import.
        from app.services.signal_service import SignalService

        session = SessionLocal()

        try:

            logger.debug(
                "Starting parser for message %s",
                message_id,
            )

            signal = await SignalService.parse_and_store_signal(
                message_id,
                raw_text,
                session,
            )

            message = session.get(Message, message_id)
            if message is not None:
                from app.telegram.publisher import publish_raw_message

                try:
                    await publish_raw_message(message, session, get_telegram_listener().client)
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    session.rollback()
                    logger.warning("Telegram publication failed for message %s (%s)", message_id, type(error).__name__)

            logger.debug(
                "Finished parser for message %s",
                message_id,
            )

        except asyncio.CancelledError:

            logger.warning(
                "Parser task cancelled for message %s",
                message_id,
            )

            session.rollback()

            raise

        except Exception as e:

            logger.error(
                "Error parsing message %s: %s",
                message_id,
                e,
                exc_info=True,
            )

            session.rollback()

        finally:

            session.close()