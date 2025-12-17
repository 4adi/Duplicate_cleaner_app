import sys
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QDateEdit, QCheckBox, QProgressBar, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal

from duplicate_records_cleaner import DuplicateCleaner


# ===================== WORKER THREAD =====================

class PreviewWorker(QThread):
    progress = Signal(int)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, cleaner, companies, start_date):
        super().__init__()
        self.cleaner = cleaner
        self.companies = companies
        self.start_date = start_date

    def run(self):
        try:
            results = []
            total = len(self.companies)

            for idx, company in enumerate(self.companies):
                self.cleaner.company_ids = [company]

                fm = self.cleaner.remove_duplicate_measurements(
                    start_date=self.start_date, dry_run=True, return_summary=True
                )
                lp = self.cleaner.remove_duplicate_production_records(
                    start_date=self.start_date, dry_run=True, return_summary=True
                )
                ffm = self.cleaner.remove_duplicate_facility_measurements(
                    start_date=self.start_date, dry_run=True, return_summary=True
                )

                results.append({
                    "company": company,
                    "fm": fm["delete_count"],
                    "lp": lp["delete_count"],
                    "ffm": ffm["delete_count"]
                })

                self.progress.emit(int(((idx + 1) / total) * 100))

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


# ===================== MAIN WINDOW =====================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧹 Mongo Duplicate Cleanup Utility")
        self.resize(1100, 750)

        self.cleaner = None
        self.preview_results = []

        self._build_ui()

    # ---------------- UI ----------------

    def _build_ui(self):
        main_layout = QVBoxLayout()

        # Mongo input
        main_layout.addWidget(QLabel("MongoDB Connection String"))
        self.mongo_input = QLineEdit()
        self.mongo_input.setPlaceholderText("mongodb+srv://user:password@cluster.mongodb.net/")
        main_layout.addWidget(self.mongo_input)

        self.connect_btn = QPushButton("Connect to Mongo")
        self.connect_btn.clicked.connect(self.connect_mongo)
        main_layout.addWidget(self.connect_btn)

        # Company list
        main_layout.addWidget(QLabel("Select Companies"))
        self.company_list = QListWidget()
        self.company_list.setSelectionMode(QListWidget.MultiSelection)
        main_layout.addWidget(self.company_list)

        # Date range
        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(datetime.now() - timedelta(days=30))

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(datetime.now())

        date_layout.addWidget(QLabel("Start Date"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("End Date"))
        date_layout.addWidget(self.end_date)

        main_layout.addLayout(date_layout)

        # Options
        self.dry_run = QCheckBox("Dry Run (Preview Only)")
        self.dry_run.setChecked(True)
        main_layout.addWidget(self.dry_run)

        # Buttons
        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton("Preview Duplicates")
        self.preview_btn.clicked.connect(self.run_preview)
        self.delete_btn = QPushButton("Delete Duplicates")
        self.delete_btn.clicked.connect(self.run_delete)

        btn_layout.addWidget(self.preview_btn)
        btn_layout.addWidget(self.delete_btn)
        main_layout.addLayout(btn_layout)

        # Progress
        self.progress = QProgressBar()
        main_layout.addWidget(self.progress)

        # Output
        self.output = QLabel()
        self.output.setAlignment(Qt.AlignTop)
        self.output.setWordWrap(True)
        main_layout.addWidget(self.output)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    # ---------------- LOGIC ----------------

    def connect_mongo(self):
        try:
            self.cleaner = DuplicateCleaner(self.mongo_input.text())
            self.company_list.clear()

            for cid in sorted(self.cleaner.company_ids):
                self.company_list.addItem(QListWidgetItem(cid))

            QMessageBox.information(self, "Success", "Connected to MongoDB")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def run_preview(self):
        if not self.cleaner:
            QMessageBox.warning(self, "Warning", "Connect to Mongo first")
            return

        companies = [i.text() for i in self.company_list.selectedItems()]
        if not companies:
            QMessageBox.warning(self, "Warning", "Select at least one company")
            return

        start_date = self.start_date.date().toString("yyyy-MM-dd")

        self.progress.setValue(0)
        self.output.setText("Running preview...")

        self.worker = PreviewWorker(self.cleaner, companies, start_date)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.show_results)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def show_results(self, results):
        self.preview_results = results
        text = ""

        for r in results:
            text += (
                f"Company: {r['company']}\n"
                f"  Field Measurements: {r['fm']}\n"
                f"  Production: {r['lp']}\n"
                f"  Facility Measurements: {r['ffm']}\n\n"
            )

        self.output.setText(text)

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

    def run_delete(self):
        if self.dry_run.isChecked():
            QMessageBox.warning(self, "Blocked", "Disable dry-run to delete")
            return

        if not self.preview_results:
            QMessageBox.warning(self, "Warning", "Run preview first")
            return

        confirm = QMessageBox.question(
            self, "Confirm Delete", "This will permanently delete records. Continue?"
        )

        if confirm != QMessageBox.Yes:
            return

        start_date = self.start_date.date().toString("yyyy-MM-dd")

        for r in self.preview_results:
            self.cleaner.company_ids = [r["company"]]
            self.cleaner.remove_duplicate_measurements(start_date, dry_run=False)
            self.cleaner.remove_duplicate_production_records(start_date, dry_run=False)
            self.cleaner.remove_duplicate_facility_measurements(start_date, dry_run=False)

        QMessageBox.information(self, "Done", "Deletion completed")


# ===================== ENTRY =====================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
