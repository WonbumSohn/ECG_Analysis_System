"""
ECG Analysis Module
ECG 분석 모듈

ECG signal analysis GUI and processing functions.
ECG 신호 분석 GUI 및 처리 함수.

Modules / 모듈:
    - ecg_gui: ECG GUI workflow manager / ECG GUI 워크플로우 관리자
    - ecg_monitor_mode_window: Analysis mode selection dialog / 분석 모드 선택 다이얼로그
    - ecg_column_selection_dialog: CSV column mapping dialog / CSV 컬럼 매핑 다이얼로그
    - ecg_offline_analysis: Offline analysis main window / 오프라인 분석 메인 윈도우
    - ecg_preprocessing: Preprocessing dialog and processing logic / 전처리 다이얼로그 및 처리 로직
        - NeuroKit2 ecg_clean (neurokit, biosppy, pantompkins, etc.)
        - Manual filters (bandpass, notch)
        - Windowed processing support / 윈도우 기반 처리 지원
    - ecg_peak_detection: R-peak detection dialog and detection logic / R-피크 검출 다이얼로그 및 검출 로직
        - SciPy Prominence (scipy.signal.find_peaks with prominence)
        - SciPy Height (scipy.signal.find_peaks with height + distance)
        - NeuroKit2 ecg_peaks (neurokit, pantompkins, hamilton, etc.)
        - Total / Windowed detection modes / 전체 / 윈도우 검출 모드 지원
"""

__version__ = "0.2.0"
