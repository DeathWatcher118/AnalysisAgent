"""
Baseline data models
Defines the structure for baseline statistics stored in BigQuery
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class BaselineStats:
    """
    Statistical baseline for a single metric
    Stored in BigQuery Baseline table
    """
    # Identification
    baseline_id: str  # Unique ID: baseline-{metric}-{timestamp}
    metric_name: str  # e.g., "error_rate", "cpu_utilization"
    
    # Statistical measures
    mean: float
    std_dev: float
    min_value: float
    max_value: float
    
    # Percentiles
    p50: float  # Median
    p95: float  # 95th percentile
    p99: float  # 99th percentile
    
    # Metadata
    calculated_at: datetime
    lookback_days: int  # How many days of data used
    sample_count: int  # Number of data points analyzed
    data_source: str  # Table name used for calculation
    
    # Optional fields
    notes: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for BigQuery insertion"""
        data = asdict(self)
        # Convert datetime to string for BigQuery
        data['calculated_at'] = self.calculated_at.isoformat()
        return data
    
    def to_bigquery_row(self):
        """Convert to BigQuery row format"""
        return {
            'baseline_id': self.baseline_id,
            'metric_name': self.metric_name,
            'mean': self.mean,
            'std_dev': self.std_dev,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'p50': self.p50,
            'p95': self.p95,
            'p99': self.p99,
            'calculated_at': self.calculated_at.isoformat() if isinstance(self.calculated_at, datetime) else self.calculated_at,
            'lookback_days': self.lookback_days,
            'sample_count': self.sample_count,
            'data_source': self.data_source,
            'notes': self.notes or ''
        }


# BigQuery table schema for Baseline table
BASELINE_TABLE_SCHEMA = [
    {"name": "baseline_id", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "metric_name", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "mean", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "std_dev", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "min_value", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "max_value", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "p50", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "p95", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "p99", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "calculated_at", "field_type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "lookback_days", "field_type": "INTEGER", "mode": "REQUIRED"},
    {"name": "sample_count", "field_type": "INTEGER", "mode": "REQUIRED"},
    {"name": "data_source", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "notes", "field_type": "STRING", "mode": "NULLABLE"},
]