"""
ECG Analysis System Configuration Manager
ECG 분석 시스템 설정 관리자

Handles saving and loading analysis parameters between sessions.
세션 간 분석 파라미터를 저장하고 불러오는 기능을 담당합니다.
Settings are stored in JSON format in the config folder.
설정은 config 폴더의 JSON 형식으로 저장됩니다.

Main features / 주요 기능:
- Save parameters (save_config) / 파라미터 저장
- Load parameters (load_config) / 파라미터 불러오기
- Query individual parameters (get) / 개별 파라미터 조회
- Update parameters (update) / 파라미터 업데이트
"""

import json
import os
import logging
from pathlib import Path


class ConfigManager:
    """
    Manager class for saving and loading parameter settings to/from files
    파라미터 설정을 파일로 저장하고 불러오는 관리자 클래스

    Main attributes / 주요 속성:
        config_dir: Directory where configuration files are stored (project_root/config)
                    설정 파일이 저장되는 디렉토리
        config_path: Full path to the configuration file
                     설정 파일의 전체 경로
        logger: Logger for configuration-related operations
                설정 관련 작업을 위한 로거
    """

    def __init__(self, config_filename="common_parameters.json", save_location=None):
        """
        Initialize the configuration manager.
        설정 관리자를 초기화합니다.

        Args:
            config_filename: Configuration file name (default: common_parameters.json)
                            설정 파일 이름 (기본값: common_parameters.json)
            save_location: Optional custom directory for configuration file.
                          If provided, config will be saved to save_location/config/
                          If None, uses project_root/config/ (default for development)
                          사용자 지정 설정 파일 디렉토리 (선택사항)
        """
        # Determine configuration directory based on save_location
        # save_location에 따라 설정 디렉토리 결정
        if save_location:
            # Use custom save location (for .app deployments)
            self.config_dir = Path(save_location) / "config"
        else:
            # Get project root directory path (parent directory of src)
            # 프로젝트 루트 디렉토리 경로 (src의 상위 디렉토리)
            current_dir = Path(__file__).parent
            project_root = current_dir.parent
            # Configuration directory: project_root/config
            self.config_dir = project_root / "config"

        self.config_path = self.config_dir / config_filename

        # Logger for tracking configuration operations
        # 설정 작업 추적을 위한 로거
        self.logger = logging.getLogger()

    def load_config(self):
        """
        Load parameters from configuration file.
        설정 파일에서 파라미터를 불러옵니다.

        Returns:
            dict: Dictionary containing saved parameters, returns None if file doesn't exist
                  저장된 파라미터를 담은 딕셔너리, 파일이 없으면 None 반환
        """
        # Check if configuration file exists
        if not self.config_path.exists():
            self.logger.info(f"No existing config file found at {self.config_path}")
            return None

        try:
            # Read JSON file
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.logger.info(f"Configuration loaded from {self.config_path}")
                self.logger.info(f"Loaded parameters: {list(config.keys())}")
                return config
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Failed to load config file: {e}", exc_info=True)
            return None

    def save_config(self, config):
        """
        Save configuration to file.
        설정을 파일로 저장합니다.

        Args:
            config: Dictionary containing parameters to save
                    저장할 파라미터를 담은 딕셔너리
        """
        try:
            # Create config directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Save as JSON file (4-space indentation, preserve Korean characters)
            # JSON 파일로 저장 (4칸 들여쓰기, 한글 문자 보존)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            self.logger.info(f"Configuration saved to {self.config_path}")
            self.logger.info(f"Saved parameters: {list(config.keys())}")

        except IOError as e:
            self.logger.error(f"Failed to save config file: {e}", exc_info=True)

    def get(self, key, default=None):
        """
        Query individual parameter value.
        개별 파라미터 값을 조회합니다.

        Args:
            key: Parameter key to query / 조회할 파라미터 키
            default: Default value to return if parameter doesn't exist or config file is missing
                     파라미터가 없거나 설정 파일이 없을 때 반환할 기본값

        Returns:
            Parameter value or default value / 파라미터 값 또는 기본값
        """
        config = self.load_config()
        if config is None:
            return default
        return config.get(key, default)

    def update(self, updates):
        """
        Update configuration with new values.
        새로운 값으로 설정을 업데이트합니다.

        If configuration file exists, loads it and updates,
        if it doesn't exist, creates a new configuration file.
        설정 파일이 있으면 불러와서 업데이트하고,
        없으면 새로운 설정 파일을 생성합니다.

        Args:
            updates: Dictionary of key-value pairs to update
                     업데이트할 키-값 쌍의 딕셔너리
        """
        # Load existing configuration (empty dictionary if none exists)
        config = self.load_config()
        if config is None:
            config = {}

        # Update with new values
        config.update(updates)

        # Save updated configuration
        self.save_config(config)
