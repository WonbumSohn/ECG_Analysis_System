"""
ECG GUI Manager
ECG GUI 관리자

Manages the entire workflow of ECG signal analysis GUI:
ECG 신호 분석 GUI의 전체 워크플로우를 관리합니다:

1. Analysis mode selection window (Realtime or Offline)
   분석 모드 선택 윈도우 (실시간 또는 오프라인)
2. For Realtime mode: Coming soon
   실시간 모드: 준비 중
3. For Offline mode: Opens offline analysis window
   오프라인 모드: 오프라인 분석 윈도우 열기

This module serves as the entry point for all ECG-related GUI functionality.
이 모듈은 모든 ECG 관련 GUI 기능의 진입점입니다.
"""

import logging
import os
from PySide6.QtWidgets import QMessageBox
from ecg.ecg_monitor_mode_window import ECGMonitorModeWindow


def ecg_analysis_gui(parent=None, save_location=None, early_log_path=None):
    """
    Start ECG GUI workflow.
    ECG GUI 워크플로우 시작.

    This function is the main entry point for ECG signal analysis.
    이 함수는 ECG 신호 분석의 메인 진입점입니다.
    Called when user selects ECG signal from MainWindow.
    MainWindow에서 ECG 신호를 선택할 때 호출됩니다.

    Workflow / 워크플로우:
    1. Display analysis mode selection window (Realtime or Offline)
       분석 모드 선택 윈도우 표시
    2. For Realtime mode: Coming soon
       실시간 모드: 준비 중
    3. For Offline mode: Open offline analysis window
       오프라인 모드: 오프라인 분석 윈도우 열기

    Args:
        parent: Parent widget (MainWindow), required for proper window management
                부모 위젯 (MainWindow), 적절한 윈도우 관리에 필요
        save_location: Result save location (parent directory of data, results, log folders)
                       결과 저장 위치 (data, results, log 폴더의 부모 디렉토리)
        early_log_path: Path to early log file for reference
                        참조용 초기 로그 파일 경로
    """
    logger = logging.getLogger()
    logger.info("=" * 60)
    logger.info("Starting ECG GUI workflow (v0.1.0)")
    logger.info("=" * 60)

    # Extract early log filename (just the filename, not full path)
    # 초기 로그 파일명 추출 (전체 경로가 아닌 파일명만)
    early_log_filename = None
    if early_log_path:
        early_log_filename = os.path.basename(early_log_path)
        logger.info(f"Related Early Log: {early_log_filename}")

    # Step 1: Analysis mode selection
    # 단계 1: 분석 모드 선택
    logger.info("Step 1: Opening ECG analysis mode selection window")
    mode_window = ECGMonitorModeWindow(parent)
    mode_window.exec()

    # Check if user selected a mode
    # 사용자가 모드를 선택했는지 확인
    if not mode_window.selected_mode:
        logger.info("User exited mode selection, returning to Main GUI")
        logger.info("=" * 60)
        return

    logger.info(f"User selected mode: {mode_window.selected_mode}")

    try:
        # Check which mode was selected
        # 어떤 모드가 선택되었는지 확인
        if mode_window.selected_mode == "Offline Analysis":
            # ===== Offline Data Analysis mode =====
            # ===== 오프라인 데이터 분석 모드 =====
            logger.info("Launching Offline Data Analysis mode")

            # Show loading dialog while importing and creating window
            # 윈도우 임포트 및 생성 중 로딩 다이얼로그 표시
            from PySide6.QtWidgets import QProgressDialog, QApplication
            from PySide6.QtCore import Qt

            progress = QProgressDialog("Loading Offline Analysis...", None, 0, 0, parent)
            progress.setWindowTitle("Loading")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setCancelButton(None)
            progress.show()
            QApplication.processEvents()

            # Import and launch offline analysis window
            # 오프라인 분석 윈도우 임포트 및 실행
            from ecg.ecg_offline_analysis import ECGOfflineAnalysis
            from config_manager import ConfigManager

            offline_window = ECGOfflineAnalysis(
                parent=parent,
                config_manager=ConfigManager(save_location=save_location),
                save_location=save_location,
                early_log_path=early_log_filename
            )

            # Close loading dialog / 로딩 다이얼로그 닫기
            progress.close()

            offline_window.exec()
            logger.info("Offline Data Analysis window closed")

        else:
            # ===== Real-time Monitoring mode =====
            # ===== 실시간 모니터링 모드 =====
            logger.info("Real-time mode selected but not yet implemented")
            QMessageBox.information(
                parent,
                "Real-time Data Analysis",
                "Real-time Data Analysis feature is coming soon.\n\n"
                "실시간 데이터 분석 기능은 준비 중입니다."
            )

    except Exception as e:
        logger.error(f"Failed to launch ECG analysis GUI: {e}", exc_info=True)
        if parent:
            QMessageBox.critical(
                parent,
                "Error",
                f"Failed to launch ECG analysis window:\n\n{str(e)}"
            )

    logger.info("ECG GUI workflow completed")
    logger.info("=" * 60)
