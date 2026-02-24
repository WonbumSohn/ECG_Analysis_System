# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview / 프로젝트 개요

ECG Analysis System - ECG(심전도) 신호 분석 시스템
- GUI Framework: PySide6
- Language: Python 3
- Architecture: BDI_GUI 프로젝트와 동일한 패턴 사용 (향후 병합 용이)

## Project Structure / 프로젝트 구조

```
0011_ECG_Analysis_System/
├── CLAUDE.md
├── requirements.txt               # PySide6, neurokit2 등 의존성
├── config/
│   ├── common_parameters.json     # 공통 설정 (save_location 등)
│   └── ecg_preprocess_settings.json  # ECG 전처리 설정
└── src/
    ├── main.py                    # 진입점 + MainWindow (신호 선택 UI)
    ├── common_utils.py            # 로깅 유틸리티 (setup_early_logging)
    ├── config_manager.py          # JSON 기반 설정 관리자
    └── ecg/
        ├── __init__.py            # ECG 모듈 메타데이터
        ├── ecg_gui.py             # ECG GUI 워크플로우 관리자
        ├── ecg_monitor_mode_window.py  # 분석 모드 선택 다이얼로그
        ├── ecg_column_selection_dialog.py  # CSV 컬럼 매핑 다이얼로그
        ├── ecg_offline_analysis.py     # 오프라인 분석 메인 윈도우
        ├── ecg_preprocessing.py        # 전처리 다이얼로그 및 처리 로직
        └── ecg_peak_detection.py       # R-피크 검출 다이얼로그 및 처리 로직
```

## Build & Run Commands / 빌드 및 실행 명령어

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # macOS

# 의존성 설치
pip install -r requirements.txt

# 앱 실행 (src 디렉토리에서)
python src/main.py
```

## Architecture / 아키텍처

- **MainWindow** (`src/main.py`): QMainWindow 기반 메인 화면. Browse/Set으로 저장 위치 설정 후 신호 선택 버튼(PPG/ECG/EMG/EEG) 표시
- **ECGMonitorModeWindow** (`src/ecg/ecg_monitor_mode_window.py`): QDialog 기반 모드 선택. Real-time(비활성) / Offline(활성)
- **ecg_analysis_gui** (`src/ecg/ecg_gui.py`): ECG GUI 워크플로우 진입점
- **ECGOfflineAnalysis** (`src/ecg/ecg_offline_analysis.py`): QDialog 기반 오프라인 분석 윈도우. CSV 로드, 전처리, 시각화
- **ecg_preprocessing** (`src/ecg/ecg_preprocessing.py`): 전처리 다이얼로그 (방법 선택, 수동 필터, NeuroKit2) 및 전처리 실행 로직. 윈도우 기반 처리 지원
- **ecg_peak_detection** (`src/ecg/ecg_peak_detection.py`): R-피크 검출 다이얼로그 (NeuroKit2) 및 검출 실행 로직. Total/Window 모드 지원
- **Logging**: 2단계 로깅 (early logging → session logging). `{save_location}/log/YYYYMMDD/YYYYMMDD_HHMMSS.log`
- **Config**: JSON 기반 설정 관리. `config/common_parameters.json`, `config/ecg_preprocess_settings.json`

## Related Projects / 관련 프로젝트

이 프로젝트는 아래 프로젝트들과 연관되어 있으며, 필요시 참조 가능:
- `0004_PPG` - PPG 관련 프로젝트
- `0005_nRF54` - nRF54 개발 프로젝트
- `0007_BDI_GUI` - BDI GUI 프로젝트 (**구조 패턴 원본**)
- `nRF54DK`, `nRF52DK` - nRF 개발 키트 프로젝트
