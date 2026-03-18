"""
Main window for the IG Reel Automation GUI application.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QComboBox, QSpinBox,
    QTextEdit, QProgressBar, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QGroupBox, QFormLayout, QLineEdit, QDateTimeEdit,
    QMessageBox, QStatusBar, QMenuBar, QMenu, QSystemTrayIcon,
    QDialog, QDialogButtonBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QDateTime, QSize
from PyQt6.QtGui import QFont, QIcon, QAction, QPixmap, QPalette, QColor

from core.database import DatabaseManager
from core.api_manager import APIManager
from core.scheduler import SchedulerManager
from utils.logger import setup_logger

class GenerationWorker(QThread):
    """Worker thread for reel generation."""
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(dict)  # result data
    error = pyqtSignal(str)

    def __init__(self, api_manager: APIManager, db_manager: DatabaseManager,
                 style: str, model: str, count: int):
        super().__init__()
        self.api_manager = api_manager
        self.db_manager = db_manager
        self.style = style
        self.model = model
        self.count = count

    def run(self):
        """Run the generation process."""
        try:
            results = []
            for i in range(self.count):
                self.progress.emit(f"Generating Reel #{i+1}", int((i / self.count) * 100))

                # Step 1: Generate idea
                self.progress.emit(f"Reel #{i+1}: Consulting LLM...", int((i / self.count) * 100) + 10)
                idea = self.api_manager.generate_reel_idea(self.style)

                # Step 2: Generate image
                self.progress.emit(f"Reel #{i+1}: Generating image...", int((i / self.count) * 100) + 30)
                image_prompt = f"Cinematic high-resolution photo. {idea['visual_detail']}"
                image_url = self.api_manager.generate_image(image_prompt, self.style)

                # Step 3: Animate video
                self.progress.emit(f"Reel #{i+1}: Animating video...", int((i / self.count) * 100) + 60)
                motion_prompt = f"Subtle camera zoom-in, {idea['motion_detail']}, hair moving in the wind, cinematic slow motion."
                video_url = self.api_manager.animate_video(image_url, motion_prompt, self.model)

                # Step 4: Save to database
                self.progress.emit(f"Reel #{i+1}: Saving...", int((i / self.count) * 100) + 90)
                reel_id = self.db_manager.create_reel(
                    title=f"Reel #{i+1} - {self.style}",
                    style=self.style
                )

                results.append({
                    'id': reel_id,
                    'idea': idea,
                    'video_url': video_url,
                    'status': 'completed'
                })

            self.progress.emit("Generation complete!", 100)
            self.finished.emit({'reels': results})

        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, db_manager: DatabaseManager, api_manager: APIManager, scheduler: SchedulerManager):
        super().__init__()
        self.db_manager = db_manager
        self.api_manager = api_manager
        self.scheduler = scheduler
        self.logger = setup_logger(__name__)

        self.generation_worker = None
        self.current_reels = []

        self.init_ui()
        self.setup_scheduler()
        self.load_data()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("IG Reel Automation - REEL-BOOM")
        self.setGeometry(100, 100, 1400, 900)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_generation_tab()
        self.create_scheduler_tab()
        self.create_analytics_tab()
        self.create_settings_tab()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Menu bar
        self.create_menu_bar()

        # Apply styling
        self.apply_styling()

    def create_generation_tab(self):
        """Create the reel generation tab."""
        generation_widget = QWidget()
        layout = QVBoxLayout(generation_widget)

        # Controls group
        controls_group = QGroupBox("Factory Controls")
        controls_layout = QFormLayout(controls_group)

        # Video model selector
        self.video_model_combo = QComboBox()
        self.video_model_combo.addItems([
            "Kling AI 3.0 (Ultra Realism)",
            "Kling AI 2.6 (High Consistency)",
            "Seedream 3.0 (Dynamic Motion)"
        ])
        controls_layout.addRow("Video Model:", self.video_model_combo)

        # Content style selector
        self.content_style_combo = QComboBox()
        self.content_style_combo.addItems([
            "Truck Girl (Adventure/Power)",
            "Car Girl (Luxury/Sleek)",
            "Farm Girl (Rustic/Life)",
            "Car Speaking Girl (POV/Info)",
            "Cyberpunk Neon (Futuristic)"
        ])
        controls_layout.addRow("Content Style:", self.content_style_combo)

        # Batch count
        self.batch_count_spin = QSpinBox()
        self.batch_count_spin.setRange(1, 10)
        self.batch_count_spin.setValue(3)
        controls_layout.addRow("Batch Amount:", self.batch_count_spin)

        # Generate button
        self.generate_btn = QPushButton("BOOM! Generate Reels")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF416C, stop:1 #FF4B2B);
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                text-transform: uppercase;
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF4B2B, stop:1 #FF416C);
            }
            QPushButton:pressed {
                background: #E63946;
            }
        """)
        self.generate_btn.clicked.connect(self.start_generation)
        controls_layout.addRow("", self.generate_btn)

        layout.addWidget(controls_group)

        # Progress and terminal
        terminal_group = QGroupBox("System Terminal")
        terminal_layout = QVBoxLayout(terminal_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        terminal_layout.addWidget(self.progress_bar)

        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background: black;
                color: #10b981;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: 1px solid #064e3b;
                border-radius: 5px;
            }
        """)
        terminal_layout.addWidget(self.terminal_output)

        layout.addWidget(terminal_group)

        # Gallery
        gallery_group = QGroupBox("Generated Reels Gallery")
        gallery_layout = QVBoxLayout(gallery_group)

        self.reels_list = QListWidget()
        self.reels_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.reels_list.setIconSize(QSize(200, 150))
        self.reels_list.setGridSize(QSize(220, 180))
        gallery_layout.addWidget(self.reels_list)

        layout.addWidget(gallery_group)

        self.tab_widget.addTab(generation_widget, "🎬 Generation")

    def create_scheduler_tab(self):
        """Create the scheduler tab."""
        scheduler_widget = QWidget()
        layout = QVBoxLayout(scheduler_widget)

        # Scheduled posts table
        posts_group = QGroupBox("Scheduled Posts")
        posts_layout = QVBoxLayout(posts_group)

        self.posts_table = QTableWidget()
        self.posts_table.setColumnCount(5)
        self.posts_table.setHorizontalHeaderLabels([
            "Reel", "Account", "Scheduled Time", "Status", "Actions"
        ])
        self.posts_table.horizontalHeader().setStretchLastSection(True)
        posts_layout.addWidget(self.posts_table)

        # Schedule new post button
        schedule_btn = QPushButton("Schedule New Post")
        schedule_btn.clicked.connect(self.show_schedule_dialog)
        posts_layout.addWidget(schedule_btn)

        layout.addWidget(posts_group)

        # Content calendar
        calendar_group = QGroupBox("Content Calendar")
        calendar_layout = QVBoxLayout(calendar_group)

        self.calendar_table = QTableWidget()
        self.calendar_table.setColumnCount(4)
        self.calendar_table.setHorizontalHeaderLabels([
            "Date", "Reels", "Accounts", "Status"
        ])
        calendar_layout.addWidget(self.calendar_table)

        layout.addWidget(calendar_group)

        self.tab_widget.addTab(scheduler_widget, "📅 Scheduler")

    def create_analytics_tab(self):
        """Create the analytics tab."""
        analytics_widget = QWidget()
        layout = QVBoxLayout(analytics_widget)

        # Analytics summary
        summary_group = QGroupBox("Performance Summary")
        summary_layout = QVBoxLayout(summary_group)

        self.analytics_table = QTableWidget()
        self.analytics_table.setColumnCount(3)
        self.analytics_table.setHorizontalHeaderLabels([
            "Metric", "Value", "Change"
        ])
        summary_layout.addWidget(self.analytics_table)

        layout.addWidget(summary_group)

        # Charts placeholder
        charts_group = QGroupBox("Analytics Charts")
        charts_layout = QVBoxLayout(charts_group)

        charts_placeholder = QLabel("Charts will be displayed here")
        charts_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        charts_placeholder.setStyleSheet("color: #666; font-size: 18px;")
        charts_layout.addWidget(charts_placeholder)

        layout.addWidget(charts_group)

        self.tab_widget.addTab(analytics_widget, "📊 Analytics")

    def create_settings_tab(self):
        """Create the settings tab."""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)

        # API Keys
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout(api_group)

        self.openai_key_input = QLineEdit()
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("OpenAI API Key:", self.openai_key_input)

        self.kling_key_input = QLineEdit()
        self.kling_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("Kling AI API Key:", self.kling_key_input)

        self.nano_banana_key_input = QLineEdit()
        self.nano_banana_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("Nano Banana Pro API Key:", self.nano_banana_key_input)

        save_api_btn = QPushButton("Save API Keys")
        save_api_btn.clicked.connect(self.save_api_keys)
        api_layout.addRow("", save_api_btn)

        layout.addWidget(api_group)

        # Instagram Accounts
        ig_group = QGroupBox("Instagram Accounts")
        ig_layout = QVBoxLayout(ig_group)

        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(3)
        self.accounts_table.setHorizontalHeaderLabels([
            "Username", "Type", "Status"
        ])
        ig_layout.addWidget(self.accounts_table)

        add_account_btn = QPushButton("Add Instagram Account")
        add_account_btn.clicked.connect(self.show_add_account_dialog)
        ig_layout.addWidget(add_account_btn)

        layout.addWidget(ig_group)

        # Templates
        templates_group = QGroupBox("Content Templates")
        templates_layout = QVBoxLayout(templates_group)

        self.templates_table = QTableWidget()
        self.templates_table.setColumnCount(3)
        self.templates_table.setHorizontalHeaderLabels([
            "Name", "Style", "Actions"
        ])
        templates_layout.addWidget(self.templates_table)

        layout.addWidget(templates_group)

        self.tab_widget.addTab(settings_widget, "⚙️ Settings")

    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu('Tools')

        refresh_action = QAction('Refresh Data', self)
        refresh_action.triggered.connect(self.load_data)
        tools_menu.addAction(refresh_action)

    def apply_styling(self):
        """Apply custom styling to the application."""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f172a, stop:1 #1e293b);
                color: #f8fafc;
            }

            QTabWidget::pane {
                border: 1px solid #334155;
                background: #1e293b;
                border-radius: 5px;
            }

            QTabBar::tab {
                background: #334155;
                color: #cbd5e1;
                padding: 10px 20px;
                margin-right: 2px;
                border-radius: 5px 5px 0 0;
            }

            QTabBar::tab:selected {
                background: #38bdf8;
                color: white;
            }

            QGroupBox {
                font-weight: bold;
                border: 2px solid #334155;
                border-radius: 5px;
                margin-top: 1ex;
                color: #f8fafc;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }

            QLabel {
                color: #cbd5e1;
            }

            QComboBox, QSpinBox, QLineEdit {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 5px;
                color: white;
                padding: 5px;
            }

            QComboBox::drop-down {
                border: none;
            }

            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }

            QTableWidget {
                background: #1e293b;
                color: #f8fafc;
                gridline-color: #334155;
                border: 1px solid #334155;
                border-radius: 5px;
            }

            QTableWidget::item {
                padding: 5px;
            }

            QHeaderView::section {
                background: #334155;
                color: #f8fafc;
                padding: 5px;
                border: none;
            }

            QProgressBar {
                border: 1px solid #334155;
                border-radius: 5px;
                text-align: center;
            }

            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF416C, stop:1 #FF4B2B);
            }
        """)

    def setup_scheduler(self):
        """Setup the scheduler for background tasks."""
        if self.scheduler:
            self.scheduler.initialize()

            # Schedule daily analytics collection
            self.scheduler.schedule_daily_analytics(self.collect_analytics)

    def load_data(self):
        """Load data from database."""
        try:
            # Load reels
            self.load_reels()

            # Load scheduled posts
            self.load_scheduled_posts()

            # Load analytics
            self.load_analytics()

            # Load settings
            self.load_settings()

        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load data: {e}")

    def load_reels(self):
        """Load reels into the gallery."""
        self.reels_list.clear()
        reels = self.db_manager.get_reels(limit=20)

        for reel in reels:
            item = QListWidgetItem()
            item.setText(f"{reel['title']}\n{reel['style']}\n{reel['status']}")
            item.setData(Qt.ItemDataRole.UserRole, reel['id'])

            # Set placeholder icon (in real app, load actual thumbnail)
            # item.setIcon(QIcon("placeholder.png"))

            self.reels_list.addItem(item)

    def load_scheduled_posts(self):
        """Load scheduled posts into table."""
        self.posts_table.setRowCount(0)
        posts = self.db_manager.get_scheduled_posts()

        for post in posts:
            row = self.posts_table.rowCount()
            self.posts_table.insertRow(row)

            self.posts_table.setItem(row, 0, QTableWidgetItem(f"Reel #{post['reel_id']}"))
            self.posts_table.setItem(row, 1, QTableWidgetItem(f"Account #{post['instagram_account_id']}"))
            self.posts_table.setItem(row, 2, QTableWidgetItem(post['scheduled_time'].strftime('%Y-%m-%d %H:%M')))
            self.posts_table.setItem(row, 3, QTableWidgetItem("Scheduled"))

            # Actions button
            actions_widget = QWidget()
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(lambda: self.cancel_post(post['id']))
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.addWidget(cancel_btn)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            self.posts_table.setCellWidget(row, 4, actions_widget)

    def load_analytics(self):
        """Load analytics data."""
        self.analytics_table.setRowCount(0)

        # Mock analytics data
        analytics_data = [
            ("Total Views", "12,450", "+15%"),
            ("Total Likes", "892", "+8%"),
            ("Total Comments", "67", "+22%"),
            ("Average Engagement", "4.2%", "+5%")
        ]

        for metric, value, change in analytics_data:
            row = self.analytics_table.rowCount()
            self.analytics_table.insertRow(row)

            self.analytics_table.setItem(row, 0, QTableWidgetItem(metric))
            self.analytics_table.setItem(row, 1, QTableWidgetItem(value))

            change_item = QTableWidgetItem(change)
            if change.startswith('+'):
                change_item.setForeground(QColor('#10b981'))
            else:
                change_item.setForeground(QColor('#ef4444'))
            self.analytics_table.setItem(row, 2, change_item)

    def load_settings(self):
        """Load settings data."""
        # Load API keys (masked)
        validation = self.api_manager.validate_api_keys()
        self.openai_key_input.setText("••••••••" if validation.get('openai') else "")
        self.kling_key_input.setText("••••••••" if validation.get('kling') else "")
        self.nano_banana_key_input.setText("••••••••" if validation.get('nano_banana') else "")

        # Load Instagram accounts
        self.accounts_table.setRowCount(0)
        accounts = self.db_manager.get_instagram_accounts()

        for account in accounts:
            row = self.accounts_table.rowCount()
            self.accounts_table.insertRow(row)

            self.accounts_table.setItem(row, 0, QTableWidgetItem(account['username']))
            self.accounts_table.setItem(row, 1, QTableWidgetItem(account['account_type']))
            self.accounts_table.setItem(row, 2, QTableWidgetItem("Active" if account.get('is_active') else "Inactive"))

    def start_generation(self):
        """Start the reel generation process."""
        if self.generation_worker and self.generation_worker.isRunning():
            QMessageBox.warning(self, "Warning", "Generation already in progress!")
            return

        # Get parameters
        model_map = {
            0: "kling-3.0",
            1: "kling-2.6",
            2: "seedream-3.0"
        }

        style_map = {
            0: "truck-girl",
            1: "car-girl",
            2: "farm-girl",
            3: "car-speaking-girl",
            4: "cyberpunk"
        }

        model = model_map[self.video_model_combo.currentIndex()]
        style = style_map[self.content_style_combo.currentIndex()]
        count = self.batch_count_spin.value()

        # Validate API keys
        validation = self.api_manager.validate_api_keys()
        missing_keys = [k for k, v in validation.items() if not v]

        if missing_keys:
            QMessageBox.warning(
                self, "API Keys Required",
                f"Please configure the following API keys in Settings: {', '.join(missing_keys)}"
            )
            return

        # Start generation
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.generate_btn.setEnabled(False)
        self.terminal_output.clear()
        self.log_to_terminal("INITIALIZING", f"Starting batch of {count} Reels with {model}...")

        self.generation_worker = GenerationWorker(
            self.api_manager, self.db_manager, style, model, count
        )
        self.generation_worker.progress.connect(self.update_progress)
        self.generation_worker.finished.connect(self.generation_finished)
        self.generation_worker.error.connect(self.generation_error)
        self.generation_worker.start()

    def update_progress(self, message: str, percentage: int):
        """Update progress bar and terminal."""
        self.progress_bar.setValue(percentage)
        self.log_to_terminal("PROGRESS", message)

    def generation_finished(self, result: dict):
        """Handle generation completion."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.log_to_terminal("COMPLETE", "All reels generated successfully!")

        # Refresh reels list
        self.load_reels()

        QMessageBox.information(self, "Success", f"Generated {len(result['reels'])} reels successfully!")

    def generation_error(self, error_msg: str):
        """Handle generation error."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.log_to_terminal("ERROR", error_msg)

        QMessageBox.critical(self, "Generation Failed", f"Error: {error_msg}")

    def log_to_terminal(self, level: str, message: str):
        """Log message to terminal output."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        color_map = {
            'INITIALIZING': '#38bdf8',
            'PROGRESS': '#10b981',
            'COMPLETE': '#10b981',
            'ERROR': '#ef4444'
        }

        color = color_map.get(level, '#f8fafc')
        self.terminal_output.append(
            f'<span style="color: #6b7280;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: bold;">{level}:</span> '
            f'<span style="color: #f8fafc;">{message}</span>'
        )

    def show_schedule_dialog(self):
        """Show dialog to schedule a new post."""
        # Implementation for scheduling dialog
        QMessageBox.information(self, "Schedule Post", "Schedule dialog not implemented yet")

    def show_add_account_dialog(self):
        """Show dialog to add Instagram account."""
        # Implementation for add account dialog
        QMessageBox.information(self, "Add Account", "Add account dialog not implemented yet")

    def save_api_keys(self):
        """Save API keys to database."""
        try:
            if self.openai_key_input.text() and self.openai_key_input.text() != "••••••••":
                self.api_manager.update_api_key('openai', self.openai_key_input.text())
                self.db_manager.store_api_key('openai', self.openai_key_input.text())

            if self.kling_key_input.text() and self.kling_key_input.text() != "••••••••":
                self.api_manager.update_api_key('kling', self.kling_key_input.text())
                self.db_manager.store_api_key('kling', self.kling_key_input.text())

            if self.nano_banana_key_input.text() and self.nano_banana_key_input.text() != "••••••••":
                self.api_manager.update_api_key('nano_banana', self.nano_banana_key_input.text())
                self.db_manager.store_api_key('nano_banana', self.nano_banana_key_input.text())

            QMessageBox.information(self, "Success", "API keys saved successfully!")
            self.load_settings()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save API keys: {e}")

    def cancel_post(self, post_id: int):
        """Cancel a scheduled post."""
        # Implementation for canceling post
        QMessageBox.information(self, "Cancel Post", f"Cancel post {post_id} not implemented yet")

    def collect_analytics(self):
        """Collect analytics data (called by scheduler)."""
        # Implementation for analytics collection
        self.logger.info("Collecting analytics data...")

    def closeEvent(self, event):
        """Handle application close event."""
        if self.scheduler:
            self.scheduler.shutdown()

        if self.generation_worker and self.generation_worker.isRunning():
            reply = QMessageBox.question(
                self, 'Confirm Exit',
                'Generation is in progress. Are you sure you want to exit?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.generation_worker.terminate()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()