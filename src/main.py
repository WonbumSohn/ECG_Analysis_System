# Standard library imports / 표준 라이브러리 임포트
import sys                        # Python interpreter arguments and exit handling
import os                         # File system path operations
import logging                    # Logging functionality
# PySide6: GUI related class imports
# PySide6: GUI 관련 클래스 임포트
from PySide6.QtWidgets import (    # Qt widgets (buttons, labels, etc.)
    QApplication,                  # Qt application (event loop) object
    QMainWindow,                   # Main window frame
    QWidget,                       # Base class for widgets
    QVBoxLayout,                   # Vertical layout
    QPushButton,                   # Button widget
    QLabel,                        # Text display label
    QHBoxLayout,                   # Horizontal layout
    QMessageBox,                   # Message box dialog
    QLineEdit,                     # Single line text input field
    QFileDialog                    # File/folder selection dialog
)
# Background task threads, signals, and alignment constants
from PySide6.QtCore import Qt

# Import utility functions / 유틸리티 함수 임포트
from common_utils import setup_early_logging
# Import configuration manager / 설정 관리자 임포트
from config_manager import ConfigManager


# =========================
# Main Window
# 메인 윈도우
# =========================

# MainWindow class: Defines main interface
# MainWindow 클래스: 메인 인터페이스 정의
class MainWindow(QMainWindow):
    # Constructor initializes UI elements and connects events
    def __init__(self):
        # Call parent class (QMainWindow) constructor
        super().__init__()

        # -------------------------------
        # (0) Configuration Manager and Save Location Initialization
        # (0) 설정 관리자 및 저장 위치 초기화
        # -------------------------------
        # Create temporary configuration manager to load previous common settings
        # 이전 공통 설정을 로드하기 위한 임시 설정 관리자 생성
        temp_config_manager = ConfigManager(config_filename="common_parameters.json")

        # Load saved common configuration
        # 저장된 공통 설정 로드
        config = temp_config_manager.load_config()
        if config is None:
            config = {}

        # Initialize save location (load from config or use default)
        # 저장 위치 초기화 (설정에서 로드 또는 기본값 사용)
        saved_location = config.get('save_location')
        if saved_location and os.path.exists(saved_location):
            # Use previously saved location if it exists and is valid
            self.save_location = saved_location
        else:
            # Default: ~/Documents/ECG_Data
            home_dir = os.path.expanduser("~")
            self.save_location = os.path.join(home_dir, "Documents", "ECG_Data")

        # ConfigManager will be created after user confirms save location
        # 사용자가 저장 위치를 확인한 후 ConfigManager가 생성됩니다
        self.config_manager = None

        # -------------------------------
        # (0.5) Early Logging Initialization
        # (0.5) 초기 로깅 초기화
        # -------------------------------
        # DO NOT initialize early logging yet
        # Early logging will be initialized when user confirms save location
        # 아직 초기 로깅을 초기화하지 않음
        # 사용자가 저장 위치를 확인할 때 초기 로깅이 초기화됩니다
        self.early_logger = None
        self.early_log_path = None

        # -------------------------------
        # (1) Main Window Setup
        # (1) 메인 윈도우 설정
        # -------------------------------
        # Set window title / 윈도우 제목 설정
        self.setWindowTitle("ECG Analysis System")
        # Set window size and position / 윈도우 크기 및 위치 설정
        self.setGeometry(500, 100, 480, 500)
        # Fix background color to light gray and all text to black
        # 배경색을 밝은 회색으로, 모든 텍스트를 검정색으로 고정
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F0F0F0;
            }
            QWidget {
                background-color: #F0F0F0;
                color: #000000;
            }
            QLabel, QPushButton {
                color: #000000;
            }
            QMessageBox {
                background-color: #F0F0F0;
            }
        """)

        # Create top welcome message label / 상단 환영 메시지 레이블 생성
        welcome_label = QLabel("Welcome!")
        # Set font size to 24pt / 폰트 크기 24pt로 설정
        welcome_label.setStyleSheet("font-size: 24pt;")
        # Center align text / 텍스트 가운데 정렬
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create main title label / 메인 제목 레이블 생성
        title_label = QLabel("ECG Analysis System")
        # Set font size to 36pt and bold (36pt for longer title)
        # 폰트 크기 36pt, 볼드 (긴 제목을 위해 36pt)
        title_label.setStyleSheet("font-size: 36pt; font-weight: bold;")
        # Center align text / 텍스트 가운데 정렬
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create subtitle label / 부제목 레이블 생성
        subtitle_label = QLabel("ECG Signal Analysis Interface")
        # Set font size to 18pt and gray color
        subtitle_label.setStyleSheet("font-size: 18pt; color: gray;")
        # Center align text / 텍스트 가운데 정렬
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create author info and version label
        # 저자 정보 및 버전 레이블 생성
        author_label = QLabel("Body Data Interface Lab | Wonbum Sohn | Version 0.1.0")
        # Set font size to 12pt and black color
        author_label.setStyleSheet("font-size: 12pt; color: black;")
        # Center align text / 텍스트 가운데 정렬
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ===== Save Location Selection Section (set first at app startup) =====
        # ===== 저장 위치 선택 섹션 (앱 시작 시 가장 먼저 설정) =====

        # Create save location selection label
        # 저장 위치 선택 레이블 생성
        self.label_save_location = QLabel("Save Location:")

        # Horizontal layout for save location section (path display + Browse button)
        # 저장 위치 섹션 수평 레이아웃 (경로 표시 + Browse 버튼)
        save_layout = QHBoxLayout()

        # Read-only input field displaying selected path
        # 선택된 경로를 표시하는 읽기 전용 입력 필드
        self.save_path_entry = QLineEdit()
        self.save_path_entry.setText(self.save_location)
        self.save_path_entry.setReadOnly(True)
        self.save_path_entry.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: #333333;
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
        """)
        save_layout.addWidget(self.save_path_entry)

        # Create Browse button and connect click event
        # Browse 버튼 생성 및 클릭 이벤트 연결
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setFixedWidth(100)
        self.btn_browse.clicked.connect(self.browse_save_location)
        save_layout.addWidget(self.btn_browse)

        # Create Set button to confirm save location
        # 저장 위치 확인을 위한 Set 버튼 생성
        self.btn_set_location = QPushButton("Set")
        self.btn_set_location.setFixedWidth(60)
        self.btn_set_location.clicked.connect(self.set_save_location)
        save_layout.addWidget(self.btn_set_location)

        # Flag to track if save location has been confirmed
        # 저장 위치 확인 여부를 추적하는 플래그
        self.location_is_set = False

        # Initialize variables to store signal selection buttons
        # 신호 선택 버튼을 저장할 변수 초기화
        self.signal_buttons_visible = False
        self.signal_buttons = []
        self.signal_instruction_label = None

        # Layout composition: title → save location → (signal buttons after confirmation) in vertical order
        # 레이아웃 구성: 제목 → 저장 위치 → (확인 후 신호 버튼) 순서로 수직 배치
        layout = QVBoxLayout()
        layout.addWidget(welcome_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(author_label)
        layout.addWidget(self.label_save_location)
        layout.addLayout(save_layout)

        # Add stretch for space expansion (to push Exit button down)
        # 공간 확장을 위한 스트레치 추가 (Exit 버튼을 아래로 밀기 위해)
        layout.addStretch()

        # Create horizontal layout for right-aligning Exit button
        # Exit 버튼 우측 정렬을 위한 수평 레이아웃 생성
        exit_layout = QHBoxLayout()
        # Add space on left (for right alignment effect)
        exit_layout.addStretch()
        # Create Exit button / Exit 버튼 생성
        self.btn_exit = QPushButton("Exit")
        # Close application when button clicked
        # 버튼 클릭 시 애플리케이션 종료
        self.btn_exit.clicked.connect(self.close_application)
        exit_layout.addWidget(self.btn_exit)
        # Add Exit layout to main layout
        layout.addLayout(exit_layout)

        # Apply layout to central container widget and mount to main window
        # 레이아웃을 중앙 컨테이너 위젯에 적용하고 메인 윈도우에 마운트
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    # Function to select save location
    # 저장 위치 선택 함수
    def browse_save_location(self):
        """
        Opens folder selection dialog to choose result save location.
        폴더 선택 다이얼로그를 열어 결과 저장 위치를 선택합니다.

        Called when user clicks Browse button.
        사용자가 Browse 버튼을 클릭할 때 호출됩니다.
        User must click Set button to confirm the location.
        사용자는 Set 버튼을 클릭하여 위치를 확인해야 합니다.
        """
        # Get current save location
        current_location = self.save_location

        # Check if current location exists, use home directory if not
        # 현재 위치가 존재하는지 확인, 없으면 홈 디렉토리 사용
        if os.path.exists(current_location):
            initial_dir = current_location
        else:
            # Use home directory as initial location
            initial_dir = os.path.expanduser("~")

        # Open folder selection dialog / 폴더 선택 다이얼로그 열기
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Save Location",  # Dialog title
            initial_dir,              # Initial directory
            QFileDialog.Option.ShowDirsOnly  # Show folders only
        )

        # If user selected a folder (not cancelled)
        # 사용자가 폴더를 선택한 경우 (취소하지 않은 경우)
        if selected_dir:
            self.save_location = selected_dir
            self.save_path_entry.setText(selected_dir)

    def set_save_location(self):
        """
        Confirm and set save location when user clicks Set button.
        사용자가 Set 버튼을 클릭할 때 저장 위치를 확인하고 설정합니다.

        This reveals the signal selection buttons.
        이 함수는 신호 선택 버튼을 표시합니다.
        """
        # Validate that a location is selected
        # 위치가 선택되었는지 확인
        current_location = self.save_path_entry.text().strip()

        if not current_location:
            QMessageBox.warning(
                self,
                "Invalid Location",
                "Please select a save location first."
            )
            return

        # Mark location as set / 위치 설정 완료 표시
        self.location_is_set = True

        # Initialize early logging NOW with user-confirmed save location
        # 사용자 확인 저장 위치로 초기 로깅 초기화
        if self.early_logger is None:
            self.early_logger, self.early_log_path = setup_early_logging(self.save_location)
            self.early_logger.info("=" * 60)
            self.early_logger.info("ECG ANALYSIS SYSTEM STARTED")
            self.early_logger.info("=" * 60)
            self.early_logger.info(f"User confirmed save location: {self.save_location}")
            self.early_logger.info(f"Early log file: {self.early_log_path}")
            self.early_logger.info("=" * 60)

        # Log the confirmation / 확인 로그 기록
        logger = logging.getLogger()
        logger.info("=" * 50)
        logger.info(f"Save location confirmed: {self.save_location}")
        logger.info("=" * 50)

        # Create config manager for common parameters with the confirmed location
        # 확인된 위치로 공통 파라미터 설정 관리자 생성
        self.common_config_manager = ConfigManager(
            config_filename="common_parameters.json",
            save_location=self.save_location
        )

        # Save location to common config
        # 공통 설정에 저장 위치 저장
        self.common_config_manager.update({'save_location': self.save_location})
        logger.info("Save location saved to configuration")

        # Show signal selection buttons directly after save location is confirmed
        # 저장 위치 확인 후 바로 신호 선택 버튼 표시
        self.show_signal_selection_buttons()

        logger.info("Signal selection buttons are now visible")

        # Show confirmation message / 확인 메시지 표시
        QMessageBox.information(
            self,
            "Save Location Set",
            f"Save location set to:\n{self.save_location}\n\n"
            f"Please select a signal type to analyze."
        )

    def show_signal_selection_buttons(self):
        """
        Display signal selection buttons after save location is confirmed.
        저장 위치 확인 후 신호 선택 버튼을 표시합니다.
        """
        logger = logging.getLogger()

        # Prevent duplicate creation if buttons already visible
        # 버튼이 이미 보이는 경우 중복 생성 방지
        if self.signal_buttons_visible:
            logger.info("Signal selection buttons already visible")
            return

        logger.info("Displaying signal selection buttons")

        # Get existing layout / 기존 레이아웃 가져오기
        container = self.centralWidget()
        layout = container.layout()

        # Find Exit button position (last HBoxLayout)
        # Exit 버튼 위치 찾기 (마지막 HBoxLayout)
        exit_layout_index = layout.count() - 1

        # Create signal selection guide label
        # 신호 선택 안내 레이블 생성
        self.signal_instruction_label = QLabel("Please select a signal to analyze:")
        self.signal_instruction_label.setStyleSheet("font-size: 16pt; color: #000000;")
        self.signal_instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.insertWidget(exit_layout_index, self.signal_instruction_label)

        # Signal type settings: (signal name, availability) tuple list
        # 신호 유형 설정: (신호 이름, 가용성) 튜플 리스트
        signals = [
            ("PPG", False),  # PPG (Photoplethysmography) - coming soon
            ("ECG", True),   # ECG (Electrocardiography) - currently available / 현재 사용 가능
            ("EMG", False),  # EMG (Electromyography) - coming soon
            ("EEG", False)   # EEG (Electroencephalography) - coming soon
        ]

        # Create grid layout for buttons
        # 버튼용 그리드 레이아웃 생성
        from PySide6.QtWidgets import QGridLayout
        button_grid = QGridLayout()
        button_grid.setSpacing(15)

        # Create signal selection buttons
        # 신호 선택 버튼 생성
        for i, (signal, available) in enumerate(signals):
            row = i % 2   # Arrange in 2 rows / 2행으로 배치
            col = i // 2  # Calculate column / 열 계산

            if available:
                # Available signal button / 사용 가능한 신호 버튼
                btn = QPushButton(signal)
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 18pt;
                        font-weight: bold;
                        min-width: 150px;
                        min-height: 80px;
                    }
                """)
                btn.clicked.connect(lambda _, s=signal: self.select_signal(s))
            else:
                # Unavailable signal button (Coming Soon)
                # 사용 불가능한 신호 버튼 (Coming Soon)
                btn = QPushButton(f"{signal}\n(Coming Soon)")
                btn.setEnabled(False)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #bdc3c7;
                        color: #7f8c8d;
                        font-size: 14pt;
                        min-width: 150px;
                        min-height: 80px;
                        border: 3px solid #95a5a6;
                        border-radius: 5px;
                    }
                """)

            button_grid.addWidget(btn, row, col)
            self.signal_buttons.append(btn)

        # Insert grid layout into main layout
        # 메인 레이아웃에 그리드 레이아웃 삽입
        layout.insertLayout(exit_layout_index + 1, button_grid)

        self.signal_buttons_visible = True
        logger.info(f"Created {len(self.signal_buttons)} signal selection buttons")

    def select_signal(self, signal_type):
        """
        Function called when user selects a signal type.
        사용자가 신호 유형을 선택할 때 호출되는 함수.
        """
        logger = logging.getLogger()
        logger.info(f"User selected signal type: {signal_type}")

        # Run appropriate GUI based on selected signal type
        # 선택된 신호 유형에 따라 적절한 GUI 실행
        if signal_type == "ECG":
            # Start ECG GUI workflow
            # ECG GUI 워크플로우 시작
            try:
                from ecg.ecg_gui import ecg_analysis_gui
                ecg_analysis_gui(
                    parent=self,
                    save_location=self.save_location,
                    early_log_path=self.early_log_path
                )
            except Exception as e:
                logger.error(f"Failed to start ECG GUI: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to start ECG GUI:\n\n{str(e)}"
                )
        elif signal_type == "PPG":
            QMessageBox.information(self, "Signal Selected", "PPG analysis coming soon")
        elif signal_type == "EMG":
            QMessageBox.information(self, "Signal Selected", "EMG analysis coming soon")
        elif signal_type == "EEG":
            QMessageBox.information(self, "Signal Selected", "EEG analysis coming soon")

    def close_application(self):
        """
        Application exit function.
        애플리케이션 종료 함수.
        """
        # Log application exit (if early logger is initialized)
        # 애플리케이션 종료 로그 (초기 로거가 초기화된 경우)
        if self.early_logger:
            logger = logging.getLogger()
            logger.info("=" * 50)
            logger.info("Application closing")
            logger.info("=" * 50)

        # Close all windows and exit application
        # 모든 윈도우를 닫고 애플리케이션 종료
        QApplication.quit()


# Program entry point / 프로그램 진입점
if __name__ == "__main__":
    # Create QApplication instance / QApplication 인스턴스 생성
    app = QApplication(sys.argv)

    # Create main window / 메인 윈도우 생성
    window = MainWindow()
    # Display main window / 메인 윈도우 표시
    window.show()

    # Run standard Qt event loop (no BLE, so qasync not needed)
    # 표준 Qt 이벤트 루프 실행 (BLE 없으므로 qasync 불필요)
    sys.exit(app.exec())
