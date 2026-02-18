"""
ECG Analysis Mode Selection Window
ECG 분석 모드 선택 윈도우

Displays ECG analysis mode options after signal selection.
신호 선택 후 ECG 분석 모드 옵션을 표시합니다.

Mode options / 모드 옵션:
- Real-time Data Analysis (coming soon) / 실시간 데이터 분석 (준비 중)
- Offline Data Analysis (available) / 오프라인 데이터 분석 (사용 가능)
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt


class ECGMonitorModeWindow(QDialog):
    """
    ECG analysis mode selection dialog
    ECG 분석 모드 선택 다이얼로그

    Allows users to select analysis mode:
    사용자가 분석 모드를 선택할 수 있습니다:
    - Real-time Data Analysis (coming soon) / 실시간 데이터 분석 (준비 중)
    - Offline Data Analysis (load and analyze previously saved data)
      오프라인 데이터 분석 (이전에 저장된 데이터를 로드하여 분석)

    Attributes:
        logger: Logger object / 로거 객체
        selected_mode: Selected mode string (None if not selected)
                       선택된 모드 문자열 (미선택 시 None)
    """

    def __init__(self, parent=None):
        """
        Initialize ECG analysis mode selection window.
        ECG 분석 모드 선택 윈도우를 초기화합니다.

        Args:
            parent: Parent widget (MainWindow)
                    부모 위젯 (MainWindow)
        """
        super().__init__(parent)

        # Logger for tracking user actions
        # 사용자 작업 추적을 위한 로거
        self.logger = logging.getLogger()

        # Track selected mode / 선택된 모드 추적
        self.selected_mode = None

        # Setup UI / UI 구성
        self.setup_ui()

        self.logger.info("ECG Analysis Mode Selection window opened")

    def setup_ui(self):
        """
        Set up user interface layout.
        사용자 인터페이스 레이아웃을 구성합니다.

        Window composition / 윈도우 구성:
        - Title and subtitle / 제목과 부제목
        - 2 mode selection buttons (Real-time disabled, Offline enabled)
          2개 모드 선택 버튼 (실시간 비활성, 오프라인 활성)
        - Bottom Exit button / 하단 Exit 버튼
        """
        # Window configuration / 윈도우 설정
        self.setWindowTitle("Analysis Mode")
        self.setFixedSize(500, 350)
        self.setStyleSheet("""
            QDialog {
                background-color: #F0F0F0;
                color: #000000;
            }
            QLabel, QPushButton {
                color: #000000;
            }
        """)

        # Main layout / 메인 레이아웃
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Title / 제목
        title_label = QLabel("Select ECG Analysis Mode")
        title_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #000000;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Subtitle / 부제목
        subtitle_label = QLabel("Choose an analysis mode")
        subtitle_label.setStyleSheet("font-size: 14pt; color: #7f8c8d;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle_label)

        # Add some spacing / 간격 추가
        main_layout.addSpacing(20)

        # Button 1: Real-time Data Analysis (Disabled - Coming Soon)
        # 버튼 1: 실시간 데이터 분석 (비활성 - 준비 중)
        self.btn_realtime = QPushButton("Real-time Data Analysis\n(Coming Soon)")
        self.btn_realtime.setEnabled(False)
        self.btn_realtime.setStyleSheet("""
            QPushButton {
                background-color: #bdc3c7;
                color: #7f8c8d;
                font-size: 14pt;
                min-height: 60px;
                border: 3px solid #95a5a6;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(self.btn_realtime)

        # Button 2: Offline Data Analysis (Available)
        # 버튼 2: 오프라인 데이터 분석 (사용 가능)
        self.btn_offline_analysis = QPushButton("Offline Data Analysis")
        self.btn_offline_analysis.setStyleSheet("""
            QPushButton {
                font-size: 14pt;
                min-height: 60px;
            }
        """)
        self.btn_offline_analysis.clicked.connect(lambda: self.select_mode("Offline Analysis"))
        main_layout.addWidget(self.btn_offline_analysis)

        # Add stretch to push Exit button to bottom
        # Exit 버튼을 아래로 밀기 위한 스트레치 추가
        main_layout.addStretch()

        # Exit button layout (aligned to right, matching Main GUI)
        # Exit 버튼 레이아웃 (우측 정렬, Main GUI와 일치)
        exit_layout = QHBoxLayout()
        exit_layout.addStretch()  # Push button to right

        # Exit button (matching Main GUI Exit button style and size)
        # Exit 버튼 (Main GUI Exit 버튼 스타일 및 크기와 일치)
        self.btn_exit = QPushButton("Exit")
        self.btn_exit.clicked.connect(self.on_exit)
        exit_layout.addWidget(self.btn_exit)

        main_layout.addLayout(exit_layout)

        self.setLayout(main_layout)

    def select_mode(self, mode):
        """
        Handle analysis mode selection.
        분석 모드 선택을 처리합니다.

        Args:
            mode: Selected mode name / 선택된 모드 이름
        """
        self.logger.info(f"User selected analysis mode: {mode}")
        self.selected_mode = mode

        self.logger.info(f"Proceeding to ECG analysis with mode: {mode}")

        # Run appropriate analysis GUI based on selected mode
        # 선택된 모드에 따라 적절한 분석 GUI 실행
        self.accept()

    def on_exit(self):
        """
        Handle Exit button click - return to Main GUI.
        Exit 버튼 클릭 처리 - Main GUI로 복귀합니다.

        Actions / 동작:
        - Set selected_mode to None / selected_mode를 None으로 설정
        - Close window / 윈도우 닫기
        """
        self.logger.info("User clicked Exit button in analysis mode selection")
        self.logger.info("Returning to Main GUI")
        self.selected_mode = None
        self.reject()
