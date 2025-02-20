# src/utils/config.py
import json
import os
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration management class."""
    
    DEFAULT_CONFIG = {
        "openai_api_key": "",
        "log_level": "INFO",
        "templates_dir": "templates",
        "output_dir": "output",
        "agents": {
            "requirement_analyst": {
                "model": "gpt-4-turbo-preview",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "test_designer": {
                "model": "gpt-4-turbo-preview",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "test_case_writer": {
                "model": "gpt-4-turbo-preview",
                "temperature": 0.5,
                "max_tokens": 2000
            },
            "quality_assurance": {
                "model": "gpt-4-turbo-preview",
                "temperature": 0.3,
                "max_tokens": 2000
            }
        },
        "export": {
            "default_template": "standard",
            "excel_settings": {
                "sheet_name": "Test Cases",
                "freeze_panes": "B2"
            }
        }
    }

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Configuration loaded from {self.config_path}")
                    return self._merge_with_default(config)
            else:
                self._save_config(self.DEFAULT_CONFIG)
                logger.info(f"Default configuration created at {self.config_path}")
                return self.DEFAULT_CONFIG
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            return self.DEFAULT_CONFIG

    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")

    def _merge_with_default(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded config with default config to ensure all keys exist."""
        merged = self.DEFAULT_CONFIG.copy()
        for key, value in config.items():
            if isinstance(value, dict) and key in merged:
                merged[key].update(value)
            else:
                merged[key] = value
        return merged

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value and save to file."""
        self.config[key] = value
        self._save_config(self.config)

    def update(self, updates: Dict[str, Any]):
        """Update multiple configuration values."""
        self.config.update(updates)
        self._save_config(self.config)

def load_config() -> Config:
    """Load configuration singleton."""
    config_path = os.getenv("AI_TESTER_CONFIG", "config.json")
    return Config(config_path)