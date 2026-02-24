"""
ECG Heart Rate Calculation Dialog and Processing Logic
ECG 심박수 계산 다이얼로그 및 처리 로직

Provides:
- HR calculation settings dialog (method selection + sudden change filter)
  HR 계산 설정 다이얼로그 (방법 선택 + 급격한 변동 필터)
- HR calculation from R-peak indices (windowed mode)
  R-피크 인덱스에서 HR 계산 (윈도우 모드)
- HR calculation settings config helpers
  HR 계산 설정 config 헬퍼
"""

import logging

import numpy as np

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QDoubleSpinBox, QGroupBox, QCheckBox,
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


# HR calculation method descriptions
# HR 계산 방법 설명
ECG_HR_METHOD_INFO = {
    "neurokit2": "Calculate HR from RR intervals using NeuroKit2 signal_rate()",
}


# =========================================================================
# Settings I/O Helpers / 설정 입출력 헬퍼
# =========================================================================

def get_default_hr_calculation_settings() -> dict:
    """
    Return default HR calculation settings.
    기본 HR 계산 설정 반환.

    Returns:
        dict: Default settings / 기본 설정
    """
    return {
        "method": "neurokit2",
        "filter_sudden_changes": False,
        "tolerance_percent": 20.0,
    }


def load_hr_calculation_settings() -> dict:
    """
    Load HR calculation settings from the shared config file.
    공유 config 파일에서 HR 계산 설정 로드.

    Returns:
        dict: HR calculation settings / HR 계산 설정
    """
    full_config = load_ecg_preprocess_settings()
    if full_config and "hr_calculation" in full_config:
        saved = full_config["hr_calculation"]
        # Merge with defaults to ensure all keys exist
        # 모든 키가 존재하도록 defaults와 병합
        defaults = get_default_hr_calculation_settings()
        defaults.update(saved)
        return defaults
    return get_default_hr_calculation_settings()


def save_hr_calculation_settings(settings: dict) -> None:
    """
    Save HR calculation settings to the shared config file.
    공유 config 파일에 HR 계산 설정 저장.

    Args:
        settings: HR calculation settings dict / HR 계산 설정
    """
    full_config = load_ecg_preprocess_settings() or get_default_ecg_preprocess_settings()
    full_config["hr_calculation"] = settings
    save_ecg_preprocess_settings(full_config)


# =========================================================================
# HR Calculation Settings Dialog / HR 계산 설정 다이얼로그
# =========================================================================

class ECGHRSettingsDialog(QDialog):
    """
    Dialog for configuring Heart Rate calculation settings.
    Heart Rate 계산 설정을 구성하기 위한 다이얼로그.

    Supports NeuroKit2-based HR calculation with optional sudden change filter.
    NeuroKit2 기반 HR 계산 및 선택적 급격한 변동 필터 지원.
    """

    def __init__(self, parent=None, current_settings: dict | None = None):
        """
        Initialize HR calculation settings dialog.
        HR 계산 설정 다이얼로그 초기화.

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
            self.settings = load_hr_calculation_settings()

        self._setup_ui()

    def _setup_ui(self):
        """
        Build the dialog UI.
        다이얼로그 UI 구성.
        """
        self.setWindowTitle("Heart Rate Calculation Settings")
        self.setMinimumWidth(450)
        self.setStyleSheet(LIGHT_MODE_STYLESHEET)

        main_layout = QVBoxLayout()

        # === Title / 타이틀 ===
        title = QLabel("Heart Rate Calculation Settings")
        title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 8px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # === HR Calculation Method GroupBox ===
        method_group = QGroupBox("HR Calculation Method")
        method_layout = QVBoxLayout()

        # Method dropdown / 방법 드롭다운
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Method:"))
        self.combo_method = QComboBox()
        for key, desc in ECG_HR_METHOD_INFO.items():
            display_name = key.replace("_", " ").title()
            # "Neurokit2" -> "NeuroKit2"
            display_name = display_name.replace("Neurokit2", "NeuroKit2")
            self.combo_method.addItem(display_name, key)
        method_row.addWidget(self.combo_method)
        method_layout.addLayout(method_row)

        # Method description label / 방법 설명 라벨
        self.label_method_desc = QLabel("")
        self.label_method_desc.setWordWrap(True)
        self.label_method_desc.setStyleSheet(
            "color: #555555; font-style: italic; margin-left: 10px; padding: 4px;"
        )
        method_layout.addWidget(self.label_method_desc)

        method_group.setLayout(method_layout)
        main_layout.addWidget(method_group)

        # === Sudden Change Filter GroupBox ===
        filter_group = QGroupBox("HR Change Filter")
        filter_layout = QVBoxLayout()

        # Filter checkbox / 필터 체크박스
        self.check_filter = QCheckBox("Ignore sudden HR changes")
        self.check_filter.setToolTip(
            "When enabled, HR values that deviate beyond the tolerance\n"
            "from the previous value are replaced with the previous value.\n"
            "This helps filter out noise-induced sudden HR spikes."
        )
        filter_layout.addWidget(self.check_filter)

        # Tolerance row / 허용 범위
        tolerance_row = QHBoxLayout()
        self.label_tolerance = QLabel("Tolerance (%):")
        tolerance_row.addWidget(self.label_tolerance)
        self.spin_tolerance = QDoubleSpinBox()
        self.spin_tolerance.setRange(1.0, 50.0)
        self.spin_tolerance.setSingleStep(1.0)
        self.spin_tolerance.setDecimals(1)
        self.spin_tolerance.setToolTip(
            "Maximum allowed HR change (%) compared to previous value"
        )
        tolerance_row.addWidget(self.spin_tolerance)
        filter_layout.addLayout(tolerance_row)

        # Filter hint label / 필터 힌트 라벨
        self.label_filter_hint = QLabel(
            "If current HR deviates more than ±tolerance% from the previous HR,\n"
            "it is replaced with the previous value.\n"
            "Physiologically, heart rate changes gradually in most cases."
        )
        self.label_filter_hint.setStyleSheet("color: #888888; font-size: 11px;")
        filter_layout.addWidget(self.label_filter_hint)

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

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
        self.check_filter.stateChanged.connect(self._on_filter_toggled)

        # === Load current settings into widgets / 현재 설정 위젯에 로드 ===
        self._load_current_settings()

    def _load_current_settings(self):
        """
        Populate widgets from settings dict.
        설정 딕셔너리에서 위젯 채우기.
        """
        # Method / 방법
        saved_method = self.settings.get("method", "neurokit2")
        idx = self.combo_method.findData(saved_method)
        if idx >= 0:
            self.combo_method.setCurrentIndex(idx)
        self._on_method_changed()

        # Filter settings / 필터 설정
        self.check_filter.setChecked(
            self.settings.get("filter_sudden_changes", False)
        )
        self.spin_tolerance.setValue(
            self.settings.get("tolerance_percent", 20.0)
        )

        # Update filter widget visibility / 필터 위젯 가시성 업데이트
        self._on_filter_toggled()

    def _on_method_changed(self):
        """
        Update method description when method changes.
        방법 변경 시 설명 업데이트.
        """
        method = self.combo_method.currentData()
        desc = ECG_HR_METHOD_INFO.get(method, "")
        self.label_method_desc.setText(desc)

    def _on_filter_toggled(self):
        """
        Toggle tolerance spinbox enabled state based on filter checkbox.
        필터 체크박스에 따라 허용 범위 스핀박스 활성화/비활성화.
        """
        enabled = self.check_filter.isChecked()
        self.label_tolerance.setEnabled(enabled)
        self.spin_tolerance.setEnabled(enabled)
        self.label_filter_hint.setEnabled(enabled)

    def get_settings(self) -> dict:
        """
        Return settings dict from current UI state.
        현재 UI 상태에서 설정 딕셔너리 반환.

        Returns:
            dict: HR calculation settings / HR 계산 설정
        """
        return {
            "method": self.combo_method.currentData(),
            "filter_sudden_changes": self.check_filter.isChecked(),
            "tolerance_percent": self.spin_tolerance.value(),
        }

    def accept(self):
        """
        Save settings and close dialog.
        설정 저장 후 다이얼로그 닫기.
        """
        save_hr_calculation_settings(self.get_settings())
        self.logger.info(f"HR calculation settings saved: {self.get_settings()}")
        super().accept()


# =========================================================================
# HR Calculation Functions / HR 계산 함수
# =========================================================================

def calculate_ecg_heart_rate(
    peak_indices: np.ndarray,
    time_data: np.ndarray,
    sampling_rate: float,
    peak_settings: dict,
    hr_settings: dict,
    logger=None,
) -> np.ndarray | None:
    """
    Calculate heart rate from R-peak indices.
    R-피크 인덱스에서 심박수 계산.

    For window mode: calculates HR per window and assigns the value
    to the next window as a horizontal line (step function).
    윈도우 모드: 윈도우별 HR 계산 후 다음 윈도우에 수평선으로 할당.

    Args:
        peak_indices: R-peak sample indices / R-피크 샘플 인덱스
        time_data: Time array in seconds / 시간 배열 (초 단위)
        sampling_rate: Sampling rate in Hz / 샘플링 레이트 (Hz)
        peak_settings: Peak detection settings (detection_range, window_size, window_step)
                       피크 검출 설정
        hr_settings: HR calculation settings (method, filter options)
                     HR 계산 설정
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: HR data array (same length as time_data, NaN for empty regions)
                    HR 데이터 배열 (time_data와 같은 길이, 빈 구간은 NaN)
        None: If detection_range is "total" (not yet supported) or calculation fails
              detection_range가 "total"이거나 계산 실패 시
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    detection_range = peak_settings.get("detection_range", "total")

    if detection_range == "total":
        logger.info("Total mode HR calculation is not yet supported")
        return None

    # Window mode / 윈도우 모드
    window_size = peak_settings.get("window_size", 20.0)
    window_step = peak_settings.get("window_step", 20.0)
    method = hr_settings.get("method", "neurokit2")
    filter_enabled = hr_settings.get("filter_sudden_changes", False)
    tolerance_pct = hr_settings.get("tolerance_percent", 20.0)

    logger.info(
        f"HR calculation: method={method}, window_size={window_size}s, "
        f"window_step={window_step}s, filter={filter_enabled}, "
        f"tolerance={tolerance_pct}%"
    )

    hr_data = _calculate_hr_windowed(
        peak_indices=peak_indices,
        time_data=time_data,
        sampling_rate=sampling_rate,
        window_size=window_size,
        window_step=window_step,
        method=method,
        logger=logger,
    )

    if hr_data is None:
        return None

    # Apply sudden change filter if enabled
    # 급격한 변동 필터 적용 (활성화 시)
    if filter_enabled:
        hr_data = _apply_sudden_change_filter(
            hr_data=hr_data,
            time_data=time_data,
            window_size=window_size,
            window_step=window_step,
            tolerance_pct=tolerance_pct,
            logger=logger,
        )

    valid_count = np.sum(~np.isnan(hr_data))
    logger.info(f"HR calculation complete: {valid_count} valid data points")

    return hr_data


def _calculate_hr_windowed(
    peak_indices: np.ndarray,
    time_data: np.ndarray,
    sampling_rate: float,
    window_size: float,
    window_step: float,
    method: str,
    logger=None,
) -> np.ndarray | None:
    """
    Calculate HR using sliding window and assign to next window.
    슬라이딩 윈도우로 HR 계산 후 다음 윈도우에 할당.

    For each window [t, t+window_size):
        1. Collect R-peaks within this window
        2. Calculate HR from RR intervals
        3. Assign HR value to the next window [t+window_size, t+2*window_size)

    Args:
        peak_indices: R-peak sample indices / R-피크 샘플 인덱스
        time_data: Time array in seconds / 시간 배열 (초 단위)
        sampling_rate: Sampling rate in Hz / 샘플링 레이트 (Hz)
        window_size: Window size in seconds / 윈도우 크기 (초)
        window_step: Window step in seconds / 윈도우 간격 (초)
        method: HR calculation method / HR 계산 방법
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: HR data array / HR 데이터 배열
        None: If calculation fails / 계산 실패 시
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Initialize HR array with NaN / NaN으로 HR 배열 초기화
    hr_data = np.full(len(time_data), np.nan)

    # Get peak times / 피크 시간 가져오기
    peak_times = time_data[peak_indices]

    data_start = time_data[0]
    data_end = time_data[-1]

    hr_count = 0
    window_count = 0
    window_start = data_start

    while window_start + window_size <= data_end:
        window_end = window_start + window_size
        window_count += 1

        # Collect peaks in current window / 현재 윈도우 내 피크 수집
        window_mask = (peak_times >= window_start) & (peak_times < window_end)
        window_peak_times = peak_times[window_mask]
        window_peak_indices = peak_indices[window_mask]

        if len(window_peak_times) >= 2:
            # Calculate HR from RR intervals / RR 간격에서 HR 계산
            hr_value = _calculate_single_window_hr(
                window_peak_indices=window_peak_indices,
                window_peak_times=window_peak_times,
                sampling_rate=sampling_rate,
                method=method,
                logger=logger,
            )

            if hr_value is not None and hr_value > 0:
                # Assign HR to the NEXT window / 다음 윈도우에 HR 할당
                next_start = window_end
                next_end = window_end + window_size
                assign_mask = (time_data >= next_start) & (time_data < next_end)
                hr_data[assign_mask] = hr_value
                hr_count += 1
        else:
            logger.debug(
                f"Window [{window_start:.1f}s, {window_end:.1f}s): "
                f"insufficient peaks ({len(window_peak_times)}), skipping"
            )

        window_start += window_step

    logger.info(
        f"HR windowed calculation: {window_count} windows processed, "
        f"{hr_count} HR values computed"
    )

    if hr_count == 0:
        logger.warning("No HR values could be calculated from the peaks")
        return None

    return hr_data


def _calculate_single_window_hr(
    window_peak_indices: np.ndarray,
    window_peak_times: np.ndarray,
    sampling_rate: float,
    method: str,
    logger=None,
) -> float | None:
    """
    Calculate HR for a single window from its R-peaks.
    단일 윈도우의 R-피크에서 HR 계산.

    Args:
        window_peak_indices: R-peak sample indices in this window / 윈도우 내 R-피크 샘플 인덱스
        window_peak_times: R-peak times in this window / 윈도우 내 R-피크 시간
        sampling_rate: Sampling rate in Hz / 샘플링 레이트 (Hz)
        method: Calculation method / 계산 방법
        logger: Logger instance / 로거 인스턴스

    Returns:
        float: Heart rate in BPM / 심박수 (BPM)
        None: If calculation fails / 계산 실패 시
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    try:
        if method == "neurokit2" and NEUROKIT2_AVAILABLE:
            # Use NeuroKit2 signal_rate() / NeuroKit2 signal_rate() 사용
            rate = nk.signal_rate(
                window_peak_indices,
                sampling_rate=sampling_rate,
                desired_length=None,
            )
            if len(rate) > 0:
                hr_value = float(np.median(rate))
                return hr_value
            return None
        else:
            # Fallback: manual RR interval calculation
            # 폴백: 수동 RR 간격 계산
            intervals = np.diff(window_peak_times)
            if len(intervals) > 0:
                median_interval = np.median(intervals)
                if median_interval > 0:
                    return 60.0 / median_interval
            return None

    except Exception as e:
        logger.debug(f"HR calculation for window failed: {e}")
        return None


def _apply_sudden_change_filter(
    hr_data: np.ndarray,
    time_data: np.ndarray,
    window_size: float,
    window_step: float,
    tolerance_pct: float,
    logger=None,
) -> np.ndarray:
    """
    Filter out sudden HR changes by replacing outlier values with previous value.
    급격한 HR 변동을 이전 값으로 대체하여 필터링.

    Physiological rationale: Heart rate is regulated by the autonomic nervous system
    and changes gradually. Sudden changes (>±tolerance%) are typically caused by
    noise, motion artifacts, or incorrect peak detection.
    생리학적 근거: 심박수는 자율신경계에 의해 조절되며 점진적으로 변한다.
    급격한 변동(>±tolerance%)은 주로 노이즈, 모션 아티팩트, 잘못된 피크 검출에 의한 것이다.

    Args:
        hr_data: HR data array with NaN gaps / NaN 간격이 있는 HR 데이터 배열
        time_data: Time array in seconds / 시간 배열 (초 단위)
        window_size: Window size in seconds / 윈도우 크기 (초)
        window_step: Window step in seconds / 윈도우 간격 (초)
        tolerance_pct: Maximum allowed change percentage / 최대 허용 변동 비율 (%)
        logger: Logger instance / 로거 인스턴스

    Returns:
        np.ndarray: Filtered HR data array / 필터링된 HR 데이터 배열
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    tolerance = tolerance_pct / 100.0
    filtered_hr = hr_data.copy()

    # Extract unique HR values per window segment
    # 윈도우 구간별 고유 HR 값 추출
    # Each window segment has the same HR value, so we find transitions
    # 각 윈도우 구간은 같은 HR 값을 가지므로 전환점을 찾음
    data_start = time_data[0]
    data_end = time_data[-1]

    # Collect (window_start, hr_value) pairs from the assigned "next window" regions
    # 할당된 "다음 윈도우" 영역에서 (window_start, hr_value) 쌍 수집
    window_hr_pairs = []
    window_start = data_start

    while window_start + window_size <= data_end:
        window_end = window_start + window_size
        # This region corresponds to the "next window" of the source window
        # 이 영역은 소스 윈도우의 "다음 윈도우"에 해당
        next_start = window_end
        next_end = window_end + window_size
        assign_mask = (time_data >= next_start) & (time_data < next_end)

        if np.any(assign_mask):
            hr_values_in_region = hr_data[assign_mask]
            valid_values = hr_values_in_region[~np.isnan(hr_values_in_region)]
            if len(valid_values) > 0:
                # All values in this region should be the same
                # 이 영역의 모든 값은 동일해야 함
                hr_val = valid_values[0]
                window_hr_pairs.append((next_start, next_end, hr_val))

        window_start += window_step

    if len(window_hr_pairs) < 2:
        logger.info("Sudden change filter: not enough HR segments to filter")
        return filtered_hr

    # Apply sequential filter / 순차 필터 적용
    filter_count = 0
    prev_hr = window_hr_pairs[0][2]  # First value is the reference / 첫 값이 기준

    for i in range(1, len(window_hr_pairs)):
        next_start, next_end, current_hr = window_hr_pairs[i]

        lower_bound = prev_hr * (1.0 - tolerance)
        upper_bound = prev_hr * (1.0 + tolerance)

        if current_hr < lower_bound or current_hr > upper_bound:
            # Replace with previous value / 이전 값으로 대체
            logger.debug(
                f"HR filter: [{next_start:.1f}s-{next_end:.1f}s] "
                f"{current_hr:.1f} bpm -> {prev_hr:.1f} bpm "
                f"(exceeded ±{tolerance_pct:.0f}% of {prev_hr:.1f})"
            )
            assign_mask = (time_data >= next_start) & (time_data < next_end)
            filtered_hr[assign_mask] = prev_hr
            filter_count += 1
            # prev_hr stays the same (we rejected the new value)
            # prev_hr은 유지 (새 값을 거부했으므로)
        else:
            prev_hr = current_hr

    if filter_count > 0:
        logger.info(
            f"Sudden change filter applied: {filter_count} out of "
            f"{len(window_hr_pairs)} HR segments replaced"
        )

    return filtered_hr
