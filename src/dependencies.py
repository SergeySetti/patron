from __future__ import annotations

import logging
import os
from typing import NewType

from dotenv import load_dotenv
from injector import Injector, Module, provider, singleton

load_dotenv()

AssistantLogger = NewType("AssistantLogger", logging.Logger)


class PatronModule(Module):

    # def configure(self, binder) -> None:
    #     # binder.bind(CompiledStateGraph, to=agent)  # Yeah, that simple

    # ------------------------------------------------------------------
    # Loggers
    # ------------------------------------------------------------------
    @staticmethod
    def _create_logger(name: str, log_file: str) -> logging.Logger:
        from logging.handlers import TimedRotatingFileHandler

        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            # Logs directory relative to this file
            logs_path = os.path.join(os.path.dirname(__file__), "logs")
            os.makedirs(logs_path, exist_ok=True)

            timed_handler = TimedRotatingFileHandler(
                filename=os.path.join(logs_path, log_file),
                when="D",  # rotate daily
                interval=1,
                backupCount=60,  # keep logs for 60 days
            )
            timed_handler.setFormatter(formatter)

            logger.addHandler(timed_handler)
            logger.addHandler(console_handler)
        return logger

    @provider
    @singleton
    def provide_logger(self) -> AssistantLogger:
        """Provide the singleton logger for the assistant."""
        return AssistantLogger(self._create_logger("assistant", "assistant_app.log"))


# Instantiate the global injector
app_container = Injector([PatronModule()])
# Log container initialisation
app_container.get(AssistantLogger).info("Injector initialized")
