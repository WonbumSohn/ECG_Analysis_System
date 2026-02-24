"""
ECG Preprocessing Dialogs and Processing Logic
ECG 전처리 다이얼로그 및 처리 로직

Provides:
- Method selection dialog (manual vs NeuroKit2)
  방법 선택 다이얼로그 (수동 vs NeuroKit2)
- Manual preprocessing dialog (BDI_GUI pattern)
  수동 전처리 다이얼로그 (BDI_GUI 패턴)
- NeuroKit2 preprocessing dialog
  NeuroKit2 전처리 다이얼로그
- Preprocessing execution function
  전처리 실행 함수
"""

import os
import json
import copy
import logging

import numpy as np

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QMessageBox,
)
from PySide6.QtCore import Qt

# NeuroKit2 optional dependency / NeuroKit2 선택적 의존성
try:
    import neurokit2 as nk
    NEUROKIT2_AVAILABLE = True
except ImportError:
    NEUROKIT2_AVAILABLE = False

# Preprocessing settings file path / 전처리 설정 파일 경로
ECG_PREPROCESS_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'config', 'ecg_preprocess_settings.json'
)

# Light mode stylesheet (shared across all dialogs)
# 라이트 모드 스타일시트 (모든 다이얼로그에서 공유)
LIGHT_MODE_STYLESHEET = """
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
    QGroupBox {
        background-color: #F0F0F0; color: #000000;
        border: 1px solid #CCCCCC; border-radius: 4px;
        margin-top: 10px; padding-top: 15px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin; left: 10px; padding: 0 5px;
    }
    QComboBox {
        background-color: #FFFFFF; color: #000000;
        border: 1px solid #CCCCCC; border-radius: 3px; padding: 3px;
    }
    QSpinBox, QDoubleSpinBox {
        background-color: #FFFFFF; color: #000000;
        border: 1px solid #CCCCCC; border-radius: 3px; padding: 3px;
    }
"""

# NeuroKit2 method descriptions / NeuroKit2 방법 설명
NEUROKIT2_METHOD_INFO = {
    "neurokit": "0.5 Hz highpass butterworth (order=5) + powerline filtering",
    "biosppy": "FIR bandpass filter [0.67-45] Hz, order = 1.5 x sampling_rate",
    "pantompkins": "Pan & Tompkins 1985 bandpass [5-15] Hz",
    "hamilton": "Hamilton 2002 bandpass [8-16] Hz",
    "elgendi": "Elgendi et al. 2010 bandpass [0.5-100] Hz",
    "engzeemod": "Engelse & Zeelenberg 1979 modified",
    "emrich": "4.0 Hz highpass butterworth (order=2)",
}


# =========================================================================
# Settings I/O Utility Functions / 설정 입출력 유틸리티 함수
# =========================================================================

def get_default_ecg_preprocess_settings() -> dict:
    """
    Return default ECG preprocessing settings.
    기본 ECG 전처리 설정 반환.

    Returns:
        dict: Default settings / 기본 설정
    """
    return {
        "last_method": "manual",
        "windowing": {
            "enabled": False,
            "window_size": 20.0,
            "window_step": 20.0,
        },
        "manual": {
            "moving_avg_enabled": False,
            "moving_avg_window": 4,
            "dc_removal_enabled": False,
            "dc_removal_method": "mean_subtraction",
            "dc_removal_window": 20,
            "dc_removal_step": 20,
            "butterworth_enabled": True,
            "butterworth_low": 0.5,
            "butterworth_high": 40.0,
            "butterworth_order": 5,
            "outlier_enabled": False,
            "outlier_method": "std",
            "outlier_multiplier": 3.0,
        },
        "neurokit2": {
            "method": "neurokit",
            "sampling_rate": None,
        },
    }


def load_ecg_preprocess_settings() -> dict | None:
    """
    Load ECG preprocessing settings from JSON file.
    JSON 파일에서 ECG 전처리 설정 로드.

    Returns:
        dict or None: Loaded settings, None if file missing or error
                      로드된 설정, 파일 없거나 오류 시 None
    """
    if os.path.exists(ECG_PREPROCESS_SETTINGS_FILE):
        try:
            with open(ECG_PREPROCESS_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Failed to load ECG preprocessing settings: {e}")
    return None


def save_ecg_preprocess_settings(settings: dict) -> None:
    """
    Save ECG preprocessing settings to JSON file.
    ECG 전처리 설정을 JSON 파일로 저장.

    Args:
        settings: Settings dictionary to save / 저장할 설정 딕셔너리
    """
    try:
        os.makedirs(os.path.dirname(ECG_PREPROCESS_SETTINGS_FILE), exist_ok=True)
        with open(ECG_PREPROCESS_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logging.error(f"Failed to save ECG preprocessing settings: {e}")


# =========================================================================
# ECGPreprocessingMethodDialog - 방법 선택 다이얼로그
# =========================================================================

class ECGPreprocessingMethodDialog(QDialog):
    """
    Dialog for selecting ECG preprocessing method.
    ECG 전처리 방법 선택 다이얼로그.

    Options:
    - "Manually Set": Open manual filter configuration dialog
      수동 필터 설정 다이얼로그 열기
    - "Use NeuroKit2": Open NeuroKit2 method selection dialog
      NeuroKit2 방법 선택 다이얼로그 열기

    Includes window-based processing option at the top.
    상단에 윈도우 기반 처리 옵션 포함.
    """

    def __init__(self, parent=None, current_windowing: dict | None = None):
        """
        Args:
            parent: Parent widget / 부모 위젯
            current_windowing: Current windowing settings dict
                               현재 윈도우 설정 딕셔너리
        """
        super().__init__(parent)
        self.selected_method = None  # "manual" or "neurokit2"

        # Load windowing settings: current > file > defaults
        # 윈도우 설정 로드: 현재 > 파일 > 기본값
        if current_windowing:
            self.windowing = copy.deepcopy(current_windowing)
        else:
            file_settings = load_ecg_preprocess_settings()
            if file_settings and "windowing" in file_settings:
                self.windowing = file_settings["windowing"]
            else:
                self.windowing = get_default_ecg_preprocess_settings()["windowing"]

        self._setup_ui()
        self._load_windowing_settings()

    def _setup_ui(self):
        """Setup the dialog UI / UI 구성"""
        self.setWindowTitle("Select ECG Preprocessing Method")
        self.setMinimumSize(420, 320)
        self.setStyleSheet(LIGHT_MODE_STYLESHEET)

        main_layout = QVBoxLayout()

        # === Title ===
        title = QLabel("Select ECG Preprocessing Method")
        title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        main_layout.addSpacing(10)

        # === Window-based Processing Group / 윈도우 기반 처리 그룹 ===
        window_group = QGroupBox("Window-based Processing")
        window_layout = QVBoxLayout()

        # Checkbox / 체크박스
        self.check_windowing = QCheckBox("Use Window-based Processing")
        window_layout.addWidget(self.check_windowing)

        # Window Size / 윈도우 크기
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("    Window Size (s):"))
        self.spin_window_size = QDoubleSpinBox()
        self.spin_window_size.setRange(1.0, 300.0)
        self.spin_window_size.setValue(20.0)
        self.spin_window_size.setSingleStep(1.0)
        self.spin_window_size.setDecimals(1)
        self.spin_window_size.setToolTip(
            "Window size in seconds"
        )
        size_layout.addWidget(self.spin_window_size)
        size_layout.addStretch()
        window_layout.addLayout(size_layout)

        # Window Step / 윈도우 간격
        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("    Window Step (s):"))
        self.spin_window_step = QDoubleSpinBox()
        self.spin_window_step.setRange(1.0, 300.0)
        self.spin_window_step.setValue(20.0)
        self.spin_window_step.setSingleStep(1.0)
        self.spin_window_step.setDecimals(1)
        self.spin_window_step.setToolTip(
            "Step between window starts (Step = Size → no overlap)"
        )
        step_layout.addWidget(self.spin_window_step)
        step_layout.addStretch()
        window_layout.addLayout(step_layout)

        # Hint label / 힌트 레이블
        hint = QLabel("    (Step = Size → no overlap)")
        hint.setStyleSheet("color: gray; font-style: italic; font-size: 9pt;")
        window_layout.addWidget(hint)

        window_group.setLayout(window_layout)
        main_layout.addWidget(window_group)

        # Enable/disable windowing inputs / 윈도우 입력 활성화/비활성화
        self.check_windowing.stateChanged.connect(self._on_windowing_toggled)
        self.spin_window_size.setEnabled(False)
        self.spin_window_step.setEnabled(False)

        main_layout.addSpacing(15)

        # === Method Selection Buttons / 방법 선택 버튼 ===
        self.btn_manual = QPushButton("Manually Set")
        self.btn_manual.setMinimumHeight(40)
        self.btn_manual.setStyleSheet(
            "QPushButton { font-size: 12pt; font-weight: bold; padding: 8px; }"
        )
        self.btn_manual.clicked.connect(self._on_manual_clicked)
        main_layout.addWidget(self.btn_manual)

        self.btn_neurokit2 = QPushButton("Use NeuroKit2")
        self.btn_neurokit2.setMinimumHeight(40)
        self.btn_neurokit2.setStyleSheet(
            "QPushButton { font-size: 12pt; font-weight: bold; padding: 8px; }"
        )
        self.btn_neurokit2.clicked.connect(self._on_neurokit2_clicked)
        if not NEUROKIT2_AVAILABLE:
            self.btn_neurokit2.setEnabled(False)
            self.btn_neurokit2.setToolTip(
                "neurokit2 package not installed.\n"
                "Run: pip install neurokit2"
            )
        main_layout.addWidget(self.btn_neurokit2)

        main_layout.addSpacing(10)

        # === Cancel Button ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumWidth(100)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def _on_windowing_toggled(self, state):
        """Toggle windowing input widgets / 윈도우 입력 위젯 토글"""
        enabled = state == Qt.CheckState.Checked.value
        self.spin_window_size.setEnabled(enabled)
        self.spin_window_step.setEnabled(enabled)

    def _load_windowing_settings(self):
        """Load windowing settings into UI / 윈도우 설정을 UI에 로드"""
        self.check_windowing.setChecked(self.windowing.get("enabled", False))
        self.spin_window_size.setValue(self.windowing.get("window_size", 20.0))
        self.spin_window_step.setValue(self.windowing.get("window_step", 20.0))
        # Trigger enable/disable
        self.spin_window_size.setEnabled(self.windowing.get("enabled", False))
        self.spin_window_step.setEnabled(self.windowing.get("enabled", False))

    def get_windowing_settings(self) -> dict:
        """
        Get windowing settings from UI.
        UI에서 윈도우 설정 가져오기.

        Returns:
            dict: Windowing settings / 윈도우 설정
        """
        return {
            "enabled": self.check_windowing.isChecked(),
            "window_size": self.spin_window_size.value(),
            "window_step": self.spin_window_step.value(),
        }

    def _on_manual_clicked(self):
        """Handle manual method selection / 수동 방법 선택 처리"""
        self.selected_method = "manual"
        self.accept()

    def _on_neurokit2_clicked(self):
        """Handle NeuroKit2 method selection / NeuroKit2 방법 선택 처리"""
        self.selected_method = "neurokit2"
        self.accept()


# =========================================================================
# ECGManualPreprocessingDialog - 수동 전처리 설정 다이얼로그
# =========================================================================

class ECGManualPreprocessingDialog(QDialog):
    """
    Dialog for configuring manual ECG preprocessing options.
    수동 ECG 전처리 옵션 설정 다이얼로그.

    Follows BDI_GUI PreprocessingDialog pattern (single channel).
    BDI_GUI PreprocessingDialog 패턴 준수 (단일 채널).
    """

    def __init__(self, parent=None, current_settings: dict | None = None):
        """
        Args:
            parent: Parent widget / 부모 위젯
            current_settings: Current manual preprocessing settings dict
                              현재 수동 전처리 설정 딕셔너리
        """
        super().__init__(parent)

        # Settings priority: current_settings > file > defaults
        # 우선순위: current_settings > 파일 > 기본값
        if current_settings:
            self.settings = copy.deepcopy(current_settings)
        else:
            file_settings = load_ecg_preprocess_settings()
            if file_settings and "manual" in file_settings:
                self.settings = file_settings["manual"]
            else:
                self.settings = get_default_ecg_preprocess_settings()["manual"]

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """Setup the dialog UI / UI 구성"""
        self.setWindowTitle("Manual ECG Preprocessing Options")
        self.setMinimumSize(500, 550)
        self.setStyleSheet(LIGHT_MODE_STYLESHEET)

        main_layout = QVBoxLayout()

        # Title
        title = QLabel("Configure Manual ECG Preprocessing Options")
        title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        main_layout.addSpacing(10)

        # === Filter options / 필터 옵션 ===
        self._create_filter_options(main_layout)

        main_layout.addStretch()

        # === OK / Cancel Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setMinimumWidth(100)
        button_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setMinimumWidth(100)
        button_layout.addWidget(btn_cancel)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _create_filter_options(self, layout):
        """
        Create all preprocessing option widgets.
        모든 전처리 옵션 위젯 생성.

        Args:
            layout: Parent layout / 부모 레이아웃
        """
        # 1. Moving Average Filter / 이동 평균 필터
        self.check_moving_avg = QCheckBox("Moving Average Filter")
        layout.addWidget(self.check_moving_avg)

        moving_avg_layout = QHBoxLayout()
        moving_avg_layout.addWidget(QLabel("    Window:"))
        self.spin_moving_avg = QSpinBox()
        self.spin_moving_avg.setRange(2, 100)
        self.spin_moving_avg.setValue(4)
        self.spin_moving_avg.setToolTip("Window size for moving average (default: 4)")
        moving_avg_layout.addWidget(self.spin_moving_avg)
        moving_avg_layout.addStretch()
        layout.addLayout(moving_avg_layout)

        self.check_moving_avg.stateChanged.connect(
            lambda state: self.spin_moving_avg.setEnabled(
                state == Qt.CheckState.Checked.value
            )
        )
        self.spin_moving_avg.setEnabled(False)

        layout.addSpacing(10)

        # 2. DC Removal / DC 제거
        self.check_dc = QCheckBox("DC Removal")
        layout.addWidget(self.check_dc)

        dc_method_layout = QHBoxLayout()
        dc_method_layout.addWidget(QLabel("    Method:"))
        self.combo_dc_method = QComboBox()
        self.combo_dc_method.addItem("Mean Subtraction", "mean_subtraction")
        self.combo_dc_method.addItem("Moving Window", "moving_average")
        dc_method_layout.addWidget(self.combo_dc_method)
        dc_method_layout.addStretch()
        layout.addLayout(dc_method_layout)

        dc_window_layout = QHBoxLayout()
        dc_window_layout.addWidget(QLabel("    Window:"))
        self.spin_dc_window = QSpinBox()
        self.spin_dc_window.setRange(1, 1000)
        self.spin_dc_window.setValue(20)
        dc_window_layout.addWidget(self.spin_dc_window)
        dc_window_layout.addStretch()
        layout.addLayout(dc_window_layout)

        dc_step_layout = QHBoxLayout()
        dc_step_layout.addWidget(QLabel("    Step:"))
        self.spin_dc_step = QSpinBox()
        self.spin_dc_step.setRange(1, 1000)
        self.spin_dc_step.setValue(20)
        self.spin_dc_step.setToolTip("Set equal to Window for no overlap")
        dc_step_layout.addWidget(self.spin_dc_step)
        dc_step_layout.addStretch()
        layout.addLayout(dc_step_layout)

        dc_hint = QLabel("    (Set equal to Window for no overlap)")
        dc_hint.setStyleSheet("color: gray; font-style: italic; font-size: 9pt;")
        layout.addWidget(dc_hint)

        def _on_dc_toggle(state):
            enabled = state == Qt.CheckState.Checked.value
            self.combo_dc_method.setEnabled(enabled)
            self.spin_dc_window.setEnabled(enabled)
            self.spin_dc_step.setEnabled(enabled)

        self.check_dc.stateChanged.connect(_on_dc_toggle)
        self.combo_dc_method.setEnabled(False)
        self.spin_dc_window.setEnabled(False)
        self.spin_dc_step.setEnabled(False)

        layout.addSpacing(10)

        # 3. Butterworth Bandpass Filter / 버터워스 대역통과 필터
        self.check_butter = QCheckBox("Butterworth Bandpass Filter")
        layout.addWidget(self.check_butter)

        butter_low_layout = QHBoxLayout()
        butter_low_layout.addWidget(QLabel("    Low Cutoff (Hz):"))
        self.spin_butter_low = QDoubleSpinBox()
        self.spin_butter_low.setRange(0.1, 10.0)
        self.spin_butter_low.setValue(0.5)
        self.spin_butter_low.setSingleStep(0.1)
        self.spin_butter_low.setDecimals(1)
        butter_low_layout.addWidget(self.spin_butter_low)
        butter_low_layout.addStretch()
        layout.addLayout(butter_low_layout)

        butter_high_layout = QHBoxLayout()
        butter_high_layout.addWidget(QLabel("    High Cutoff (Hz):"))
        self.spin_butter_high = QDoubleSpinBox()
        self.spin_butter_high.setRange(1.0, 100.0)
        self.spin_butter_high.setValue(40.0)
        self.spin_butter_high.setSingleStep(0.5)
        self.spin_butter_high.setDecimals(1)
        butter_high_layout.addWidget(self.spin_butter_high)
        butter_high_layout.addStretch()
        layout.addLayout(butter_high_layout)

        butter_order_layout = QHBoxLayout()
        butter_order_layout.addWidget(QLabel("    Order:"))
        self.spin_butter_order = QSpinBox()
        self.spin_butter_order.setRange(1, 10)
        self.spin_butter_order.setValue(5)
        butter_order_layout.addWidget(self.spin_butter_order)
        butter_order_layout.addStretch()
        layout.addLayout(butter_order_layout)

        def _on_butter_toggle(state):
            enabled = state == Qt.CheckState.Checked.value
            self.spin_butter_low.setEnabled(enabled)
            self.spin_butter_high.setEnabled(enabled)
            self.spin_butter_order.setEnabled(enabled)

        self.check_butter.stateChanged.connect(_on_butter_toggle)
        self.spin_butter_low.setEnabled(False)
        self.spin_butter_high.setEnabled(False)
        self.spin_butter_order.setEnabled(False)

        layout.addSpacing(10)

        # 4. Outlier Removal / 이상치 제거
        self.check_outlier = QCheckBox("Outlier Removal")
        layout.addWidget(self.check_outlier)

        outlier_method_layout = QHBoxLayout()
        outlier_method_layout.addWidget(QLabel("    Method:"))
        self.combo_outlier_method = QComboBox()
        self.combo_outlier_method.addItem("Std-based", "std")
        self.combo_outlier_method.addItem("Median/MAD-based", "median_mad")
        outlier_method_layout.addWidget(self.combo_outlier_method)
        outlier_method_layout.addStretch()
        layout.addLayout(outlier_method_layout)

        outlier_mult_layout = QHBoxLayout()
        outlier_mult_layout.addWidget(QLabel("    Multiplier:"))
        self.spin_outlier_mult = QDoubleSpinBox()
        self.spin_outlier_mult.setRange(0.5, 10.0)
        self.spin_outlier_mult.setValue(3.0)
        self.spin_outlier_mult.setSingleStep(0.5)
        self.spin_outlier_mult.setDecimals(1)
        outlier_mult_layout.addWidget(self.spin_outlier_mult)
        outlier_mult_layout.addStretch()
        layout.addLayout(outlier_mult_layout)

        def _on_outlier_toggle(state):
            enabled = state == Qt.CheckState.Checked.value
            self.combo_outlier_method.setEnabled(enabled)
            self.spin_outlier_mult.setEnabled(enabled)

        self.check_outlier.stateChanged.connect(_on_outlier_toggle)
        self.combo_outlier_method.setEnabled(False)
        self.spin_outlier_mult.setEnabled(False)

    def _load_current_settings(self):
        """Load current settings into UI widgets / 현재 설정을 UI 위젯에 로드"""
        s = self.settings

        # Moving Average
        self.check_moving_avg.setChecked(s.get('moving_avg_enabled', False))
        self.spin_moving_avg.setValue(s.get('moving_avg_window', 4))
        self.spin_moving_avg.setEnabled(s.get('moving_avg_enabled', False))

        # DC Removal
        self.check_dc.setChecked(s.get('dc_removal_enabled', False))
        idx = self.combo_dc_method.findData(s.get('dc_removal_method', 'mean_subtraction'))
        if idx >= 0:
            self.combo_dc_method.setCurrentIndex(idx)
        self.combo_dc_method.setEnabled(s.get('dc_removal_enabled', False))
        self.spin_dc_window.setValue(s.get('dc_removal_window', 20))
        self.spin_dc_window.setEnabled(s.get('dc_removal_enabled', False))
        self.spin_dc_step.setValue(s.get('dc_removal_step', 20))
        self.spin_dc_step.setEnabled(s.get('dc_removal_enabled', False))

        # Butterworth
        self.check_butter.setChecked(s.get('butterworth_enabled', True))
        self.spin_butter_low.setValue(s.get('butterworth_low', 0.5))
        self.spin_butter_low.setEnabled(s.get('butterworth_enabled', True))
        self.spin_butter_high.setValue(s.get('butterworth_high', 40.0))
        self.spin_butter_high.setEnabled(s.get('butterworth_enabled', True))
        self.spin_butter_order.setValue(s.get('butterworth_order', 5))
        self.spin_butter_order.setEnabled(s.get('butterworth_enabled', True))

        # Outlier Removal
        self.check_outlier.setChecked(s.get('outlier_enabled', False))
        idx = self.combo_outlier_method.findData(s.get('outlier_method', 'std'))
        if idx >= 0:
            self.combo_outlier_method.setCurrentIndex(idx)
        self.combo_outlier_method.setEnabled(s.get('outlier_enabled', False))
        self.spin_outlier_mult.setValue(s.get('outlier_multiplier', 3.0))
        self.spin_outlier_mult.setEnabled(s.get('outlier_enabled', False))

    def get_settings(self) -> dict:
        """
        Get manual settings from UI widgets.
        UI 위젯에서 수동 설정 가져오기.

        Returns:
            dict: Manual preprocessing settings / 수동 전처리 설정
        """
        return {
            'moving_avg_enabled': self.check_moving_avg.isChecked(),
            'moving_avg_window': self.spin_moving_avg.value(),
            'dc_removal_enabled': self.check_dc.isChecked(),
            'dc_removal_method': self.combo_dc_method.currentData(),
            'dc_removal_window': self.spin_dc_window.value(),
            'dc_removal_step': self.spin_dc_step.value(),
            'butterworth_enabled': self.check_butter.isChecked(),
            'butterworth_low': self.spin_butter_low.value(),
            'butterworth_high': self.spin_butter_high.value(),
            'butterworth_order': self.spin_butter_order.value(),
            'outlier_enabled': self.check_outlier.isChecked(),
            'outlier_method': self.combo_outlier_method.currentData(),
            'outlier_multiplier': self.spin_outlier_mult.value(),
        }

    def accept(self):
        """Save settings to file when OK clicked / OK 클릭 시 설정 파일에 저장"""
        settings = self.get_settings()
        full_config = load_ecg_preprocess_settings() or get_default_ecg_preprocess_settings()
        full_config["manual"] = settings
        full_config["last_method"] = "manual"
        save_ecg_preprocess_settings(full_config)
        super().accept()


# =========================================================================
# ECGNeuroKit2PreprocessingDialog - NeuroKit2 전처리 설정 다이얼로그
# =========================================================================

class ECGNeuroKit2PreprocessingDialog(QDialog):
    """
    Dialog for configuring NeuroKit2 ecg_clean() parameters.
    NeuroKit2 ecg_clean() 파라미터 설정 다이얼로그.
    """

    def __init__(self, parent=None, current_settings: dict | None = None,
                 sampling_rate: float | None = None):
        """
        Args:
            parent: Parent widget / 부모 위젯
            current_settings: Current neurokit2 settings dict / 현재 neurokit2 설정
            sampling_rate: Sampling rate from loaded data / 로드된 데이터의 샘플링 레이트
        """
        super().__init__(parent)
        self.data_sampling_rate = sampling_rate

        # Settings priority: current_settings > file > defaults
        # 우선순위: current_settings > 파일 > 기본값
        if current_settings:
            self.settings = copy.deepcopy(current_settings)
        else:
            file_settings = load_ecg_preprocess_settings()
            if file_settings and "neurokit2" in file_settings:
                self.settings = file_settings["neurokit2"]
            else:
                self.settings = get_default_ecg_preprocess_settings()["neurokit2"]

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """Setup the dialog UI / UI 구성"""
        self.setWindowTitle("NeuroKit2 ECG Preprocessing")
        self.setMinimumSize(450, 350)
        self.setStyleSheet(LIGHT_MODE_STYLESHEET)

        main_layout = QVBoxLayout()

        # Title
        title = QLabel("NeuroKit2 ECG Preprocessing")
        title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        main_layout.addSpacing(15)

        # === Method selection / 방법 선택 ===
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))
        self.combo_method = QComboBox()
        for method_name in NEUROKIT2_METHOD_INFO:
            self.combo_method.addItem(method_name, method_name)
        method_layout.addWidget(self.combo_method)
        method_layout.addStretch()
        main_layout.addLayout(method_layout)

        main_layout.addSpacing(5)

        # Method info label / 방법 정보 레이블
        info_header = QLabel("Method Info:")
        info_header.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(info_header)

        self.label_method_info = QLabel("")
        self.label_method_info.setWordWrap(True)
        self.label_method_info.setStyleSheet(
            "border: 1px solid #CCCCCC; border-radius: 4px; "
            "padding: 8px; background-color: #FFFFFF; min-height: 40px;"
        )
        main_layout.addWidget(self.label_method_info)

        self.combo_method.currentIndexChanged.connect(self._on_method_changed)

        main_layout.addSpacing(15)

        # === Sampling Rate / 샘플링 레이트 ===
        sr_layout = QHBoxLayout()
        sr_layout.addWidget(QLabel("Sampling Rate (Hz):"))
        self.spin_sampling_rate = QDoubleSpinBox()
        self.spin_sampling_rate.setRange(1.0, 10000.0)
        self.spin_sampling_rate.setSingleStep(1.0)
        self.spin_sampling_rate.setDecimals(1)
        sr_layout.addWidget(self.spin_sampling_rate)
        sr_layout.addStretch()
        main_layout.addLayout(sr_layout)

        # Auto-detected hint / 자동 감지 힌트
        if self.data_sampling_rate is not None:
            sr_hint = QLabel(f"    (auto-detected from data: {self.data_sampling_rate:.1f} Hz)")
            sr_hint.setStyleSheet("color: gray; font-style: italic; font-size: 9pt;")
            main_layout.addWidget(sr_hint)

        main_layout.addStretch()

        # === OK / Cancel Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setMinimumWidth(100)
        button_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setMinimumWidth(100)
        button_layout.addWidget(btn_cancel)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _on_method_changed(self, _index: int):
        """
        Update method info label when method selection changes.
        방법 선택 변경 시 방법 정보 레이블 업데이트.
        """
        method = self.combo_method.currentData()
        info_text = NEUROKIT2_METHOD_INFO.get(method, "")
        self.label_method_info.setText(info_text)

    def _load_current_settings(self):
        """Load current settings into UI / 현재 설정을 UI에 로드"""
        # Method
        method = self.settings.get("method", "neurokit")
        idx = self.combo_method.findData(method)
        if idx >= 0:
            self.combo_method.setCurrentIndex(idx)
        self._on_method_changed(0)  # Update info label

        # Sampling Rate: prefer data SR > saved SR > default 1000
        # 샘플링 레이트: 데이터 SR > 저장된 SR > 기본값 1000
        sr = self.data_sampling_rate
        if sr is None:
            sr = self.settings.get("sampling_rate")
        if sr is None:
            sr = 1000.0
        self.spin_sampling_rate.setValue(sr)

    def get_settings(self) -> dict:
        """
        Get NeuroKit2 settings from UI widgets.
        UI 위젯에서 NeuroKit2 설정 가져오기.

        Returns:
            dict: NeuroKit2 settings / NeuroKit2 설정
        """
        return {
            "method": self.combo_method.currentData(),
            "sampling_rate": self.spin_sampling_rate.value(),
        }

    def accept(self):
        """Save settings to file when OK clicked / OK 클릭 시 설정 저장"""
        settings = self.get_settings()
        full_config = load_ecg_preprocess_settings() or get_default_ecg_preprocess_settings()
        full_config["neurokit2"] = settings
        full_config["last_method"] = "neurokit2"
        save_ecg_preprocess_settings(full_config)
        super().accept()


# =========================================================================
# Preprocessing Execution / 전처리 실행
# =========================================================================

def apply_ecg_preprocessing(
    ecg_signal: np.ndarray,
    method: str,
    manual_settings: dict | None = None,
    neurokit2_settings: dict | None = None,
    sampling_rate: float | None = None,
    windowing: dict | None = None,
    logger: logging.Logger | None = None,
) -> np.ndarray:
    """
    Apply preprocessing to raw ECG signal.
    원본 ECG 신호에 전처리 적용.

    Args:
        ecg_signal: Raw ECG signal array / 원본 ECG 신호 배열
        method: "manual" or "neurokit2" / "manual" 또는 "neurokit2"
        manual_settings: Manual preprocessing settings (required if method="manual")
                         수동 전처리 설정 (method="manual" 시 필수)
        neurokit2_settings: NeuroKit2 settings (required if method="neurokit2")
                            NeuroKit2 설정 (method="neurokit2" 시 필수)
        sampling_rate: Sampling rate in Hz / Hz 단위 샘플링 레이트
        windowing: Windowing settings dict / 윈도우 설정 딕셔너리
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Preprocessed ECG signal / 전처리된 ECG 신호

    Raises:
        ValueError: If required settings are missing / 필수 설정 누락 시
    """
    log = logger or logging.getLogger(__name__)

    if windowing and windowing.get("enabled") and sampling_rate:
        log.info("Applying windowed preprocessing")
        return _apply_windowed_preprocessing(
            ecg_signal, method, manual_settings, neurokit2_settings,
            sampling_rate, windowing, log,
        )
    else:
        log.info("Applying global preprocessing")
        return _apply_single_preprocessing(
            ecg_signal, method, manual_settings, neurokit2_settings,
            sampling_rate, log,
        )


def _apply_windowed_preprocessing(
    signal: np.ndarray,
    method: str,
    manual_settings: dict | None,
    neurokit2_settings: dict | None,
    sampling_rate: float,
    windowing: dict,
    logger: logging.Logger,
) -> np.ndarray:
    """
    Apply preprocessing in sliding windows.
    슬라이딩 윈도우로 전처리 적용.

    Args:
        signal: Raw ECG signal / 원본 ECG 신호
        method: "manual" or "neurokit2"
        manual_settings: Manual preprocessing settings / 수동 전처리 설정
        neurokit2_settings: NeuroKit2 settings / NeuroKit2 설정
        sampling_rate: Sampling rate in Hz / Hz 단위 샘플링 레이트
        windowing: Windowing settings / 윈도우 설정
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Preprocessed signal / 전처리된 신호
    """
    window_size = windowing["window_size"]
    window_step = windowing["window_step"]

    window_samples = int(window_size * sampling_rate)
    step_samples = int(window_step * sampling_rate)

    if window_samples <= 0 or step_samples <= 0:
        raise ValueError(
            f"Invalid window parameters: size={window_size}s, step={window_step}s, "
            f"sr={sampling_rate}Hz"
        )

    data_length = len(signal)
    result = np.zeros(data_length, dtype=float)

    window_count = 0
    start_idx = 0

    while start_idx < data_length:
        end_idx = min(start_idx + window_samples, data_length)
        window_data = signal[start_idx:end_idx].copy()

        # Skip if window too small (< 10 samples)
        # 윈도우가 너무 작으면 스킵 (10 샘플 미만)
        if len(window_data) < 10:
            logger.warning(
                f"  Window {window_count}: too small ({len(window_data)} samples), skipping"
            )
            start_idx += step_samples
            window_count += 1
            continue

        # Apply preprocessing to this window
        # 이 윈도우에 전처리 적용
        processed = _apply_single_preprocessing(
            window_data, method, manual_settings, neurokit2_settings,
            sampling_rate, logger,
        )

        # Write processed window to result
        # 처리된 윈도우를 결과에 기록
        result[start_idx:end_idx] = processed

        window_count += 1
        start_idx += step_samples

    logger.info(
        f"Windowed preprocessing completed: {window_count} windows "
        f"(size={window_size}s, step={window_step}s)"
    )

    return result


def _apply_single_preprocessing(
    signal: np.ndarray,
    method: str,
    manual_settings: dict | None,
    neurokit2_settings: dict | None,
    sampling_rate: float | None,
    logger: logging.Logger,
) -> np.ndarray:
    """
    Apply preprocessing to a single signal segment.
    단일 신호 세그먼트에 전처리 적용.

    Args:
        signal: ECG signal array / ECG 신호 배열
        method: "manual" or "neurokit2"
        manual_settings: Manual settings / 수동 설정
        neurokit2_settings: NeuroKit2 settings / NeuroKit2 설정
        sampling_rate: Sampling rate / 샘플링 레이트
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Preprocessed signal / 전처리된 신호
    """
    if method == "manual":
        if manual_settings is None:
            raise ValueError("manual_settings is required for method='manual'")
        return _apply_manual_preprocessing(signal, manual_settings, sampling_rate, logger)
    elif method == "neurokit2":
        if neurokit2_settings is None:
            raise ValueError("neurokit2_settings is required for method='neurokit2'")
        return _apply_neurokit2_preprocessing(signal, neurokit2_settings, logger)
    else:
        raise ValueError(f"Unknown preprocessing method: {method}")


def _apply_manual_preprocessing(
    signal: np.ndarray,
    settings: dict,
    sampling_rate: float | None,
    logger: logging.Logger,
) -> np.ndarray:
    """
    Apply manual preprocessing steps to ECG signal.
    ECG 신호에 수동 전처리 단계 적용.

    Processing order / 처리 순서:
    1. Moving Average (uniform_filter1d)
    2. DC Removal (mean_subtraction or moving_average)
    3. Butterworth Bandpass (scipy.signal.butter + filtfilt)
    4. Outlier Removal (std or median_mad based)

    Args:
        signal: ECG signal array / ECG 신호 배열
        settings: Manual preprocessing settings / 수동 전처리 설정
        sampling_rate: Sampling rate in Hz / Hz 단위 샘플링 레이트
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Preprocessed signal / 전처리된 신호
    """
    from scipy.ndimage import uniform_filter1d
    from scipy.signal import butter, filtfilt

    result = signal.copy()

    # 1. Moving Average Filter / 이동 평균 필터
    if settings.get('moving_avg_enabled', False):
        window = settings['moving_avg_window']
        if len(result) >= window:
            result = uniform_filter1d(result, size=window, mode='nearest')
            logger.info(f"  Applied moving average filter (window={window})")

    # 2. DC Removal / DC 제거
    if settings.get('dc_removal_enabled', False):
        method = settings['dc_removal_method']
        if method == 'mean_subtraction':
            result = result - np.mean(result)
            logger.info("  Applied DC removal (mean subtraction)")
        elif method == 'moving_average':
            window = settings['dc_removal_window']
            dc_component = uniform_filter1d(result, size=window, mode='nearest')
            result = result - dc_component
            logger.info(
                f"  Applied DC removal (moving average, window={window})"
            )

    # 3. Butterworth Bandpass Filter / 버터워스 대역통과 필터
    if settings.get('butterworth_enabled', False):
        if sampling_rate is None:
            logger.warning("  Butterworth filter skipped: sampling rate unknown")
        else:
            low = settings['butterworth_low']
            high = settings['butterworth_high']
            order = settings['butterworth_order']
            nyq = sampling_rate / 2

            low_norm = low / nyq
            high_norm = high / nyq

            if 0 < low_norm < high_norm < 1:
                # Check minimum signal length for filter
                # 필터에 필요한 최소 신호 길이 확인
                min_length = 3 * max(order, 1) + 1
                if len(result) >= min_length:
                    try:
                        b, a = butter(order, [low_norm, high_norm], btype='band')
                        result = filtfilt(b, a, result)
                        logger.info(
                            f"  Applied Butterworth filter "
                            f"(low={low}Hz, high={high}Hz, order={order})"
                        )
                    except Exception as e:
                        logger.warning(f"  Butterworth filter failed: {e}")
                else:
                    logger.warning(
                        f"  Butterworth filter skipped: signal too short "
                        f"({len(result)} < {min_length})"
                    )
            else:
                logger.warning(
                    f"  Invalid Butterworth filter range: "
                    f"low={low}, high={high}, sr={sampling_rate}"
                )

    # 4. Outlier Removal / 이상치 제거
    if settings.get('outlier_enabled', False):
        result = result.astype(float)
        method = settings['outlier_method']
        mult = settings['outlier_multiplier']
        outlier_mask = np.zeros(len(result), dtype=bool)

        if method == 'std':
            mean_val = np.mean(result)
            std_val = np.std(result)
            if std_val > 0:
                outlier_mask = np.abs(result - mean_val) > mult * std_val
        elif method == 'median_mad':
            median_val = np.median(result)
            mad = np.median(np.abs(result - median_val))
            if mad > 0:
                outlier_mask = np.abs(result - median_val) > mult * mad * 1.4826

        if np.any(outlier_mask):
            result[outlier_mask] = np.nan
            valid_indices = ~np.isnan(result)
            if np.any(valid_indices):
                result = np.interp(
                    np.arange(len(result)),
                    np.arange(len(result))[valid_indices],
                    result[valid_indices],
                )
            logger.info(
                f"  Applied outlier removal "
                f"({method}, mult={mult}, removed {np.sum(outlier_mask)} points)"
            )

    return result


def _apply_neurokit2_preprocessing(
    signal: np.ndarray,
    settings: dict,
    logger: logging.Logger,
) -> np.ndarray:
    """
    Apply NeuroKit2 ecg_clean() to ECG signal.
    NeuroKit2 ecg_clean()으로 ECG 신호 전처리.

    Args:
        signal: Raw ECG signal / 원본 ECG 신호
        settings: {"method": str, "sampling_rate": float}
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Cleaned ECG signal / 정제된 ECG 신호
    """
    if not NEUROKIT2_AVAILABLE:
        raise ImportError(
            "neurokit2 is not installed. Run: pip install neurokit2"
        )

    method = settings.get("method", "neurokit")
    sr = settings.get("sampling_rate", 1000)

    logger.info(f"  Applying NeuroKit2 ecg_clean (method={method}, sr={sr})")

    cleaned = nk.ecg_clean(signal, sampling_rate=int(sr), method=method)

    logger.info("  NeuroKit2 preprocessing completed")

    return np.array(cleaned)
