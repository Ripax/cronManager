import os
import sys
import tempfile
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QComboBox, QListWidget, QLineEdit, QHBoxLayout,
    QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt


class CronManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cron Task Manager")
        self.setGeometry(100, 100, 700, 400)
        self.editing_index = None

        self.layout = QVBoxLayout()

        title = QLabel("Cron Task Manager")
        title.setFont(QFont("Arial", 16))
        title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)

        self.cron_list = QListWidget()
        self.layout.addWidget(QLabel("📋 Installed Cron Jobs:"))
        self.layout.addWidget(self.cron_list)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ Add Cron Task")
        self.add_btn.clicked.connect(self.show_config_ui)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ Edit Selected")
        self.edit_btn.clicked.connect(self.edit_selected)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("❌ Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        btn_layout.addWidget(self.delete_btn)

        self.export_btn = QPushButton("📤 Export Cron")
        self.export_btn.clicked.connect(self.export_crontab)
        btn_layout.addWidget(self.export_btn)

        self.import_btn = QPushButton("📥 Import Cron")
        self.import_btn.clicked.connect(self.import_cron_tasks)
        btn_layout.addWidget(self.import_btn)

        self.layout.addLayout(btn_layout)

        self.config_layout = QVBoxLayout()

        self.script_type = QComboBox()
        self.script_type.addItems(["Python", "Bash"])
        self.config_layout.addWidget(QLabel("🛠️ Script Type:"))
        self.config_layout.addWidget(self.script_type)

        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Select script file or enter command")
        self.config_layout.addWidget(self.file_path)

        browse_btn = QPushButton("📂 Browse Script")
        browse_btn.clicked.connect(self.browse_script)
        self.config_layout.addWidget(browse_btn)

        self.minute = QLineEdit("*")
        self.hour = QLineEdit("*")
        self.day = QLineEdit("*")
        self.month = QLineEdit("*")
        self.weekday = QLineEdit("*")
        schedule_layout = QHBoxLayout()
        schedule_layout.addWidget(QLabel("Min"))
        schedule_layout.addWidget(self.minute)
        schedule_layout.addWidget(QLabel("Hour"))
        schedule_layout.addWidget(self.hour)
        schedule_layout.addWidget(QLabel("Day"))
        schedule_layout.addWidget(self.day)
        schedule_layout.addWidget(QLabel("Month"))
        schedule_layout.addWidget(self.month)
        schedule_layout.addWidget(QLabel("Weekday"))
        schedule_layout.addWidget(self.weekday)
        self.config_layout.addLayout(schedule_layout)

        accept_btn = QPushButton("✅ Accept")
        accept_btn.clicked.connect(self.add_or_edit_cron)
        self.config_layout.addWidget(accept_btn)

        self.layout.addLayout(self.config_layout)
        self.setLayout(self.layout)

        self.load_cron()

    def browse_script(self):
        options = QFileDialog.Options()
        path, _ = QFileDialog.getOpenFileName(self, "Select Script", "", "All Files (*)", options=options)
        if path:
            self.file_path.setText(path)

    def get_schedule_string(self):
        return f"{self.minute.text()} {self.hour.text()} {self.day.text()} {self.month.text()} {self.weekday.text()}"

    def load_cron(self):
        self.cron_list.clear()
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
            elif "no crontab for" in result.stderr:
                lines = []
            else:
                lines = []

            for line in lines:
                if line.strip() and not line.strip().startswith("#"):
                    self.cron_list.addItem(line.strip())
        except Exception as e:
            self.cron_list.addItem(f"Error loading cron: {e}")

    def show_config_ui(self):
        self.editing_index = None
        self.file_path.clear()
        self.add_btn.setText("➕ Add Cron Task")

    def add_or_edit_cron(self):
        script = self.file_path.text().strip()

        if os.path.isfile(script):
            if script.endswith(".sh"):
                command = f"/bin/bash `{script}`"
            elif script.endswith(".py"):
                command = f"/usr/bin/env dnpython-pipe5 `{script}`"
            else:
                command = script  # Fallback if extension is unknown
        else:
            command = script  # Treat as inline shell command

        if not command:
            QMessageBox.warning(self, "Invalid Input", "Please enter a script path or command.")
            return

        if os.path.isfile(command):
            if not os.access(command, os.X_OK):
                QMessageBox.warning(self, "Permission Denied", "Selected file is not executable.")
                return

        schedule = self.get_schedule_string()
        entry = f"{schedule} {command}"

        try:
            result = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True)
            lines = []
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
            elif "no crontab for" in result.stderr:
                lines = []

            lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]

            if self.editing_index is not None:
                lines[self.editing_index] = entry
                self.editing_index = None
                self.add_btn.setText("➕ Add Cron Task")
            else:
                lines.append(entry)

            new_cron = "\n".join(lines) + "\n"
            proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
            proc.communicate(new_cron.encode())

            if proc.returncode == 0:
                self.load_cron()
                self.file_path.clear()
                QMessageBox.information(self, "Success", "Cron job saved.")
            else:
                QMessageBox.critical(self, "Error", "Failed to update crontab.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def edit_selected(self):
        current_row = self.cron_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a cron job to edit.")
            return

        text = self.cron_list.item(current_row).text()
        parts = text.strip().split(maxsplit=5)
        if len(parts) < 6:
            QMessageBox.warning(self, "Parse Error", "Selected cron entry could not be parsed.")
            return

        self.minute.setText(parts[0])
        self.hour.setText(parts[1])
        self.day.setText(parts[2])
        self.month.setText(parts[3])
        self.weekday.setText(parts[4])
        self.file_path.setText(parts[5])
        self.editing_index = current_row
        self.add_btn.setText("✏️ Editing Mode")

    def delete_selected(self):
        current_row = self.cron_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a cron job to delete.")
            return

        confirm = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this cron job?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        try:
            result = subprocess.run(
                ["crontab", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            lines = []
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
            elif "no crontab for" in result.stderr:
                lines = []

            lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]
            if current_row < len(lines):
                lines.pop(current_row)

            new_cron = "\n".join(lines) + "\n"
            proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
            proc.communicate(new_cron.encode())

            if proc.returncode == 0:
                self.load_cron()
            else:
                QMessageBox.critical(self, "Error", "Failed to update crontab.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def export_crontab(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Crontab", "crontab_backup.txt", "Text Files (*.txt)")
        if not path:
            return
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            if result.returncode == 0:
                with open(path, 'w') as f:
                    f.write(result.stdout)
                QMessageBox.information(self, "Exported", f"Crontab saved to {path}")
            else:
                QMessageBox.warning(self, "Error", "No crontab found or failed to export.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def import_cron_tasks(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Crontab", "", "Cron Files (*.cron);;All Files (*)")
        if file_path:
            try:
                # Read current crontab
                current = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         universal_newlines=True)
                current_tasks = current.stdout.strip().splitlines() if current.returncode == 0 else []

                # Read imported crontab
                with open(file_path, "r") as f:
                    imported_tasks = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

                # Merge avoiding duplicates
                merged_tasks = current_tasks[:]
                for task in imported_tasks:
                    if task not in merged_tasks:
                        merged_tasks.append(task)

                # Save merged tasks
                with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp:
                    tmp.write("\n".join(merged_tasks) + "\n")
                    tmp.flush()
                    subprocess.run(["crontab", tmp.name])
                os.unlink(tmp.name)

                self.load_cron()
                QMessageBox.information(self, "Success", "Cron tasks imported and merged successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import tasks:\n{e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    manager = CronManager()
    manager.show()
    sys.exit(app.exec_())
