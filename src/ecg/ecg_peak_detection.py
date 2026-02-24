"""
ECG R-Peak Detection Dialog and Processing Logic
ECG R-피크 검출 다이얼로그 및 처리 로직

Provides:
- R-Peak detection settings dialog (SciPy + NeuroKit2 methods)
  R-피크 검출 설정 다이얼로그 (SciPy + NeuroKit2 방법)
- R-Peak detection execution (total / windowed)
  R-피크 검출 실행 (전체 / 윈도우)
- Peak detection settings config helpers
  피크 검출 설정 config 헬퍼
"""

import logging

import numpy as np
from scipy.signal import find_peaks

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox,
)
from PySide6.QtCore import Qt

# NeuroKit2 optional dependency / NeuroKit2 선택적 의존성
try:
    import neurokit2 as nk
    NEUROKIT2_AVAILABLE = True
except ImportError:
    NEUROKIT2_AVAILABLE = False

# Reuse shared resources from preprocessing module
# 전처리 모듈의 공유 리소스 재사용
from ecg.ecg_preprocessing import (
    LIGHT_MODE_STYLESHEET,
    load_ecg_preprocess_settings,
    save_ecg_preprocess_settings,
    get_default_ecg_preprocess_settings,
)


# Top-level detection method descriptions
# 최상위 검출 방법 설명
ECG_DETECTION_METHOD_INFO = {
    "scipy_prominence": "Detect peaks using signal prominence (std multiplier). Flexible for any species.",
    "scipy_height": "Detect peaks using height threshold and minimum distance. Flexible for any species.",
    "neurokit2": "NeuroKit2 library ECG algorithms. Designed for human ECG (60-200 BPM).",
}

# NeuroKit2 ECG R-peak detection sub-method descriptions
# NeuroKit2 ECG R-피크 검출 하위 방법 설명
ECG_PEAK_METHOD_INFO = {
    "neurokit": "QRS detection based on steepness of absolute gradient (default)",
    "pantompkins1985": "Pan & Tompkins 1985 - bandpass + derivative + squaring + moving window integration",
    "hamilton2002": "Hamilton 2002 - adaptive thresholding",
    "christov2004": "Christov 2004 - adaptive thresholds with combined features",
    "elgendi2010": "Elgendi et al. 2010 - two moving averages based",
    "engzeemod2012": "Engelse & Zeelenberg 1979 modified by Lourenco et al. 2012",
    "manikandan2012": "Manikandan & Soman 2012 - Shannon energy envelope",
    "kalidas2017": "Kalidas et al. 2017 - adaptive threshold with PanTompkins base",
    "nabian2018": "Nabian et al. 2018 - Pan-Tompkins based adaptation",
    "rodrigues2021": "Rodrigues et al. 2021 - adaptation of Sadhukhan & Mitra 2012",
    "emrich2023": "Emrich et al. 2023 - FastNVG based on visibility graph",
    "promac": "ProMAC - probabilistic combination of multiple detectors",
}


# =========================================================================
# Settings I/O Helpers / 설정 입출력 헬퍼
# =========================================================================

def get_default_peak_detection_settings() -> dict:
    """
    Return default ECG peak detection settings.
    기본 ECG 피크 검출 설정 반환.

    Returns:
        dict: Default settings / 기본 설정
    """
    return {
        "method": "scipy_prominence",
        "sub_method": "neurokit",
        "detection_range": "total",
        "window_size": 20.0,
        "window_step": 20.0,
        "prominence_multiplier": 0.5,
        "height_ratio": 0.3,
        "height_distance": 20,
    }


def load_peak_detection_settings() -> dict:
    """
    Load peak detection settings from the shared config file.
    공유 config 파일에서 피크 검출 설정 로드.

    Returns:
        dict: Peak detection settings / 피크 검출 설정
    """
    full_config = load_ecg_preprocess_settings()
    if full_config and "peak_detection" in full_config:
        saved = full_config["peak_detection"]
        # Merge with defaults to ensure all keys exist
        # 모든 키가 존재하도록 defaults와 병합
        defaults = get_default_peak_detection_settings()
        defaults.update(saved)
        return defaults
    return get_default_peak_detection_settings()


def save_peak_detection_settings(settings: dict) -> None:
    """
    Save peak detection settings to the shared config file.
    공유 config 파일에 피크 검출 설정 저장.

    Args:
        settings: Peak detection settings dict / 피크 검출 설정
    """
    full_config = load_ecg_preprocess_settings() or get_default_ecg_preprocess_settings()
    full_config["peak_detection"] = settings
    save_ecg_preprocess_settings(full_config)


# =========================================================================
# Peak Detection Settings Dialog / 피크 검출 설정 다이얼로그
# =========================================================================

class ECGPeakDetectionSettingsDialog(QDialog):
    """
    Dialog for configuring R-peak detection settings.
    R-피크 검출 설정을 구성하기 위한 다이얼로그.

    Supports SciPy (Prominence, Height) and NeuroKit2 detection methods.
    SciPy (Prominence, Height) 및 NeuroKit2 검출 방법 지원.
    """

    def __init__(self, parent=None, current_settings: dict | None = None):
        """
        Initialize peak detection settings dialog.
        피크 검출 설정 다이얼로그 초기화.

        Args:
            parent: Parent widget / 부모 위젯
            current_settings: Current settings (overrides config file if given)
                              현재 설정 (주어지면 config 파일 대신 사용)
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)

        # Load settings: current_settings > config file > defaults
        # 설정 로드: current_settings > config 파일 > defaults
        if current_settings:
            self.settings = current_settings.copy()
        else:
            self.settings = load_peak_detection_settings()

        self._setup_ui()

    def _setup_ui(self):
        """
        Build the dialog UI.
        다이얼로그 UI 구성.
        """
        self.setWindowTitle("R-Peak Detection Settings")
        self.setMinimumWidth(480)
        self.setStyleSheet(LIGHT_MODE_STYLESHEET)

        main_layout = QVBoxLayout()

        # === Title / 타이틀 ===
        title = QLabel("R-Peak Detection Settings")
        title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 8px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # === Peak Detection Method GroupBox ===
        method_group = QGroupBox("Peak Detection Method")
        method_layout = QVBoxLayout()

        # Detection Method dropdown / 검출 방법 드롭다운
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Detection Method:"))
        self.combo_method = QComboBox()
        self.combo_method.addItem("SciPy - Prominence", "scipy_prominence")
        self.combo_method.addItem("SciPy - Height", "scipy_height")
        self.combo_method.addItem("NeuroKit2", "neurokit2")
        method_row.addWidget(self.combo_method)
        method_layout.addLayout(method_row)

        # Method description label / 방법 설명 라벨
        self.label_method_desc = QLabel("")
        self.label_method_desc.setWordWrap(True)
        self.label_method_desc.setStyleSheet(
            "color: #555555; font-style: italic; margin-left: 10px; padding: 4px;"
        )
        method_layout.addWidget(self.label_method_desc)

        # --- SciPy - Prominence parameters / SciPy - Prominence 파라미터 ---
        self.group_scipy_prominence = QGroupBox("SciPy - Prominence Parameters")
        prominence_layout = QVBoxLayout()

        prominence_row = QHBoxLayout()
        prominence_row.addWidget(QLabel("Prominence Multiplier (x std):"))
        self.spin_prominence = QDoubleSpinBox()
        self.spin_prominence.setRange(0.1, 5.0)
        self.spin_prominence.setSingleStep(0.1)
        self.spin_prominence.setDecimals(2)
        self.spin_prominence.setToolTip(
            "Multiplier for signal std to set prominence threshold"
        )
        prominence_row.addWidget(self.spin_prominence)
        prominence_layout.addLayout(prominence_row)

        prominence_hint = QLabel(
            "prominence = std(signal) x multiplier\n"
            "Higher value → fewer peaks (stricter)"
        )
        prominence_hint.setStyleSheet("color: #888888; font-size: 11px;")
        prominence_layout.addWidget(prominence_hint)

        self.group_scipy_prominence.setLayout(prominence_layout)
        method_layout.addWidget(self.group_scipy_prominence)

        # --- SciPy - Height parameters / SciPy - Height 파라미터 ---
        self.group_scipy_height = QGroupBox("SciPy - Height Parameters")
        height_layout = QVBoxLayout()

        height_ratio_row = QHBoxLayout()
        height_ratio_row.addWidget(QLabel("Height Threshold Ratio:"))
        self.spin_height_ratio = QDoubleSpinBox()
        self.spin_height_ratio.setRange(0.05, 0.95)
        self.spin_height_ratio.setSingleStep(0.05)
        self.spin_height_ratio.setDecimals(2)
        self.spin_height_ratio.setToolTip(
            "Height threshold = min + (max - min) x ratio"
        )
        height_ratio_row.addWidget(self.spin_height_ratio)
        height_layout.addLayout(height_ratio_row)

        height_dist_row = QHBoxLayout()
        height_dist_row.addWidget(QLabel("Min Peak Distance (samples):"))
        self.spin_height_distance = QSpinBox()
        self.spin_height_distance.setRange(1, 1000)
        self.spin_height_distance.setToolTip(
            "Minimum distance between adjacent peaks in samples"
        )
        height_dist_row.addWidget(self.spin_height_distance)
        height_layout.addLayout(height_dist_row)

        height_hint = QLabel(
            "height = min + (max - min) x ratio\n"
            "Higher ratio → fewer peaks (stricter)"
        )
        height_hint.setStyleSheet("color: #888888; font-size: 11px;")
        height_layout.addWidget(height_hint)

        self.group_scipy_height.setLayout(height_layout)
        method_layout.addWidget(self.group_scipy_height)

        # --- NeuroKit2 parameters / NeuroKit2 파라미터 ---
        self.group_neurokit2 = QGroupBox("NeuroKit2 Parameters")
        nk_layout = QVBoxLayout()

        # Sub-method dropdown / 하위 방법 드롭다운
        sub_method_row = QHBoxLayout()
        sub_method_row.addWidget(QLabel("Sub-method:"))
        self.combo_sub_method = QComboBox()
        for key in ECG_PEAK_METHOD_INFO:
            self.combo_sub_method.addItem(key, key)
        sub_method_row.addWidget(self.combo_sub_method)
        nk_layout.addLayout(sub_method_row)

        # Sub-method info label / 하위 방법 정보 라벨
        self.label_sub_method_info = QLabel("")
        self.label_sub_method_info.setWordWrap(True)
        self.label_sub_method_info.setStyleSheet(
            "color: #555555; font-style: italic; margin-left: 10px; padding: 4px;"
        )
        nk_layout.addWidget(self.label_sub_method_info)

        nk_warning = QLabel(
            "Note: NeuroKit2 algorithms are designed for human ECG (60-200 BPM).\n"
            "For animal ECG, use SciPy methods instead."
        )
        nk_warning.setStyleSheet("color: #cc6600; font-size: 11px;")
        nk_layout.addWidget(nk_warning)

        self.group_neurokit2.setLayout(nk_layout)
        method_layout.addWidget(self.group_neurokit2)

        method_group.setLayout(method_layout)
        main_layout.addWidget(method_group)

        # === Detection Range GroupBox / 검출 범위 ===
        range_group = QGroupBox("Detection Range")
        range_layout = QVBoxLayout()

        # Range dropdown / 범위 드롭다운
        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("Range:"))
        self.combo_range = QComboBox()
        self.combo_range.addItem("Total", "total")
        self.combo_range.addItem("Window", "window")
        range_row.addWidget(self.combo_range)
        range_layout.addLayout(range_row)

        # Window Size / 윈도우 크기
        self.window_size_row = QHBoxLayout()
        self.label_window_size = QLabel("Window Size (s):")
        self.window_size_row.addWidget(self.label_window_size)
        self.spin_window_size = QDoubleSpinBox()
        self.spin_window_size.setRange(1.0, 300.0)
        self.spin_window_size.setSingleStep(1.0)
        self.spin_window_size.setDecimals(1)
        self.window_size_row.addWidget(self.spin_window_size)
        range_layout.addLayout(self.window_size_row)

        # Window Step / 윈도우 간격
        self.window_step_row = QHBoxLayout()
        self.label_window_step = QLabel("Window Step (s):")
        self.window_step_row.addWidget(self.label_window_step)
        self.spin_window_step = QDoubleSpinBox()
        self.spin_window_step.setRange(1.0, 300.0)
        self.spin_window_step.setSingleStep(1.0)
        self.spin_window_step.setDecimals(1)
        self.window_step_row.addWidget(self.spin_window_step)
        range_layout.addLayout(self.window_step_row)

        # Hint label / 힌트 라벨
        self.label_window_hint = QLabel("(Step = Size → no overlap)")
        self.label_window_hint.setStyleSheet("color: #888888; font-size: 11px;")
        range_layout.addWidget(self.label_window_hint)

        range_group.setLayout(range_layout)
        main_layout.addWidget(range_group)

        # === Buttons / 버튼 ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        button_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # === Connect signals / 시그널 연결 ===
        self.combo_method.currentIndexChanged.connect(self._on_method_changed)
        self.combo_sub_method.currentIndexChanged.connect(self._on_sub_method_changed)
        self.combo_range.currentIndexChanged.connect(self._on_range_changed)

        # === Load current settings into widgets / 현재 설정 위젯에 로드 ===
        self._load_current_settings()

    def _load_current_settings(self):
        """
        Populate widgets from settings dict.
        설정 딕셔너리에서 위젯 채우기.
        """
        # Detection method / 검출 방법
        saved_method = self.settings.get("method", "scipy_prominence")
        idx = self.combo_method.findData(saved_method)
        if idx >= 0:
            self.combo_method.setCurrentIndex(idx)

        # SciPy - Prominence parameters / SciPy - Prominence 파라미터
        self.spin_prominence.setValue(
            self.settings.get("prominence_multiplier", 0.5)
        )

        # SciPy - Height parameters / SciPy - Height 파라미터
        self.spin_height_ratio.setValue(
            self.settings.get("height_ratio", 0.3)
        )
        self.spin_height_distance.setValue(
            self.settings.get("height_distance", 20)
        )

        # NeuroKit2 sub-method / NeuroKit2 하위 방법
        saved_sub = self.settings.get("sub_method", "neurokit")
        idx = self.combo_sub_method.findData(saved_sub)
        if idx >= 0:
            self.combo_sub_method.setCurrentIndex(idx)
        self._on_sub_method_changed()

        # Detection range / 검출 범위
        saved_range = self.settings.get("detection_range", "total")
        idx = self.combo_range.findData(saved_range)
        if idx >= 0:
            self.combo_range.setCurrentIndex(idx)

        # Window parameters / 윈도우 파라미터
        self.spin_window_size.setValue(self.settings.get("window_size", 20.0))
        self.spin_window_step.setValue(self.settings.get("window_step", 20.0))

        # Update visibility / 가시성 업데이트
        self._on_method_changed()
        self._on_range_changed()

    def _on_method_changed(self):
        """
        Toggle method-specific parameter group visibility.
        방법별 파라미터 그룹 가시성 전환.
        """
        method = self.combo_method.currentData()

        # Update description label / 설명 라벨 업데이트
        desc = ECG_DETECTION_METHOD_INFO.get(method, "")
        self.label_method_desc.setText(desc)

        # Show/hide parameter groups / 파라미터 그룹 표시/숨기기
        self.group_scipy_prominence.setVisible(method == "scipy_prominence")
        self.group_scipy_height.setVisible(method == "scipy_height")
        self.group_neurokit2.setVisible(method == "neurokit2")

    def _on_sub_method_changed(self):
        """
        Update sub-method info label when NeuroKit2 sub-method changes.
        NeuroKit2 하위 방법 변경 시 정보 라벨 업데이트.
        """
        sub_method = self.combo_sub_method.currentData()
        info = ECG_PEAK_METHOD_INFO.get(sub_method, "")
        self.label_sub_method_info.setText(info)

    def _on_range_changed(self):
        """
        Toggle window parameter visibility based on detection range.
        검출 범위에 따라 윈도우 파라미터 가시성 전환.
        """
        is_window = self.combo_range.currentData() == "window"
        self.label_window_size.setVisible(is_window)
        self.spin_window_size.setVisible(is_window)
        self.label_window_step.setVisible(is_window)
        self.spin_window_step.setVisible(is_window)
        self.label_window_hint.setVisible(is_window)

    def get_settings(self) -> dict:
        """
        Return settings dict from current UI state.
        현재 UI 상태에서 설정 딕셔너리 반환.

        All parameters are saved regardless of current method selection,
        so values persist when switching between methods.
        현재 방법 선택과 관계없이 모든 파라미터를 저장하여
        방법 전환 시 값이 유지됨.

        Returns:
            dict: Peak detection settings / 피크 검출 설정
        """
        return {
            "method": self.combo_method.currentData(),
            "sub_method": self.combo_sub_method.currentData(),
            "detection_range": self.combo_range.currentData(),
            "window_size": self.spin_window_size.value(),
            "window_step": self.spin_window_step.value(),
            "prominence_multiplier": self.spin_prominence.value(),
            "height_ratio": self.spin_height_ratio.value(),
            "height_distance": self.spin_height_distance.value(),
        }

    def accept(self):
        """
        Save settings and close dialog.
        설정 저장 후 다이얼로그 닫기.
        """
        save_peak_detection_settings(self.get_settings())
        self.logger.info(f"Peak detection settings saved: {self.get_settings()}")
        super().accept()


# =========================================================================
# Peak Detection Functions / 피크 검출 함수
# =========================================================================

def _detect_on_segment(
    segment: np.ndarray,
    sampling_rate: float,
    settings: dict,
    logger: logging.Logger,
) -> np.ndarray:
    """
    Detect peaks on a single signal segment (method dispatch).
    단일 신호 구간에서 피크 검출 (방법별 분기).

    Args:
        segment: Signal segment / 신호 구간
        sampling_rate: Sampling rate in Hz / Hz 단위 샘플링 레이트
        settings: Peak detection settings / 피크 검출 설정
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Local peak indices within the segment / 구간 내 로컬 피크 인덱스
    """
    method = settings.get("method", "scipy_prominence")

    if method == "scipy_prominence":
        prominence_mult = settings.get("prominence_multiplier", 0.5)
        prominence = np.std(segment) * prominence_mult
        peaks, _ = find_peaks(segment, prominence=prominence)
        return peaks

    elif method == "scipy_height":
        height_ratio = settings.get("height_ratio", 0.3)
        distance = settings.get("height_distance", 20)
        sig_min = np.min(segment)
        sig_max = np.max(segment)
        height_threshold = sig_min + (sig_max - sig_min) * height_ratio
        peaks, _ = find_peaks(segment, height=height_threshold, distance=distance)
        return peaks

    elif method == "neurokit2":
        if not NEUROKIT2_AVAILABLE:
            logger.error("NeuroKit2 is not installed")
            return np.array([], dtype=int)
        sub_method = settings.get("sub_method", "neurokit")
        _, info = nk.ecg_peaks(
            segment, sampling_rate=int(sampling_rate), method=sub_method,
            smoothwindow=0.02, avgwindow=0.15, gradthreshweight=1.5, minlenweight=0.4, mindelay=0.08,
        )
        return np.array(info["ECG_R_Peaks"])

    else:
        logger.error(f"Unknown detection method: {method}")
        return np.array([], dtype=int)


def detect_ecg_r_peaks(
    ecg_cleaned: np.ndarray,
    sampling_rate: float,
    settings: dict,
    logger: logging.Logger | None = None,
) -> np.ndarray | None:
    """
    Detect R-peaks in preprocessed ECG signal.
    전처리된 ECG 신호에서 R-피크 검출.

    Args:
        ecg_cleaned: Preprocessed ECG signal / 전처리된 ECG 신호
        sampling_rate: Sampling rate in Hz / Hz 단위 샘플링 레이트
        settings: Peak detection settings dict / 피크 검출 설정
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Array of R-peak sample indices, or None if failed
                    R-피크 샘플 인덱스 배열, 실패 시 None
    """
    log = logger or logging.getLogger(__name__)
    method = settings.get("method", "scipy_prominence")
    detection_range = settings.get("detection_range", "total")

    if detection_range == "window":
        window_size = settings.get("window_size", 20.0)
        window_step = settings.get("window_step", 20.0)
        log.info(
            f"Detecting R-peaks (windowed): method={method}, "
            f"window_size={window_size}s, window_step={window_step}s"
        )
        return _detect_peaks_windowed(
            ecg_cleaned, sampling_rate, settings, log,
        )
    else:
        log.info(f"Detecting R-peaks (total): method={method}")
        return _detect_peaks_total(ecg_cleaned, sampling_rate, settings, log)


def _detect_peaks_total(
    ecg_cleaned: np.ndarray,
    sampling_rate: float,
    settings: dict,
    logger: logging.Logger,
) -> np.ndarray | None:
    """
    Detect R-peaks across the entire signal.
    전체 신호에서 R-피크 검출.

    Args:
        ecg_cleaned: Preprocessed ECG signal / 전처리된 ECG 신호
        sampling_rate: Sampling rate in Hz / Hz 단위 샘플링 레이트
        settings: Peak detection settings / 피크 검출 설정
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Array of R-peak indices, or None if failed
                    R-피크 인덱스 배열, 실패 시 None
    """
    try:
        r_peaks = _detect_on_segment(ecg_cleaned, sampling_rate, settings, logger)
        logger.info(f"Detected {len(r_peaks)} R-peaks (total mode)")
        return np.sort(r_peaks)
    except Exception as e:
        logger.error(f"R-peak detection failed: {e}", exc_info=True)
        return None


def _detect_peaks_windowed(
    ecg_cleaned: np.ndarray,
    sampling_rate: float,
    settings: dict,
    logger: logging.Logger,
) -> np.ndarray | None:
    """
    Detect R-peaks using sliding window approach.
    슬라이딩 윈도우 방식으로 R-피크 검출.

    Args:
        ecg_cleaned: Preprocessed ECG signal / 전처리된 ECG 신호
        sampling_rate: Sampling rate in Hz / Hz 단위 샘플링 레이트
        settings: Peak detection settings / 피크 검출 설정
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Array of R-peak indices, or None if failed
                    R-피크 인덱스 배열, 실패 시 None
    """
    window_size = settings.get("window_size", 20.0)
    window_step = settings.get("window_step", 20.0)

    window_samples = int(window_size * sampling_rate)
    step_samples = int(window_step * sampling_rate)

    if window_samples <= 0 or step_samples <= 0:
        logger.error(
            f"Invalid window parameters: size={window_size}s, step={window_step}s, "
            f"sr={sampling_rate}Hz"
        )
        return None

    data_length = len(ecg_cleaned)
    all_peaks = set()
    window_count = 0
    start_idx = 0

    while start_idx < data_length:
        end_idx = min(start_idx + window_samples, data_length)
        window_data = ecg_cleaned[start_idx:end_idx]

        # Skip if window too small (< 10 samples)
        # 윈도우가 너무 작으면 스킵 (10 샘플 미만)
        if len(window_data) < 10:
            logger.warning(
                f"  Window {window_count}: too small ({len(window_data)} samples), skipping"
            )
            start_idx += step_samples
            window_count += 1
            continue

        try:
            local_peaks = _detect_on_segment(
                window_data, sampling_rate, settings, logger,
            )
            # Convert local indices to global indices
            # 로컬 인덱스를 글로벌 인덱스로 변환
            for p in local_peaks:
                global_idx = start_idx + p
                if global_idx < data_length:
                    all_peaks.add(global_idx)
        except Exception as e:
            logger.warning(f"  Window {window_count}: peak detection failed: {e}")

        window_count += 1
        start_idx += step_samples

    peaks_array = np.sort(np.array(list(all_peaks), dtype=int))
    logger.info(
        f"Windowed R-peak detection completed: {len(peaks_array)} peaks in "
        f"{window_count} windows (size={window_size}s, step={window_step}s)"
    )
    return peaks_array
