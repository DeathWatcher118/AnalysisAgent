"""
Anomaly data models
Defines structures for anomaly detection and analysis
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class AnomalyType(Enum):
    """Types of anomalies that can be detected"""
    STABILITY = "stability"  # System instability, failures, errors
    PERFORMANCE = "performance"  # Slow response, degraded throughput
    COST = "cost"  # Financial waste, over-provisioning
    RESOURCE = "resource"  # CPU, memory, disk issues
    UNKNOWN = "unknown"


class Severity(Enum):
    """Severity levels for anomalies"""
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Action required soon
    MEDIUM = "medium"  # Should be addressed
    LOW = "low"  # Monitor
    INFO = "info"  # Informational


@dataclass
class Anomaly:
    """
    Represents a detected anomaly
    """
    # Identification
    anomaly_id: str
    detected_at: datetime
    
    # Metric information
    metric_name: str
    metric_type: str  # e.g., "error_rate", "cpu_utilization"
    
    # Values
    current_value: float
    baseline_value: float
    deviation_sigma: float  # Standard deviations from baseline
    deviation_percentage: float  # Percentage change
    
    # Classification
    anomaly_type: AnomalyType
    severity: Severity
    confidence: float  # 0.0 to 1.0
    
    # Context
    affected_resources: List[Dict[str, Any]] = field(default_factory=list)
    time_window: Dict[str, datetime] = field(default_factory=dict)
    related_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'anomaly_id': self.anomaly_id,
            'detected_at': self.detected_at.isoformat(),
            'metric_name': self.metric_name,
            'metric_type': self.metric_type,
            'current_value': self.current_value,
            'baseline_value': self.baseline_value,
            'deviation_sigma': self.deviation_sigma,
            'deviation_percentage': self.deviation_percentage,
            'anomaly_type': self.anomaly_type.value,
            'severity': self.severity.value,
            'confidence': self.confidence,
            'affected_resources': self.affected_resources,
            'time_window': {k: v.isoformat() for k, v in self.time_window.items()},
            'related_metrics': self.related_metrics,
            'metadata': self.metadata
        }


@dataclass
class RootCause:
    """
    Root cause analysis result
    """
    primary_cause: str
    contributing_factors: List[str]
    confidence: float
    evidence: List[str]
    correlation_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    """
    Actionable recommendation for addressing an anomaly
    """
    priority: str  # "critical", "high", "medium", "low"
    action: str  # What to do
    rationale: str  # Why this action
    expected_impact: str  # What will happen
    implementation_steps: List[str] = field(default_factory=list)
    estimated_effort: str = ""  # e.g., "5 minutes", "1 hour"
    risk_level: str = "low"  # "low", "medium", "high"
    cost_impact: Optional[str] = None  # For cost-related recommendations


@dataclass
class HumanReadableSummary:
    """
    Plain language summary for non-technical audiences
    """
    what_happened: str  # Clear explanation of the issue
    why_it_happened: str  # Root cause in simple terms
    what_is_the_impact: str  # Business/operational impact
    what_improvements_can_be_made: str  # Recommended actions
    estimated_benefit_if_implemented: str  # Expected outcomes and benefits


@dataclass
class AnomalyAnalysis:
    """
    Complete analysis of an anomaly with recommendations
    """
    anomaly: Anomaly
    root_cause: RootCause
    recommendations: List[Recommendation]
    
    # Analysis metadata
    analyzed_at: datetime
    analysis_duration_ms: int
    ai_model_used: str
    
    # Additional insights
    historical_context: str = ""
    trend_analysis: str = ""
    predicted_impact: str = ""
    
    # Human-readable summary (non-technical language)
    summary: Optional['HumanReadableSummary'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            'anomaly': self.anomaly.to_dict(),
            'root_cause': {
                'primary_cause': self.root_cause.primary_cause,
                'contributing_factors': self.root_cause.contributing_factors,
                'confidence': self.root_cause.confidence,
                'evidence': self.root_cause.evidence,
                'correlation_data': self.root_cause.correlation_data
            },
            'recommendations': [
                {
                    'priority': rec.priority,
                    'action': rec.action,
                    'rationale': rec.rationale,
                    'expected_impact': rec.expected_impact,
                    'implementation_steps': rec.implementation_steps,
                    'estimated_effort': rec.estimated_effort,
                    'risk_level': rec.risk_level,
                    'cost_impact': rec.cost_impact
                }
                for rec in self.recommendations
            ],
            'analyzed_at': self.analyzed_at.isoformat(),
            'analysis_duration_ms': self.analysis_duration_ms,
            'ai_model_used': self.ai_model_used,
            'historical_context': self.historical_context,
            'trend_analysis': self.trend_analysis,
            'predicted_impact': self.predicted_impact
        }
        
        # Add human-readable summary if available
        if self.summary:
            result['summary'] = {
                'what_happened': self.summary.what_happened,
                'why_it_happened': self.summary.why_it_happened,
                'what_is_the_impact': self.summary.what_is_the_impact,
                'what_improvements_can_be_made': self.summary.what_improvements_can_be_made,
                'estimated_benefit_if_implemented': self.summary.estimated_benefit_if_implemented
            }
        
        return result
    
    def get_plain_language_report(self) -> str:
        """
        Generate a plain language report suitable for all audiences
        """
        if not self.summary:
            return "Summary not available"
        
        report = f"""
ANOMALY ANALYSIS REPORT
{'=' * 80}

WHAT HAPPENED:
{self.summary.what_happened}

WHY IT HAPPENED:
{self.summary.why_it_happened}

WHAT IS THE IMPACT:
{self.summary.what_is_the_impact}

WHAT IMPROVEMENTS CAN BE MADE:
{self.summary.what_improvements_can_be_made}

ESTIMATED BENEFIT IF IMPLEMENTED:
{self.summary.estimated_benefit_if_implemented}

{'=' * 80}
Analysis completed at: {self.analyzed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Confidence level: {self.root_cause.confidence:.0%}
"""
        return report.strip()


# BigQuery schema for Anomaly table
ANOMALY_TABLE_SCHEMA = [
    {"name": "anomaly_id", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "detected_at", "field_type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "metric_name", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "metric_type", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "current_value", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "baseline_value", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "deviation_sigma", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "deviation_percentage", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "anomaly_type", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "severity", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "confidence", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "affected_resources", "field_type": "JSON", "mode": "NULLABLE"},
    {"name": "related_metrics", "field_type": "JSON", "mode": "NULLABLE"},
    {"name": "metadata", "field_type": "JSON", "mode": "NULLABLE"},
]

# BigQuery schema for Analysis table
ANALYSIS_TABLE_SCHEMA = [
    {"name": "analysis_id", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "anomaly_id", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "analyzed_at", "field_type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "root_cause", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "contributing_factors", "field_type": "JSON", "mode": "NULLABLE"},
    {"name": "confidence", "field_type": "FLOAT", "mode": "REQUIRED"},
    {"name": "recommendations", "field_type": "JSON", "mode": "REQUIRED"},
    {"name": "ai_model_used", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "analysis_duration_ms", "field_type": "INTEGER", "mode": "REQUIRED"},
]