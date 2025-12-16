"""
Configuration management
Loads and provides access to configuration settings
"""

import os
import yaml
from typing import Dict, Any, List
from pathlib import Path


class Config:
    """
    Configuration manager for anomaly detection system
    Loads settings from config.yaml
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config.yaml file. If None, looks in project root.
        """
        if config_path is None:
            # Look for config.yaml in project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config.yaml"
        
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            print(f"[OK] Configuration loaded from {self.config_path}")
            return config
        except FileNotFoundError:
            print(f"[WARNING] Config file not found: {self.config_path}")
            print("[INFO] Using default configuration")
            return self._get_default_config()
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            print("[INFO] Using default configuration")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'bigquery': {
                'project_id': 'ccibt-hack25ww7-730',
                'dataset_id': 'hackaton',
                'location': 'us-central1'
            },
            'baseline': {
                'lookback_days': 30,
                'calculation_method': 'simple_stats',
                'refresh_schedule': 'daily',
                'percentiles': [50, 95, 99]
            },
            'detection': {
                'threshold_sigma': 2.5,
                'analysis_window_hours': 24,
                'min_confidence': 0.7
            },
            'insight': {
                'model': 'gemini-1.5-pro',
                'max_tokens': 1024,
                'temperature': 0.3
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Path to config value (e.g., "baseline.lookback_days")
            default: Default value if key not found
        
        Returns:
            Configuration value
        
        Example:
            config.get("baseline.lookback_days")  # Returns 30
            config.get("baseline.calculation_method")  # Returns "simple_stats"
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    # Convenience methods for common config access
    
    @property
    def bigquery_project_id(self) -> str:
        """Get BigQuery project ID"""
        return self.get('bigquery.project_id', 'ccibt-hack25ww7-730')
    
    @property
    def bigquery_dataset_id(self) -> str:
        """Get BigQuery dataset ID"""
        return self.get('bigquery.dataset_id', 'hackaton')
    
    @property
    def baseline_lookback_days(self) -> int:
        """Get baseline lookback days"""
        return self.get('baseline.lookback_days', 30)
    
    @property
    def baseline_calculation_method(self) -> str:
        """Get baseline calculation method"""
        return self.get('baseline.calculation_method', 'simple_stats')
    
    @property
    def baseline_metrics(self) -> List[Dict[str, Any]]:
        """Get list of metrics to calculate baselines for"""
        return self.get('baseline.metrics', [])
    
    @property
    def detection_threshold_sigma(self) -> float:
        """Get detection threshold (standard deviations)"""
        return self.get('detection.threshold_sigma', 2.5)
    
    @property
    def detection_analysis_window_hours(self) -> int:
        """Get analysis window in hours"""
        return self.get('detection.analysis_window_hours', 24)
    
    @property
    def insight_model(self) -> str:
        """Get ADK model name"""
        return self.get('insight.model', 'gemini-1.5-pro')
    
    @property
    def insight_max_tokens(self) -> int:
        """Get max tokens for insight generation"""
        return self.get('insight.max_tokens', 1024)
    
    @property
    def insight_temperature(self) -> float:
        """Get temperature for insight generation"""
        return self.get('insight.temperature', 0.3)
    
    def reload(self):
        """Reload configuration from file"""
        self._config = self._load_config()
        print("[OK] Configuration reloaded")
    
    def update(self, key_path: str, value: Any):
        """
        Update configuration value
        
        Args:
            key_path: Path to config value (e.g., "baseline.lookback_days")
            value: New value
        """
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        print(f"[OK] Updated {key_path} = {value}")
    
    def save(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
            print(f"[OK] Configuration saved to {self.config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")
    
    def __repr__(self) -> str:
        return f"Config(path={self.config_path})"


# Global configuration instance
_config = None

def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config


if __name__ == "__main__":
    # Test configuration loading
    config = Config()
    
    print("\n" + "=" * 80)
    print("CONFIGURATION TEST")
    print("=" * 80)
    
    print(f"\nBigQuery Project: {config.bigquery_project_id}")
    print(f"BigQuery Dataset: {config.bigquery_dataset_id}")
    print(f"Baseline Lookback Days: {config.baseline_lookback_days}")
    print(f"Baseline Method: {config.baseline_calculation_method}")
    print(f"Detection Threshold: {config.detection_threshold_sigma} sigma")
    print(f"Insight Model: {config.insight_model}")
    
    print(f"\nBaseline Metrics:")
    for metric in config.baseline_metrics:
        status = "[OK]" if metric.get('enabled', False) else "[DISABLED]"
        print(f"  {status} {metric['name']} (priority: {metric.get('priority', 'N/A')})")
    
    print("\n" + "=" * 80)