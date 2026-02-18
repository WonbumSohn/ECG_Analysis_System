"""
Common Utility Functions Collection
공통 유틸리티 함수 모음
====================================

Contains functions commonly used across the ECG Analysis System.
ECG 분석 시스템에서 공통으로 사용하는 함수를 포함합니다.

Main features / 주요 기능:
- Logging setup: Create and manage date-based log files
  로깅 설정: 날짜 기반 로그 파일 생성 및 관리
"""

import os
import logging
from datetime import datetime


def setup_early_logging(save_location=None):
    """
    Function to initialize early logging with timestamp-based filename.
    타임스탬프 기반 파일명으로 초기 로깅을 초기화하는 함수.

    This is used for logging from app startup until analysis mode is selected.
    앱 시작부터 분석 모드가 선택될 때까지 로깅에 사용됩니다.

    Args:
        save_location (str, optional): User-specified save location. Uses default if None.
                                       사용자 지정 저장 위치. None이면 기본값 사용.

    Returns:
        tuple: (logger instance, log file path)
               (로거 인스턴스, 로그 파일 경로)
    """
    # Determine log directory / 로그 디렉토리 결정
    if save_location:
        # Create log folder in user-specified save location
        # 사용자 지정 저장 위치에 로그 폴더 생성
        log_dir = os.path.join(save_location, "log")
    else:
        # Default: Create log folder path based on current script's directory
        # 기본값: 현재 스크립트 디렉토리 기준으로 로그 폴더 경로 생성
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(os.path.dirname(current_dir), "log")

    # Create date-based subdirectory (YYYYMMDD)
    # 날짜 기반 하위 디렉토리 생성 (YYYYMMDD)
    date_folder = datetime.now().strftime("%Y%m%d")
    session_log_dir = os.path.join(log_dir, date_folder)
    os.makedirs(session_log_dir, exist_ok=True)

    # Generate log filename using timestamp
    # 타임스탬프를 사용하여 로그 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{timestamp}.log"
    log_path = os.path.join(session_log_dir, log_filename)

    # Get root logger and clear any existing handlers
    # 루트 로거를 가져오고 기존 핸들러를 모두 제거
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    # Create file handler / 파일 핸들러 생성
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Create console handler / 콘솔 핸들러 생성
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Add handlers to logger / 로거에 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Early log file created: {log_filename}")
    logger.info("This log will be used until analysis mode is selected")

    return logger, log_path
