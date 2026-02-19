"""
ECG Column Selection Dialog
ECG 컬럼 선택 다이얼로그

Provides a dialog for users to preview CSV data and select appropriate columns
for time, ECG signal, and optional event markers.
CSV 데이터를 미리보기하고 시간, ECG 신호, 이벤트 마커 컬럼을 선택하는 다이얼로그입니다.

This dialog supports:
- Table preview of the first 10 rows
- Header detection (first row as column names)
- Time and ECG column selection via dropdown
- BioRadio marker configuration with color selection
"""

import os
import logging
import pandas as pd

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QLineEdit, QColorDialog,
    QGroupBox, QScrollArea, QWidget, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

# Default color palette for markers / 마커 기본 색상 팔레트
DEFAULT_MARKER_COLORS = [
    '#00AA00',   # Green
    '#FF0000',   # Red
    '#0000FF',   # Blue
    '#FF8C00',   # DarkOrange
    '#800080',   # Purple
    '#008B8B',   # DarkCyan
    '#8B4513',   # SaddleBrown
    '#FF1493',   # DeepPink
]


class ECGColumnSelectionDialog(QDialog):
    """
    Dialog for selecting CSV columns for ECG analysis.
    ECG 분석을 위한 CSV 컬럼 선택 다이얼로그.

    Users can:
    - Preview the loaded CSV data in a table
    - Toggle whether the first row is a column header
    - Select time and ECG signal columns
    - Configure BioRadio event markers with custom names and colors
    """

    def __init__(self, parent=None, file_path=None):
        """
        Initialize column selection dialog.
        컬럼 선택 다이얼로그 초기화.

        Args:
            parent: Parent widget / 부모 위젯
            file_path: Path to the CSV file / CSV 파일 경로
        """
        super().__init__(parent)
        self.logger = logging.getLogger()
        self.file_path = file_path
        self.result = None

        # Load CSV without header (treat first row as data)
        # CSV를 헤더 없이 로드 (첫 행을 데이터로 취급)
        self.df_raw = pd.read_csv(file_path, header=None, low_memory=False)

        # Drop columns that are entirely NaN (trailing comma issue)
        # 전체가 NaN인 컬럼 제거 (후행 쉼표 문제)
        self.df_raw = self.df_raw.dropna(axis=1, how='all')

        self.num_columns = len(self.df_raw.columns)
        self.has_header = False

        # Marker row widgets storage / 마커 행 위젯 저장
        self.marker_widgets = []

        self.setup_ui()
        self.logger.info(f"Column selection dialog opened for: {os.path.basename(file_path)}")

    def setup_ui(self):
        """
        Build the dialog UI layout.
        다이얼로그 UI 레이아웃 구성.
        """
        self.setWindowTitle(f"Column Selection - {os.path.basename(self.file_path)}")
        self.setMinimumSize(700, 600)

        # Force light mode / 라이트 모드 강제
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; color: #000000; }
            QWidget { background-color: #F0F0F0; color: #000000; }
            QLabel { background-color: #F0F0F0; color: #000000; }
            QPushButton {
                background-color: #FFFFFF; color: #000000;
                border: 1px solid #CCCCCC; border-radius: 4px; padding: 5px 15px;
            }
            QPushButton:hover { background-color: #E8E8E8; border-color: #999999; }
            QPushButton:pressed { background-color: #D0D0D0; }
            QPushButton:disabled { background-color: #E0E0E0; color: #999999; }
            QCheckBox { background-color: #F0F0F0; color: #000000; }
            QCheckBox::indicator {
                border: 2px solid #333333; border-radius: 3px;
                width: 14px; height: 14px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #4CA3E0;
                border-color: #333333;
            }
            QComboBox {
                background-color: #FFFFFF; color: #000000;
                border: 1px solid #CCCCCC; border-radius: 3px; padding: 3px 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF; color: #000000;
                selection-background-color: #D0D0D0; selection-color: #000000;
            }
            QSpinBox {
                background-color: #FFFFFF; color: #000000;
                border: 1px solid #CCCCCC; border-radius: 3px; padding: 3px 5px;
            }
            QLineEdit {
                background-color: #FFFFFF; color: #000000;
                border: 1px solid #CCCCCC; border-radius: 3px; padding: 3px 5px;
            }
            QTableWidget {
                background-color: #FFFFFF; color: #000000;
                gridline-color: #CCCCCC;
            }
            QHeaderView::section {
                background-color: #E0E0E0; color: #000000;
                border: 1px solid #CCCCCC; padding: 4px;
            }
            QGroupBox {
                background-color: #F0F0F0; color: #000000;
                border: 1px solid #CCCCCC; border-radius: 4px;
                margin-top: 10px; padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 5px;
            }
        """)

        main_layout = QVBoxLayout()

        # === Table preview / 테이블 미리보기 ===
        preview_label = QLabel("Data Preview (first 10 rows):")
        preview_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(preview_label)

        self.table_preview = QTableWidget()
        self.table_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_preview.setMaximumHeight(200)
        main_layout.addWidget(self.table_preview)

        self._populate_preview_table()

        # === First row is header checkbox / 첫 행이 헤더 체크박스 ===
        self.checkbox_header = QCheckBox("First row is column header")
        self.checkbox_header.stateChanged.connect(self._on_header_checkbox_changed)
        main_layout.addWidget(self.checkbox_header)

        # === Column selection / 컬럼 선택 ===
        column_group = QGroupBox("Column Selection")
        column_layout = QGridLayout()

        column_layout.addWidget(QLabel("Time Column:"), 0, 0)
        self.combo_time = QComboBox()
        column_layout.addWidget(self.combo_time, 0, 1)

        column_layout.addWidget(QLabel("ECG Column:"), 1, 0)
        self.combo_ecg = QComboBox()
        column_layout.addWidget(self.combo_ecg, 1, 1)

        column_group.setLayout(column_layout)
        main_layout.addWidget(column_group)

        self._populate_column_dropdowns()

        # === Marker section / 마커 섹션 ===
        marker_group = QGroupBox("Markers")
        marker_main_layout = QVBoxLayout()

        # Marker checkbox / 마커 체크박스
        self.checkbox_markers = QCheckBox("Markers exist")
        self.checkbox_markers.stateChanged.connect(self._on_markers_checkbox_changed)
        marker_main_layout.addWidget(self.checkbox_markers)

        # Device selection (initially hidden) / 장치 선택 (초기 숨김)
        self.device_widget = QWidget()
        device_layout = QHBoxLayout()
        device_layout.setContentsMargins(20, 0, 0, 0)
        device_layout.addWidget(QLabel("Device:"))
        self.combo_device = QComboBox()
        self.combo_device.addItems(["BioRadio"])
        device_layout.addWidget(self.combo_device)
        device_layout.addStretch()
        self.device_widget.setLayout(device_layout)
        self.device_widget.setVisible(False)
        marker_main_layout.addWidget(self.device_widget)

        # Marker count + Select button (initially hidden)
        # 마커 개수 + Select 버튼 (초기 숨김)
        self.marker_count_widget = QWidget()
        count_layout = QHBoxLayout()
        count_layout.setContentsMargins(20, 0, 0, 0)
        count_layout.addWidget(QLabel("Marker Count:"))
        self.spinbox_marker_count = QSpinBox()
        self.spinbox_marker_count.setRange(1, 20)
        self.spinbox_marker_count.setValue(1)
        count_layout.addWidget(self.spinbox_marker_count)
        self.btn_select_markers = QPushButton("Set")
        self.btn_select_markers.clicked.connect(self._on_select_markers_clicked)
        count_layout.addWidget(self.btn_select_markers)
        count_layout.addStretch()
        self.marker_count_widget.setLayout(count_layout)
        self.marker_count_widget.setVisible(False)
        marker_main_layout.addWidget(self.marker_count_widget)

        # Dynamic marker rows container (scrollable)
        # 동적 마커 행 컨테이너 (스크롤 가능)
        self.marker_scroll = QScrollArea()
        self.marker_scroll.setWidgetResizable(True)
        self.marker_container = QWidget()
        self.marker_container_layout = QGridLayout()
        self.marker_container_layout.setContentsMargins(20, 0, 0, 0)
        self.marker_container_layout.setColumnStretch(0, 3)  # Name column (wide)
        self.marker_container_layout.setColumnStretch(1, 2)  # Column dropdown
        self.marker_container_layout.setColumnStretch(2, 0)  # Color button (fixed)
        self.marker_container.setLayout(self.marker_container_layout)
        self.marker_scroll.setWidget(self.marker_container)
        self.marker_scroll.setVisible(False)
        marker_main_layout.addWidget(self.marker_scroll)

        marker_group.setLayout(marker_main_layout)
        main_layout.addWidget(marker_group)

        # === OK / Cancel buttons / 확인 / 취소 버튼 ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)

        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(btn_ok)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _populate_preview_table(self):
        """
        Fill table widget with first 10 rows of data.
        테이블 위젯을 데이터의 첫 10행으로 채우기.
        """
        preview_rows = min(10, len(self.df_raw))
        self.table_preview.setRowCount(preview_rows)
        self.table_preview.setColumnCount(self.num_columns)

        # Set column headers / 컬럼 헤더 설정
        if self.has_header:
            # Use first row as header / 첫 행을 헤더로 사용
            headers = [str(self.df_raw.iloc[0, i]) for i in range(self.num_columns)]
            self.table_preview.setHorizontalHeaderLabels(headers)
            # Fill data starting from row 1 / 1행부터 데이터 채우기
            start_row = 1
        else:
            # Use column numbers / 컬럼 번호 사용
            headers = [f"Column {i + 1}" for i in range(self.num_columns)]
            self.table_preview.setHorizontalHeaderLabels(headers)
            start_row = 0

        # Fill table cells / 테이블 셀 채우기
        for row_idx in range(preview_rows):
            data_row = start_row + row_idx
            if data_row >= len(self.df_raw):
                break
            for col_idx in range(self.num_columns):
                value = str(self.df_raw.iloc[data_row, col_idx])
                item = QTableWidgetItem(value)
                self.table_preview.setItem(row_idx, col_idx, item)

        self.table_preview.resizeColumnsToContents()

    def _populate_column_dropdowns(self):
        """
        Populate time/ECG column dropdowns based on header state.
        헤더 상태에 따라 시간/ECG 컬럼 드롭박스 채우기.
        """
        self.combo_time.clear()
        self.combo_ecg.clear()

        items = self._get_column_display_names()

        self.combo_time.addItems(items)
        self.combo_ecg.addItems(items)

        # Auto-select columns containing "time" and "ecg" (case-insensitive)
        # "time"과 "ecg"를 포함하는 컬럼 자동 선택 (대소문자 무시)
        if self.has_header:
            for i in range(self.num_columns):
                header_name = str(self.df_raw.iloc[0, i]).lower()
                if "time" in header_name:
                    self.combo_time.setCurrentIndex(i)
                if "ecg" in header_name:
                    self.combo_ecg.setCurrentIndex(i)

        # Also update marker dropdowns if they exist
        # 마커 드롭박스도 업데이트
        self._update_marker_dropdowns()

    def _get_column_display_names(self):
        """
        Get display names for column dropdowns.
        컬럼 드롭박스 표시 이름 가져오기.

        Returns:
            list: Column display names
        """
        if self.has_header:
            return [str(self.df_raw.iloc[0, i]) for i in range(self.num_columns)]
        else:
            return [f"Column {i + 1}" for i in range(self.num_columns)]

    def _on_header_checkbox_changed(self, state):
        """
        Handle header checkbox toggle.
        헤더 체크박스 토글 처리.

        Args:
            state: Checkbox state / 체크박스 상태
        """
        self.has_header = (state == Qt.CheckState.Checked.value)
        self.logger.info(f"Header checkbox changed: has_header={self.has_header}")

        # Update table preview and dropdowns
        # 테이블 미리보기 및 드롭박스 업데이트
        self._populate_preview_table()
        self._populate_column_dropdowns()

    def _on_markers_checkbox_changed(self, state):
        """
        Show/hide marker configuration when markers checkbox toggled.
        마커 체크박스 토글 시 마커 설정 표시/숨기기.

        Args:
            state: Checkbox state / 체크박스 상태
        """
        is_checked = (state == Qt.CheckState.Checked.value)
        self.device_widget.setVisible(is_checked)
        self.marker_count_widget.setVisible(is_checked)

        if not is_checked:
            # Hide marker rows when unchecked / 미체크 시 마커 행 숨기기
            self.marker_scroll.setVisible(False)
            self._clear_marker_rows()

    def _on_select_markers_clicked(self):
        """
        Generate marker configuration rows based on marker count.
        마커 개수에 따라 마커 설정 행 생성.
        """
        count = self.spinbox_marker_count.value()
        self._clear_marker_rows()

        # Add header labels to grid row 0
        # 헤더 레이블을 grid 행 0에 추가
        lbl_name = QLabel("Name")
        lbl_name.setStyleSheet("font-weight: bold;")
        lbl_col = QLabel("Column")
        lbl_col.setStyleSheet("font-weight: bold;")
        lbl_color = QLabel("Color")
        lbl_color.setStyleSheet("font-weight: bold;")
        self.marker_container_layout.addWidget(lbl_name, 0, 0)
        self.marker_container_layout.addWidget(lbl_col, 0, 1)
        self.marker_container_layout.addWidget(lbl_color, 0, 2)

        # Add marker rows to grid rows 1~N
        # 마커 행을 grid 행 1~N에 추가
        items = self._get_column_display_names()
        for i in range(count):
            row_data = self._create_marker_row(i, items, grid_row=i + 1)
            self.marker_widgets.append(row_data)

        self.marker_scroll.setVisible(True)

        # Remove max height limit so all rows are visible
        # 최대 높이 제한 해제하여 모든 행 표시
        self.marker_scroll.setMaximumHeight(16777215)

        # Resize dialog to fit content
        # 다이얼로그 크기를 콘텐츠에 맞게 조정
        self.adjustSize()

        self.logger.info(f"Generated {count} marker rows")

    def _create_marker_row(self, index, column_items, grid_row):
        """
        Create a single marker configuration row in the grid layout.
        그리드 레이아웃에 단일 마커 설정 행 생성.

        Args:
            index: Marker index for default color / 기본 색상용 마커 인덱스
            column_items: Column display names for dropdown / 드롭박스용 컬럼 표시 이름
            grid_row: Row index in the grid layout / 그리드 레이아웃 행 인덱스

        Returns:
            dict: Row data dict with widget references
        """
        # Marker name input / 마커 이름 입력
        name_edit = QLineEdit()
        name_edit.setPlaceholderText(f"Marker {index + 1}")
        self.marker_container_layout.addWidget(name_edit, grid_row, 0)

        # Column dropdown / 컬럼 드롭박스
        column_combo = QComboBox()
        column_combo.addItems(column_items)
        self.marker_container_layout.addWidget(column_combo, grid_row, 1)

        # Auto-fill marker name when column is selected (if header exists)
        # 컬럼 선택 시 마커 이름 자동 채우기 (헤더 존재 시)
        column_combo.currentIndexChanged.connect(
            lambda idx, ne=name_edit: self._on_marker_column_changed(idx, ne)
        )

        # Color button / 색상 버튼
        default_color = DEFAULT_MARKER_COLORS[index % len(DEFAULT_MARKER_COLORS)]
        color_btn = QPushButton()
        color_btn.setFixedSize(40, 25)
        color_btn.setStyleSheet(
            f"background-color: {default_color}; border: 1px solid #999999; border-radius: 3px;"
        )

        row_data = {
            "name_edit": name_edit,
            "column_combo": column_combo,
            "color_btn": color_btn,
            "color": default_color,
        }

        color_btn.clicked.connect(lambda checked, rd=row_data: self._on_color_button_clicked(rd))
        self.marker_container_layout.addWidget(color_btn, grid_row, 2)

        return row_data

    def _on_marker_column_changed(self, index, name_edit):
        """
        Auto-fill marker name when a column is selected (header mode only).
        컬럼 선택 시 마커 이름 자동 채우기 (헤더 모드에서만).

        Args:
            index: Selected column index / 선택된 컬럼 인덱스
            name_edit: QLineEdit for marker name / 마커 이름 QLineEdit
        """
        # Guard: ignore invalid index (fired during combo.clear())
        # 가드: 잘못된 인덱스 무시 (combo.clear() 시 발생)
        if index < 0 or index >= self.num_columns:
            return

        # Only auto-fill when header is enabled
        # 헤더가 활성화된 경우에만 자동 채우기
        if not self.has_header:
            return

        column_name = str(self.df_raw.iloc[0, index])
        name_edit.setText(column_name)

    def _on_color_button_clicked(self, row_data):
        """
        Open color dialog and update button color.
        색상 다이얼로그 열고 버튼 색상 업데이트.

        Args:
            row_data: Marker row data dict / 마커 행 데이터 딕셔너리
        """
        current_color = QColor(row_data["color"])
        color = QColorDialog.getColor(current_color, self, "Select Marker Color")
        if color.isValid():
            hex_color = color.name()
            row_data["color"] = hex_color
            row_data["color_btn"].setStyleSheet(
                f"background-color: {hex_color}; border: 1px solid #999999; border-radius: 3px;"
            )

    def _clear_marker_rows(self):
        """
        Remove all marker row widgets.
        모든 마커 행 위젯 제거.
        """
        self.marker_widgets.clear()
        while self.marker_container_layout.count():
            child = self.marker_container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _update_marker_dropdowns(self):
        """
        Update column dropdowns in existing marker rows.
        기존 마커 행의 컬럼 드롭박스 업데이트.
        """
        items = self._get_column_display_names()
        for row_data in self.marker_widgets:
            combo = row_data["column_combo"]
            current_idx = combo.currentIndex()
            combo.clear()
            combo.addItems(items)
            if 0 <= current_idx < len(items):
                combo.setCurrentIndex(current_idx)

    def _on_ok_clicked(self):
        """
        Validate selections and build result dict.
        선택 항목 검증 및 결과 딕셔너리 생성.
        """
        time_idx = self.combo_time.currentIndex()
        ecg_idx = self.combo_ecg.currentIndex()

        # Validate: time and ECG must be different columns
        # 검증: 시간과 ECG는 다른 컬럼이어야 함
        if time_idx == ecg_idx:
            QMessageBox.warning(
                self, "Selection Error",
                "Time and ECG columns must be different."
            )
            return

        # Build column names / 컬럼 이름 생성
        display_names = self._get_column_display_names()

        self.result = {
            "time_column": time_idx,
            "time_column_name": display_names[time_idx],
            "ecg_column": ecg_idx,
            "ecg_column_name": display_names[ecg_idx],
            "has_header": self.has_header,
            "markers": [],
        }

        # Collect marker info if markers checked / 마커 체크 시 마커 정보 수집
        if self.checkbox_markers.isChecked() and self.marker_widgets:
            for row_data in self.marker_widgets:
                name = row_data["name_edit"].text().strip()
                if not name:
                    name = row_data["name_edit"].placeholderText()

                col_idx = row_data["column_combo"].currentIndex()

                self.result["markers"].append({
                    "name": name,
                    "column": col_idx,
                    "column_name": display_names[col_idx],
                    "color": row_data["color"],
                })

            self.logger.info(f"Markers configured: {len(self.result['markers'])}")

        self.logger.info(
            f"Column selection: time={display_names[time_idx]}, "
            f"ecg={display_names[ecg_idx]}, "
            f"has_header={self.has_header}, "
            f"markers={len(self.result['markers'])}"
        )

        self.accept()

    def get_result(self):
        """
        Return the column selection result.
        컬럼 선택 결과 반환.

        Returns:
            dict or None: Selection result or None if cancelled
        """
        return self.result
