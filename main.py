#!/usr/bin/env python3
"""
IG Reel Automation Tool - Main Application
A comprehensive GUI application for automated Instagram reel generation and management.
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFont, QIcon

from ui.main_window import MainWindow
from core.database import DatabaseManager
from core.api_manager import APIManager
from core.scheduler import SchedulerManager
from utils.logger import setup_logger

# Global logger
logger = setup_logger(__name__)

class ReelAutomationApp:
    """Main application class for IG Reel Automation Tool."""

    def __init__(self):
        self.app = None
        self.main_window = None
        self.db_manager = None
        self.api_manager = None
        self.scheduler = None

    def initialize(self):
        """Initialize application components."""
        try:
            # Load environment variables
            from dotenv import load_dotenv
            load_dotenv()

            # Initialize database
            self.db_manager = DatabaseManager()
            self.db_manager.initialize()

            # Initialize API manager
            self.api_manager = APIManager()

            # Initialize scheduler
            self.scheduler = SchedulerManager()

            logger.info("Application components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            return False

    def run(self):
        """Run the application."""
        try:
            # Create Qt application
            self.app = QApplication(sys.argv)

            # Set application properties
            self.app.setApplicationName("IG Reel Automation")
            self.app.setApplicationVersion("1.0.0")
            self.app.setOrganizationName("ReelBoom")

            # Set font and style
            font = QFont("Segoe UI", 10)
            self.app.setFont(font)

            # Enable high DPI scaling
            self.app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            self.app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

            # Create main window
            self.main_window = MainWindow(self.db_manager, self.api_manager, self.scheduler)

            # Show main window
            self.main_window.show()

            # Start event loop
            sys.exit(self.app.exec())

        except Exception as e:
            logger.error(f"Application failed to start: {e}")
            sys.exit(1)

def main():
    """Main entry point."""
    app = ReelAutomationApp()

    if app.initialize():
        app.run()
    else:
        logger.error("Application initialization failed")
        sys.exit(1)

if __name__ == "__main__":
    main()