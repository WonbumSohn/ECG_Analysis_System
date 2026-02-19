"""
ECG Offline Data Analysis Window
ECG 오프라인 데이터 분석 윈도우

Provides functionality to load and analyze previously recorded ECG data.
이전에 기록된 ECG 데이터를 로드하고 분석하는 기능을 제공합니다.

Users can:
- Load CSV files and select columns via a column selection dialog
- View interactive Raw ECG Signal graph with marker visualization
- Navigate through long recordings using scroll and zoom
- Save graphs as PNG files

Author: ECG Analysis System Team
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime

# Qt imports
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCheckBox, QFileDialog, QMessageBox, QWidget
)
from PySide6.QtCore import Qt

# Matplotlib imports for interactive plotting
# Matplotlib 임포트 (인터랙티브 플로팅)
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class ECGOfflineAnalysis(QDialog):
    """
    Offline ECG data analysis window.
    오프라인 ECG 데이터 분석 윈도우.

    Provides interactive visualization and analysis of previously recorded ECG data
    with zoom, pan, marker visualization, and hover tooltip capabilities.
    줌, 팬, 마커 시각화, 호버 툴팁 기능을 갖춘 ECG 데이터 인터랙티브 시각화 및 분석.
    """

    def __init__(self, parent=None, config_manager=None, save_location=None, early_log_path=None):
        """
        Initialize offline analysis window.
        오프라인 분석 윈도우 초기화.

        Args:
            parent: Parent widget / 부모 위젯
            config_manager: Configuration manager instance / 설정 관리자 인스턴스
            save_location: Directory where data files are stored / 데이터 파일 저장 디렉토리
            early_log_path: Path to early log file for reference / 참조용 초기 로그 파일 경로
        """
        super().__init__(parent)

        self.parent = parent
        self.config_manager = config_manager
        self.save_location = save_location
        self.early_log_path = early_log_path
        self.logger = logging.getLogger()

        # Track logging state / 로깅 상태 추적
        self.file_logging_initialized = False
        self.loaded_filename = None
        self.loaded_file_path = None

        # Results directory for saving figures
        # 그래프 저장을 위한 Results 디렉토리
        if save_location:
            self.results_dir = os.path.join(save_location, 'results')
        else:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.results_dir = os.path.join(current_dir, 'results')

        # Data storage / 데이터 저장
        self.df = None
        self.time_data = None
        self.ecg_data = None
        self.ecg_preprocessed = None
        self.hr_data = None

        # Column selection result / 컬럼 선택 결과
        self.column_selection = None

        # Marker storage / 마커 저장
        # Each: {"name": str, "column": int, "color": str, "times": list[float]}
        self.markers = []

        # Sampling rate (calculated from time data)
        # 샘플링 레이트 (시간 데이터에서 계산)
        self.sampling_rate = None

        # Start/End marker filter info for display
        # Start/End 마커 필터 정보 (표시용)
        self.filter_info = None

        # Annotations for hover tooltips / 호버 툴팁용 어노테이션
        self.annotation_raw = None
        self.annotation_preprocessed = None
        self.annotation_hr = None

        # Setup UI / UI 구성
        self.setup_ui()

        self.logger.info("ECG Offline analysis window initialized")

    def setup_ui(self):
        """
        Setup the user interface.
        사용자 인터페이스 구성.
        """
        # Window settings / 윈도우 설정
        self.setWindowTitle("ECG Offline Data Analysis")
        self.setGeometry(200, 100, 1200, 800)

        # Force light mode colors (ignore system dark mode)
        # 라이트 모드 강제 (시스템 다크 모드 무시)
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
            QMessageBox { background-color: #F0F0F0; color: #000000; }
            QMessageBox QLabel { color: #000000; }
            QMessageBox QPushButton { background-color: #FFFFFF; color: #000000; min-width: 80px; }
        """)

        # Main layout / 메인 레이아웃
        main_layout = QVBoxLayout()

        # === Top control panel / 상단 컨트롤 패널 ===
        control_layout = QHBoxLayout()

        # Load button / 로드 버튼
        self.btn_load = QPushButton("Load CSV File")
        self.btn_load.clicked.connect(self.load_csv_file)
        control_layout.addWidget(self.btn_load)

        # Select Preprocessing button (placeholder)
        # 전처리 선택 버튼 (placeholder)
        self.btn_preprocessing = QPushButton("Select Preprocessing")
        self.btn_preprocessing.clicked.connect(self._on_preprocessing_clicked)
        self.btn_preprocessing.setEnabled(False)
        control_layout.addWidget(self.btn_preprocessing)

        # File info label / 파일 정보 레이블
        self.label_file_info = QLabel("No file loaded")
        control_layout.addWidget(self.label_file_info)

        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        # === Matplotlib figure (3x1 grid with shared x-axis) ===
        # === Matplotlib 그래프 (3x1 그리드, 공유 x축) ===
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)

        # Create subplots (3 rows x 1 col) with shared x-axis
        # 서브플롯 생성 (3행 x 1열), 공유 x축
        self.ax_raw = self.figure.add_subplot(3, 1, 1)
        self.ax_preprocessed = self.figure.add_subplot(3, 1, 2, sharex=self.ax_raw)
        self.ax_hr = self.figure.add_subplot(3, 1, 3, sharex=self.ax_raw)

        # Initialize subplot titles and labels
        # 서브플롯 제목 및 레이블 초기화
        self.ax_raw.set_title("Raw ECG Signal")
        self.ax_raw.set_xlabel("Time (s)")
        self.ax_raw.set_ylabel("Amplitude")
        self.ax_raw.grid(True, alpha=0.3)

        self.ax_preprocessed.set_title("Preprocessed ECG Signal")
        self.ax_preprocessed.set_xlabel("Time (s)")
        self.ax_preprocessed.set_ylabel("Amplitude")
        self.ax_preprocessed.grid(True, alpha=0.3)

        self.ax_hr.set_title("Heart Rate")
        self.ax_hr.set_xlabel("Time (s)")
        self.ax_hr.set_ylabel("HR (bpm)")
        self.ax_hr.grid(True, alpha=0.3)

        # Apply layout settings / 레이아웃 설정 적용
        self.figure.subplots_adjust(hspace=0.7)

        # Add canvas to layout / 캔버스를 레이아웃에 추가
        main_layout.addWidget(self.canvas)

        # === Navigation toolbar / 네비게이션 툴바 ===
        self.toolbar = NavigationToolbar(self.canvas, self)
        main_layout.addWidget(self.toolbar)

        # Customize Home button behavior
        # Home 버튼 동작 커스터마이징
        self._original_home = self.toolbar.home
        for action in self.toolbar.actions():
            if action.text() and 'Home' in action.text():
                try:
                    action.triggered.disconnect()
                except TypeError:
                    pass
                action.triggered.connect(self._custom_home)
                break

        # Customize Save button behavior
        # Save 버튼 동작 커스터마이징
        for action in self.toolbar.actions():
            if action.text() and 'Save' in action.text():
                try:
                    action.triggered.disconnect()
                except TypeError:
                    pass
                action.triggered.connect(self.save_all_figures)
                break

        # === Bottom controls / 하단 컨트롤 ===
        bottom_controls_layout = QHBoxLayout()

        # Peak detection checkbox (disabled for now)
        # 피크 검출 체크박스 (현재 비활성화)
        self.checkbox_peaks = QCheckBox("Check Peaks")
        self.checkbox_peaks.setChecked(False)
        self.checkbox_peaks.setEnabled(False)
        bottom_controls_layout.addWidget(self.checkbox_peaks)

        # HR analysis controls (disabled for now)
        # HR 분석 컨트롤 (현재 비활성화)
        hr_label = QLabel("HR Analysis:")
        bottom_controls_layout.addWidget(hr_label)

        self.checkbox_hr = QCheckBox("Show HR")
        self.checkbox_hr.setChecked(False)
        self.checkbox_hr.setEnabled(False)
        bottom_controls_layout.addWidget(self.checkbox_hr)

        bottom_controls_layout.addStretch()
        main_layout.addLayout(bottom_controls_layout)

        # Set main layout / 메인 레이아웃 설정
        self.setLayout(main_layout)

        # Connect mouse events for hover tooltip and zoom
        # 호버 툴팁 및 줌을 위한 마우스 이벤트 연결
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)

    # =========================================================================
    # Data Loading / 데이터 로딩
    # =========================================================================

    def load_csv_file(self):
        """
        Open file dialog, load CSV, then open column selection dialog.
        파일 다이얼로그 열기, CSV 로드, 컬럼 선택 다이얼로그 열기.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ECG Data File / ECG 데이터 파일 선택",
            self.save_location if self.save_location else "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        self.logger.info(f"Selected file: {file_path}")

        try:
            # Open column selection dialog
            # 컬럼 선택 다이얼로그 열기
            from ecg.ecg_column_selection_dialog import ECGColumnSelectionDialog

            dialog = ECGColumnSelectionDialog(parent=self, file_path=file_path)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                self.logger.info("Column selection cancelled")
                return

            result = dialog.get_result()
            if result is None:
                return

            self.column_selection = result
            self.loaded_file_path = file_path

            # Extract base filename / 기본 파일명 추출
            filename = os.path.basename(file_path)
            base_filename = os.path.splitext(filename)[0]
            self.loaded_filename = base_filename

            # Load CSV with appropriate header setting
            # 적절한 헤더 설정으로 CSV 로드
            if result["has_header"]:
                self.df = pd.read_csv(file_path, low_memory=False)
            else:
                self.df = pd.read_csv(file_path, header=None, low_memory=False)

            # Drop columns that are entirely NaN (trailing comma)
            # 전체가 NaN인 컬럼 제거 (후행 쉼표)
            self.df = self.df.dropna(axis=1, how='all')

            # Process data based on selection / 선택에 따라 데이터 처리
            self._process_data(result)

            # Apply Start/End marker range filtering
            # Start/End 마커 범위 필터링 적용
            self._apply_start_end_filtering()

            # Initialize file-specific logging / 파일별 로깅 초기화
            if not self.file_logging_initialized:
                self._initialize_offline_logging(base_filename)

            # Update file info label / 파일 정보 레이블 업데이트
            self._update_file_info_label(filename)

            # Reset states / 상태 초기화
            self.ecg_preprocessed = None
            self.hr_data = None
            self.checkbox_peaks.setChecked(False)
            self.checkbox_hr.setChecked(False)

            # Enable preprocessing button / 전처리 버튼 활성화
            self.btn_preprocessing.setEnabled(True)

            # Plot data / 데이터 플로팅
            self.plot_data()

            self.logger.info(f"Data loaded successfully: {filename}")

        except Exception as e:
            self.logger.error(f"Failed to load CSV file: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Load Error",
                f"Failed to load CSV file:\nCSV 파일 로드 실패:\n\n{str(e)}"
            )

    def _process_data(self, result):
        """
        Extract selected columns from DataFrame and parse time.
        DataFrame에서 선택된 컬럼을 추출하고 시간을 파싱.

        Args:
            result: Column selection result dict / 컬럼 선택 결과 딕셔너리
        """
        time_col = result["time_column"]
        ecg_col = result["ecg_column"]

        # Extract time and ECG data by column index
        # 컬럼 인덱스로 시간 및 ECG 데이터 추출
        time_series = self.df.iloc[:, time_col]
        ecg_series = self.df.iloc[:, ecg_col]

        # Parse time column (auto-detect format)
        # 시간 컬럼 파싱 (형식 자동 감지)
        self.time_data = self._parse_time_column(time_series)

        # Convert ECG to float array / ECG를 float 배열로 변환
        self.ecg_data = pd.to_numeric(ecg_series, errors='coerce').values.astype(float)

        # Calculate sampling rate / 샘플링 레이트 계산
        if self.time_data is not None and len(self.time_data) > 1:
            duration = self.time_data[-1] - self.time_data[0]
            if duration > 0:
                self.sampling_rate = (len(self.time_data) - 1) / duration
            else:
                self.sampling_rate = None
        else:
            self.sampling_rate = None

        # Process markers / 마커 처리
        self.markers = []
        for marker_info in result.get("markers", []):
            marker_col = marker_info["column"]
            marker_data = pd.to_numeric(self.df.iloc[:, marker_col], errors='coerce').values

            # Find times where marker value == 1
            # 마커 값이 1인 시간 찾기
            marker_indices = np.where(marker_data == 1)[0]
            marker_times = self.time_data[marker_indices].tolist() if len(marker_indices) > 0 else []

            self.markers.append({
                "name": marker_info["name"],
                "column": marker_col,
                "color": marker_info["color"],
                "times": marker_times,
            })

            self.logger.info(
                f"Marker '{marker_info['name']}': {len(marker_times)} events found"
            )

    def _parse_time_column(self, time_series):
        """
        Convert time column to seconds (float). Auto-detect format.
        시간 컬럼을 초(float)로 변환. 형식 자동 감지.

        Supports:
        - Numeric seconds (already float)
        - HH:MM:SS or HH:MM:SS.mmm format (string)
        - Fallback: index-based

        Args:
            time_series: pandas Series with time values / 시간 값이 있는 pandas Series

        Returns:
            numpy.ndarray: Time in seconds / 초 단위 시간
        """
        # 1. Already numeric / 이미 숫자인 경우
        if pd.api.types.is_numeric_dtype(time_series):
            self.logger.info("Time format: numeric (float seconds)")
            return time_series.values.astype(float)

        # 2. Try converting string to numeric / 문자열 → 숫자 변환 시도
        try:
            result = pd.to_numeric(time_series)
            self.logger.info("Time format: numeric string → float seconds")
            return result.values.astype(float)
        except (ValueError, TypeError):
            pass

        # 3. Try timedelta conversion (HH:MM:SS.mmm)
        # timedelta 변환 시도 (HH:MM:SS.mmm)
        try:
            td = pd.to_timedelta(time_series)
            self.logger.info("Time format: HH:MM:SS.mmm → float seconds")
            return td.dt.total_seconds().values
        except (ValueError, TypeError):
            pass

        # 4. Fallback: index-based / 최후의 수단: 인덱스 기반
        self.logger.warning("Time format not recognized, using index-based time")
        self.sampling_rate = None
        return np.arange(len(time_series), dtype=float)

    def _apply_start_end_filtering(self):
        """
        Apply Start/End marker range filtering to the loaded data.
        Start/End 마커 범위 필터링을 로드된 데이터에 적용.

        Rules:
        - Both Start and End: use data from Start time to End time
        - Only Start: use Start time to end of data
        - Only End: use beginning of data to End time
        - Neither: use all data (no filtering)

        규칙:
        - Start와 End 모두: Start 시간부터 End 시간까지 사용
        - Start만: Start 시간부터 데이터 끝까지 사용
        - End만: 데이터 시작부터 End 시간까지 사용
        - 둘 다 없음: 전체 데이터 사용 (필터링 없음)
        """
        self.filter_info = None

        if not self.markers or self.time_data is None:
            return

        # Find Start and End markers (case-insensitive exact match)
        # Start/End 마커 찾기 (대소문자 무시 정확 매칭)
        start_time = None
        end_time = None

        for marker in self.markers:
            name_lower = marker["name"].strip().lower()
            if name_lower == "start" and marker["times"]:
                start_time = marker["times"][0]
                self.logger.info(f"Start marker found at {start_time:.3f}s")
            elif name_lower == "end" and marker["times"]:
                end_time = marker["times"][0]
                self.logger.info(f"End marker found at {end_time:.3f}s")

        # No Start/End markers: no filtering
        # Start/End 마커 없음: 필터링 없음
        if start_time is None and end_time is None:
            return

        # Determine filter boundaries / 필터 경계 결정
        data_start = self.time_data[0]
        data_end = self.time_data[-1]

        filter_start = start_time if start_time is not None else data_start
        filter_end = end_time if end_time is not None else data_end

        # Validate: start must be before end
        # 검증: 시작이 끝보다 앞이어야 함
        if filter_start >= filter_end:
            self.logger.warning(
                f"Start/End filter invalid: Start ({filter_start:.3f}s) >= "
                f"End ({filter_end:.3f}s). Skipping filtering."
            )
            return

        # Apply boolean mask / 부울 마스크 적용
        original_count = len(self.time_data)
        mask = (self.time_data >= filter_start) & (self.time_data <= filter_end)

        if not np.any(mask):
            self.logger.warning(
                "No data points found in Start/End range. Skipping filtering."
            )
            return

        self.time_data = self.time_data[mask]
        self.ecg_data = self.ecg_data[mask]

        # Shift time to start from 0
        # 시간을 0부터 시작하도록 시프트
        time_offset = self.time_data[0]
        self.time_data = self.time_data - time_offset

        # Filter marker times to the new range and shift to 0-based
        # 마커 시간을 새 범위로 필터링 후 0 기준으로 시프트
        for marker in self.markers:
            marker["times"] = [
                t - time_offset for t in marker["times"]
                if filter_start <= t <= filter_end
            ]

        # Recalculate sampling rate with filtered data
        # 필터링된 데이터로 샘플링 레이트 재계산
        if len(self.time_data) > 1:
            duration = self.time_data[-1] - self.time_data[0]
            if duration > 0:
                self.sampling_rate = (len(self.time_data) - 1) / duration

        # Build filter info string for display
        # 표시용 필터 정보 문자열 생성
        filter_parts = []
        if start_time is not None:
            filter_parts.append(f"Start={start_time:.2f}s")
        if end_time is not None:
            filter_parts.append(f"End={end_time:.2f}s")
        filtered_count = len(self.time_data)
        self.filter_info = f"{', '.join(filter_parts)} ({filtered_count} samples)"

        self.logger.info(
            f"Start/End filtering applied: {self.filter_info}, "
            f"samples: {original_count} -> {len(self.time_data)}"
        )

    def _update_file_info_label(self, filename):
        """
        Update file info label with data statistics.
        파일 정보 레이블을 데이터 통계로 업데이트.

        Args:
            filename: Loaded filename / 로드된 파일명
        """
        sample_count = len(self.time_data)
        duration = self.time_data[-1] - self.time_data[0] if len(self.time_data) > 1 else 0

        if self.sampling_rate is not None:
            info_text = (
                f"Loaded: {filename} | "
                f"{self.sampling_rate:.1f} Hz | "
                f"Duration: {duration:.1f}s | "
                f"Samples: {sample_count}"
            )
        else:
            info_text = (
                f"Loaded: {filename} | "
                f"Duration: {duration:.1f}s | "
                f"Samples: {sample_count}"
            )

        # Append filter info if Start/End filtering was applied
        # Start/End 필터링 적용 시 필터 정보 추가
        if self.filter_info:
            info_text += f" | Filtered: {self.filter_info}"

        self.label_file_info.setText(info_text)

    # =========================================================================
    # Plotting / 플로팅
    # =========================================================================

    def plot_data(self):
        """
        Clear and redraw all subplots with current data.
        현재 데이터로 모든 서브플롯을 지우고 다시 그리기.
        """
        if self.time_data is None or self.ecg_data is None:
            return

        # === Raw ECG Signal / Raw ECG 신호 ===
        self.ax_raw.clear()
        self.ax_raw.set_title("Raw ECG Signal")
        self.ax_raw.set_xlabel("Time (s)")
        self.ax_raw.set_ylabel("Amplitude")
        self.ax_raw.grid(True, alpha=0.3)

        # Plot ECG signal / ECG 신호 플로팅
        ecg_label = self.column_selection.get("ecg_column_name", "ECG") if self.column_selection else "ECG"
        self.ax_raw.plot(
            self.time_data, self.ecg_data,
            'k-', linewidth=0.5, alpha=0.8, label=ecg_label
        )

        # Plot markers / 마커 플로팅
        self._plot_markers(self.ax_raw)

        # Add legend / 범례 추가
        handles, labels = self.ax_raw.get_legend_handles_labels()
        if handles:
            self.ax_raw.legend(loc='upper right', fontsize=8)

        # === Preprocessed ECG Signal (empty for now) ===
        # === 전처리된 ECG 신호 (현재 비어 있음) ===
        self.ax_preprocessed.clear()
        self.ax_preprocessed.set_title("Preprocessed ECG Signal")
        self.ax_preprocessed.set_xlabel("Time (s)")
        self.ax_preprocessed.set_ylabel("Amplitude")
        self.ax_preprocessed.grid(True, alpha=0.3)

        if self.ecg_preprocessed is not None:
            self.ax_preprocessed.plot(
                self.time_data, self.ecg_preprocessed,
                'k-', linewidth=0.5, alpha=0.8, label="ECG (preprocessed)"
            )
            self.ax_preprocessed.legend(loc='upper right', fontsize=8)

        # === Heart Rate (empty for now) ===
        # === 심박수 (현재 비어 있음) ===
        self.ax_hr.clear()
        self.ax_hr.set_title("Heart Rate")
        self.ax_hr.set_xlabel("Time (s)")
        self.ax_hr.set_ylabel("HR (bpm)")
        self.ax_hr.grid(True, alpha=0.3)

        if self.hr_data is not None:
            valid_mask = ~np.isnan(self.hr_data)
            if np.any(valid_mask):
                self.ax_hr.plot(
                    self.time_data[valid_mask], self.hr_data[valid_mask],
                    'k-', linewidth=1.0, label="Heart Rate"
                )
                self.ax_hr.legend(loc='upper right', fontsize=8)

        # Apply layout and redraw / 레이아웃 적용 및 다시 그리기
        self.figure.subplots_adjust(hspace=0.7)

        # Reset annotations / 어노테이션 초기화
        self.annotation_raw = None
        self.annotation_preprocessed = None
        self.annotation_hr = None

        self.canvas.draw()

    def _plot_markers(self, ax):
        """
        Draw vertical dashed lines for event markers.
        이벤트 마커를 위한 수직 점선 그리기.

        Args:
            ax: Matplotlib axis / Matplotlib 축
        """
        for marker in self.markers:
            color = marker["color"]
            name = marker["name"]
            times = marker["times"]

            if not times:
                continue

            # Skip Start/End markers (range already reflected by data filtering)
            # Start/End 마커는 데이터 필터링으로 이미 범위가 반영되므로 표시 생략
            if name.strip().lower() in ("start", "end"):
                continue

            for i, t in enumerate(times):
                # Only add label on first line for legend
                # 범례에 첫 번째 라인에만 레이블 추가
                label = name if i == 0 else None
                ax.axvline(
                    x=t, color=color, linestyle='--',
                    linewidth=1.0, alpha=0.7, label=label
                )

    # =========================================================================
    # Mouse Interaction / 마우스 인터랙션
    # =========================================================================

    def on_mouse_move(self, event):
        """
        Handle mouse move event for hover tooltip.
        호버 툴팁을 위한 마우스 이동 이벤트 처리.

        Args:
            event: Matplotlib mouse event / Matplotlib 마우스 이벤트
        """
        if self.time_data is None:
            return

        if event.inaxes == self.ax_raw:
            self._update_annotation_raw(event)
            if self.annotation_preprocessed is not None:
                self.annotation_preprocessed.set_visible(False)
            if self.annotation_hr is not None:
                self.annotation_hr.set_visible(False)
        elif event.inaxes == self.ax_preprocessed:
            self._update_annotation_preprocessed(event)
            if self.annotation_raw is not None:
                self.annotation_raw.set_visible(False)
            if self.annotation_hr is not None:
                self.annotation_hr.set_visible(False)
        elif event.inaxes == self.ax_hr:
            self._update_annotation_hr(event)
            if self.annotation_raw is not None:
                self.annotation_raw.set_visible(False)
            if self.annotation_preprocessed is not None:
                self.annotation_preprocessed.set_visible(False)
        else:
            # Hide all annotations / 모든 어노테이션 숨기기
            if self.annotation_raw is not None:
                self.annotation_raw.set_visible(False)
            if self.annotation_preprocessed is not None:
                self.annotation_preprocessed.set_visible(False)
            if self.annotation_hr is not None:
                self.annotation_hr.set_visible(False)
            self.canvas.draw_idle()

    def _update_annotation_raw(self, event):
        """
        Update annotation for Raw ECG Signal graph.
        Raw ECG Signal 그래프 어노테이션 업데이트.

        Args:
            event: Matplotlib mouse event / Matplotlib 마우스 이벤트
        """
        if event.xdata is None or event.ydata is None:
            return

        # Find nearest data point / 가장 가까운 데이터 포인트 찾기
        idx = np.argmin(np.abs(self.time_data - event.xdata))
        x_point = self.time_data[idx]
        y_point = self.ecg_data[idx]

        # Create or update annotation / 어노테이션 생성 또는 업데이트
        if self.annotation_raw is None:
            self.annotation_raw = self.ax_raw.annotate(
                '', xy=(x_point, y_point),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='lightyellow', alpha=0.9),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )

        self.annotation_raw.xy = (x_point, y_point)
        self.annotation_raw.set_text(f'Time: {x_point:.3f}s\nECG: {y_point:.6f}')
        self.annotation_raw.set_visible(True)
        self.canvas.draw_idle()

    def _update_annotation_preprocessed(self, event):
        """
        Update annotation for Preprocessed ECG Signal graph.
        Preprocessed ECG Signal 그래프 어노테이션 업데이트.

        Args:
            event: Matplotlib mouse event / Matplotlib 마우스 이벤트
        """
        if event.xdata is None or event.ydata is None:
            return

        if self.ecg_preprocessed is None:
            return

        idx = np.argmin(np.abs(self.time_data - event.xdata))
        x_point = self.time_data[idx]
        y_point = self.ecg_preprocessed[idx]

        if self.annotation_preprocessed is None:
            self.annotation_preprocessed = self.ax_preprocessed.annotate(
                '', xy=(x_point, y_point),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='lightcyan', alpha=0.9),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )

        self.annotation_preprocessed.xy = (x_point, y_point)
        self.annotation_preprocessed.set_text(f'Time: {x_point:.3f}s\nECG: {y_point:.6f}')
        self.annotation_preprocessed.set_visible(True)
        self.canvas.draw_idle()

    def _update_annotation_hr(self, event):
        """
        Update annotation for Heart Rate graph.
        Heart Rate 그래프 어노테이션 업데이트.

        Args:
            event: Matplotlib mouse event / Matplotlib 마우스 이벤트
        """
        if event.xdata is None or event.ydata is None:
            return

        if self.hr_data is None:
            return

        idx = np.argmin(np.abs(self.time_data - event.xdata))
        x_point = self.time_data[idx]
        hr_value = self.hr_data[idx]

        if np.isnan(hr_value):
            return

        if self.annotation_hr is None:
            self.annotation_hr = self.ax_hr.annotate(
                '', xy=(x_point, hr_value),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='lightyellow', alpha=0.9),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )

        self.annotation_hr.xy = (x_point, hr_value)
        self.annotation_hr.set_text(f'Time: {x_point:.3f}s\nHR: {hr_value:.1f} bpm')
        self.annotation_hr.set_visible(True)
        self.canvas.draw_idle()

    def on_scroll(self, event):
        """
        Handle mouse scroll event for zooming.
        줌을 위한 마우스 스크롤 이벤트 처리.

        Args:
            event: Matplotlib scroll event / Matplotlib 스크롤 이벤트
        """
        if event.inaxes is None:
            return

        # Get current x-axis limits / 현재 x축 범위 가져오기
        cur_xlim = event.inaxes.get_xlim()

        # Zoom factor / 줌 팩터
        base_scale = 1.2

        if event.button == 'up':
            scale_factor = 1 / base_scale  # Zoom in
        elif event.button == 'down':
            scale_factor = base_scale  # Zoom out
        else:
            return

        # Calculate new limits centered on cursor
        # 커서 중심으로 새 범위 계산
        xdata = event.xdata
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])

        new_xlim = [xdata - new_width * (1 - relx), xdata + new_width * relx]

        # Apply to the axis - sharex will automatically sync all other axes
        # 축에 적용 - sharex가 다른 축도 자동 동기화
        event.inaxes.set_xlim(new_xlim)

        self.canvas.draw_idle()

    # =========================================================================
    # Navigation / 네비게이션
    # =========================================================================

    def _custom_home(self, *args):
        """
        Custom Home button behavior - reset to full data range.
        Home 버튼 커스텀 동작 - 전체 데이터 범위로 리셋.
        """
        if self.time_data is None:
            self._original_home(*args)
            return

        # Reset x-axis to full data range
        # x축을 전체 데이터 범위로 리셋
        x_min, x_max = np.nanmin(self.time_data), np.nanmax(self.time_data)
        self.ax_raw.set_xlim(x_min, x_max)

        # Update Raw ECG y-axis / Raw ECG y축 업데이트
        if self.ecg_data is not None:
            y_min, y_max = np.nanmin(self.ecg_data), np.nanmax(self.ecg_data)
            margin = (y_max - y_min) * 0.05
            self.ax_raw.set_ylim(y_min - margin, y_max + margin)

        # Update Preprocessed y-axis / Preprocessed y축 업데이트
        if self.ecg_preprocessed is not None:
            y_min, y_max = np.nanmin(self.ecg_preprocessed), np.nanmax(self.ecg_preprocessed)
            margin = (y_max - y_min) * 0.05
            self.ax_preprocessed.set_ylim(y_min - margin, y_max + margin)

        # Update HR y-axis / HR y축 업데이트
        if self.hr_data is not None:
            valid = self.hr_data[~np.isnan(self.hr_data)]
            if len(valid) > 0:
                self.ax_hr.set_ylim(np.min(valid) - 5, np.max(valid) + 5)

        # Other subplot y-axes: autoscale
        # 기타 서브플롯 y축: autoscale
        for ax in [self.ax_preprocessed, self.ax_hr]:
            ax.relim()
            ax.autoscale_view(scalex=False, scaley=True)

        self.canvas.draw()

    # =========================================================================
    # Preprocessing (Placeholder) / 전처리 (Placeholder)
    # =========================================================================

    def _on_preprocessing_clicked(self):
        """
        Handle Select Preprocessing button click (placeholder).
        Select Preprocessing 버튼 클릭 처리 (placeholder).
        """
        self.logger.info("Select Preprocessing button clicked (placeholder)")
        QMessageBox.information(
            self, "Select Preprocessing",
            "ECG preprocessing feature will be implemented soon.\n\n"
            "ECG 전처리 기능이 곧 구현될 예정입니다."
        )

    # =========================================================================
    # Save / 저장
    # =========================================================================

    def save_all_figures(self):
        """
        Save all graphs with data as individual PNG files.
        데이터가 있는 모든 그래프를 개별 PNG 파일로 저장.

        Files saved to: Results/YYYYMMDD/{loaded_filename}_{graph_name}.png
        """
        if self.loaded_filename is None or self.time_data is None:
            QMessageBox.warning(
                self, "Save Error",
                "No data loaded. Please load a CSV file first.\n"
                "데이터가 로드되지 않았습니다. 먼저 CSV 파일을 로드하세요."
            )
            return

        try:
            # Create date-based results folder / 날짜 기반 results 폴더 생성
            date_folder = datetime.now().strftime("%Y%m%d")
            results_session_dir = os.path.join(self.results_dir, date_folder)
            os.makedirs(results_session_dir, exist_ok=True)

            # Build list of graphs to save (only those with data)
            # 저장할 그래프 목록 (데이터가 있는 것만)
            graphs = []
            if self.ecg_data is not None:
                graphs.append((self.ax_raw, "Raw_ECG_Signal"))
            if self.ecg_preprocessed is not None:
                graphs.append((self.ax_preprocessed, "Preprocessed_ECG_Signal"))
            if self.hr_data is not None:
                graphs.append((self.ax_hr, "Heart_Rate"))

            if not graphs:
                QMessageBox.warning(
                    self, "Save Error",
                    "No graphs with data to save.\n"
                    "저장할 데이터가 있는 그래프가 없습니다."
                )
                return

            saved_files = []
            for ax, graph_name in graphs:
                base_filename = f"{self.loaded_filename}_{graph_name}.png"
                filename = self._get_unique_filename(results_session_dir, base_filename)
                filepath = self._save_single_figure(ax, results_session_dir, filename)
                saved_files.append(filepath)

            # Success message / 성공 메시지
            QMessageBox.information(
                self, "Save Complete",
                f"All figures saved successfully!\n"
                f"모든 그래프가 성공적으로 저장되었습니다!\n\n"
                f"Location: {results_session_dir}\n"
                f"Files:\n" + "\n".join([f"  - {os.path.basename(f)}" for f in saved_files])
            )

            self.logger.info(f"All figures saved to: {results_session_dir}")

        except Exception as e:
            self.logger.error(f"Failed to save figures: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Save Error",
                f"Failed to save figures:\n그래프 저장 실패:\n\n{str(e)}"
            )

    def _save_single_figure(self, ax, results_session_dir, filename, dpi=300):
        """
        Save a single subplot as an individual PNG file.
        단일 서브플롯을 개별 PNG 파일로 저장.

        Args:
            ax: Matplotlib axis to save / 저장할 Matplotlib 축
            results_session_dir: Target directory / 저장 대상 디렉토리
            filename: Output filename / 출력 파일명
            dpi: Image resolution / 이미지 해상도

        Returns:
            str: Full path of saved file / 저장된 파일의 전체 경로
        """
        # Create new figure / 새 Figure 생성
        fig_single, ax_single = plt.subplots(figsize=(10, 6))

        # Copy line data / 라인 데이터 복사
        for line in ax.get_lines():
            xdata = line.get_xdata()
            ydata = line.get_ydata()

            # Detect axvline lines (vertical marker lines in axes coords)
            # axvline 감지 (axes 좌표계의 수직 마커 라인)
            if (len(xdata) == 2 and len(ydata) == 2
                    and xdata[0] == xdata[1]
                    and ydata[0] == 0 and ydata[1] == 1):
                ax_single.axvline(
                    x=xdata[0],
                    color=line.get_color(),
                    linewidth=line.get_linewidth(),
                    alpha=line.get_alpha() if line.get_alpha() is not None else 0.7,
                    linestyle=line.get_linestyle(),
                    label=line.get_label() if not line.get_label().startswith('_') else None
                )
            else:
                ax_single.plot(
                    xdata, ydata,
                    color=line.get_color(),
                    linewidth=line.get_linewidth(),
                    alpha=line.get_alpha() if line.get_alpha() is not None else 1.0,
                    linestyle=line.get_linestyle(),
                    label=line.get_label() if not line.get_label().startswith('_') else None
                )

        # Copy scatter data (peak markers)
        # scatter 데이터 복사 (피크 마커)
        for collection in ax.collections:
            offsets = collection.get_offsets()
            if len(offsets) > 0:
                facecolors = collection.get_facecolor()
                sizes = collection.get_sizes()
                ax_single.scatter(
                    offsets[:, 0], offsets[:, 1],
                    c=[facecolors[0]] if len(facecolors) > 0 else 'red',
                    s=sizes[0] if len(sizes) > 0 else 20,
                    marker='o', zorder=5
                )

        # Copy axis settings / 축 설정 복사
        ax_single.set_title(ax.get_title())
        ax_single.set_xlabel(ax.get_xlabel())
        ax_single.set_ylabel(ax.get_ylabel())
        ax_single.set_xlim(ax.get_xlim())
        ax_single.set_ylim(ax.get_ylim())
        ax_single.grid(True, alpha=0.3)

        # Add legend if exists / 범례 추가 (있는 경우)
        handles, labels = ax_single.get_legend_handles_labels()
        if handles:
            ax_single.legend(loc='upper right', fontsize=8)

        # Save / 저장
        filepath = os.path.join(results_session_dir, filename)
        fig_single.tight_layout()
        fig_single.savefig(filepath, dpi=dpi, bbox_inches='tight')
        plt.close(fig_single)

        self.logger.info(f"Figure saved: {filepath}")
        return filepath

    def _get_unique_filename(self, results_session_dir, filename):
        """
        Get unique filename by adding suffix before extension if file already exists.
        파일이 존재하면 확장자 앞에 접미사를 추가하여 고유한 파일명 반환.

        Args:
            results_session_dir: Target directory / 저장 대상 디렉토리
            filename: Original filename (e.g., "data_Raw_ECG_Signal.png")

        Returns:
            str: Unique filename (e.g., "data_Raw_ECG_Signal.png" or "data_Raw_ECG_Signal_2.png")
        """
        if not os.path.exists(os.path.join(results_session_dir, filename)):
            return filename

        # If file exists, add counter suffix before extension
        # 파일 존재 시 확장자 앞에 카운터 추가
        name, ext = os.path.splitext(filename)
        counter = 2
        while True:
            new_filename = f"{name}_{counter}{ext}"
            if not os.path.exists(os.path.join(results_session_dir, new_filename)):
                self.logger.info(f"Filename '{filename}' exists, using '{new_filename}'")
                return new_filename
            counter += 1

    # =========================================================================
    # Logging / 로깅
    # =========================================================================

    def _initialize_offline_logging(self, base_filename):
        """
        Initialize logging for offline analysis based on loaded CSV filename.
        로드된 CSV 파일명에 기반한 오프라인 분석 로깅 초기화.

        Transitions from early logging (YYYYMMDD_HHMMSS.log)
        to file-specific logging (e.g., data_file_offline.log).
        초기 로깅에서 파일별 로깅으로 전환.

        Args:
            base_filename: Base filename from loaded CSV / 로드된 CSV 기본 파일명
        """
        if self.file_logging_initialized:
            return

        # Get early log path / 초기 로그 경로 가져오기
        early_log_path = self.early_log_path or getattr(self.parent, 'early_log_path', None)

        self.logger.info("=" * 60)
        self.logger.info("OFFLINE ANALYSIS CSV LOADED - TRANSITIONING TO FILE-SPECIFIC LOG")
        self.logger.info("=" * 60)
        if early_log_path:
            self.logger.info(f"Early log file location: {early_log_path}")
        self.logger.info(f"Loaded CSV base filename: {base_filename}")

        # Generate unique offline log filename
        # 고유한 오프라인 로그 파일명 생성
        offline_log_filename = f"{base_filename}_offline"
        offline_log_filename = self._get_unique_log_filename(offline_log_filename)

        self.logger.info(f"New log filename: {offline_log_filename}.log")
        self.logger.info("Early logging will now stop, and file-specific logging will begin")
        self.logger.info("=" * 60)

        # Import and call setup_logging
        # setup_logging 임포트 및 호출
        from common_utils import setup_logging
        setup_logging(offline_log_filename, save_location=self.save_location)

        # Log in the new file-specific log file
        # 새 파일별 로그에 기록
        self.logger = logging.getLogger()
        self.logger.info("=" * 60)
        self.logger.info("OFFLINE ANALYSIS SESSION STARTED")
        self.logger.info("=" * 60)
        self.logger.info(f"Analyzing file: {base_filename}")
        self.logger.info(f"Save location: {self.save_location}")
        if early_log_path:
            self.logger.info(f"Related Early Log: {early_log_path}")
        else:
            self.logger.info("No early log (direct launch)")
        self.logger.info("File-specific offline logging is now active")
        self.logger.info("=" * 60)

        self.file_logging_initialized = True

    def _get_unique_log_filename(self, base_log_filename):
        """
        Get unique log filename by checking for existing log files.
        기존 로그 파일을 확인하여 고유한 로그 파일명 반환.

        Args:
            base_log_filename: Base log filename (without .log extension)
                              기본 로그 파일명 (.log 확장자 없이)

        Returns:
            str: Unique log filename (without .log extension)
        """
        if not self.save_location:
            return base_log_filename

        date_folder = datetime.now().strftime("%Y%m%d")
        log_dir = os.path.join(self.save_location, "log", date_folder)

        if not os.path.exists(log_dir):
            return base_log_filename

        # Check if log file already exists
        # 로그 파일이 이미 존재하는지 확인
        test_path = os.path.join(log_dir, f"{base_log_filename}.log")
        if not os.path.exists(test_path):
            return base_log_filename

        # Add counter suffix / 카운터 접미사 추가
        counter = 2
        while True:
            new_filename = f"{base_log_filename}_{counter}"
            test_path = os.path.join(log_dir, f"{new_filename}.log")
            if not os.path.exists(test_path):
                return new_filename
            counter += 1
