"""D2R Vault — application entry point."""
from __future__ import annotations

import logging
import sys

from app import config


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    setup_logging()
    logger = logging.getLogger("d2r_vault")
    logger.info("Starting %s v%s", config.APP_NAME, config.APP_VERSION)

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # keep running in tray (spec §38)
    app.setApplicationName(config.APP_NAME)

    def handle_exception(exc_type, exc_value, exc_tb):
        # The app must never crash outright — log it and keep going
        # where possible (spec §41/§54).
        logger.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = handle_exception

    from app.gui.main_window import MainWindow

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
