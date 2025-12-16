"""
Cloud Function entry point for Anomaly Analysis Agent Service
"""

import functions_framework
import json
import logging
from datetime import datetime
from typing import Dict, Any

from src.agent.anomaly_analyzer import AnomalyAnalyzerAgent
from src.models.anomaly import Anomaly, AnomalyType, Severity
from src.utils.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@functions_framework.http
def analyze_anomaly(request):
    """
    HTTP Cloud Function to analyze detected anomalies
    
    Expected JSON payload (matches ANOMALY_DETECTOR_INTERFACE.md):
    {
        "anomaly_id": "anom_20241216_001",
        "detected_at": "2024-12-16T14:05:30Z",
        "metric_name": "error_rate",
        "metric_type": "error_rate",
        "current_value": 15.5,
        "baseline_value": 2.3,
        "deviation_sigma": 5.2,
        "deviation_percentage": 574.0,
        "anomaly_type": "stability",
        "severity": "high",
        "source_system": "cloud_workload_dataset",
        "affected_resources": ["service-a", "service-b"]
    }
    
    Returns:
    {
        "success": true,
        "analysis_id": "analysis_20241216_001",
        "anomaly_id": "anom_20241216_001",
        "root_causes": [...],
        "recommendations": [...],
        "human_readable_summary": {
            "what_happened": "...",
            "why_it_happened": "...",
            "what_is_the_impact": "...",
            "what_improvements_can_be_made": "...",
            "estimated_benefit_if_implemented": "..."
        },
        "analyzed_at": "2024-12-16T14:05:35Z"
    }
    """
    
    # Set CORS headers for the preflight request
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    try:
        # Parse request
        request_json = request.get_json(silent=True)
        
        if not request_json:
            return (
                json.dumps({
                    'error': 'Invalid request',
                    'message': 'Request body must be JSON'
                }),
                400,
                headers
            )
        
        # Validate required fields (per ANOMALY_DETECTOR_INTERFACE.md)
        required_fields = [
            'anomaly_id', 'detected_at', 'metric_name', 'metric_type',
            'current_value', 'baseline_value', 'deviation_sigma',
            'deviation_percentage', 'anomaly_type', 'severity'
        ]
        missing_fields = [f for f in required_fields if f not in request_json]
        
        if missing_fields:
            return (
                json.dumps({
                    'error': 'Missing required fields',
                    'missing': missing_fields,
                    'required': required_fields
                }),
                400,
                headers
            )
        
        logger.info(f"Analyzing anomaly: {request_json['anomaly_id']}")
        
        # Parse datetime
        detected_at = datetime.fromisoformat(request_json['detected_at'].replace('Z', '+00:00'))
        
        # Create Anomaly object
        anomaly = Anomaly(
            anomaly_id=request_json['anomaly_id'],
            detected_at=detected_at,
            metric_name=request_json['metric_name'],
            metric_type=request_json['metric_type'],
            current_value=float(request_json['current_value']),
            baseline_value=float(request_json['baseline_value']),
            deviation_sigma=float(request_json['deviation_sigma']),
            deviation_percentage=float(request_json['deviation_percentage']),
            anomaly_type=AnomalyType(request_json['anomaly_type']),
            severity=Severity(request_json['severity']),
            confidence=request_json.get('confidence', 0.8),
            affected_resources=request_json.get('affected_resources', []),
            time_window=request_json.get('time_window', {}),
            related_metrics=request_json.get('related_metrics', {}),
            metadata=request_json.get('metadata', {})
        )
        
        # Initialize analyzer
        config = get_config()
        analyzer = AnomalyAnalyzerAgent(config)
        
        # Analyze anomaly
        analysis = analyzer.analyze_anomaly(anomaly)
        
        # Prepare response
        response_data = {
            'success': True,
            'anomaly_id': analysis.anomaly.anomaly_id,
            'root_cause': {
                'primary_cause': analysis.root_cause.primary_cause,
                'contributing_factors': analysis.root_cause.contributing_factors,
                'confidence': analysis.root_cause.confidence,
                'evidence': analysis.root_cause.evidence
            },
            'recommendations': [
                {
                    'priority': rec.priority,
                    'action': rec.action,
                    'rationale': rec.rationale,
                    'expected_impact': rec.expected_impact,
                    'implementation_steps': rec.implementation_steps,
                    'estimated_effort': rec.estimated_effort,
                    'risk_level': rec.risk_level
                }
                for rec in analysis.recommendations
            ],
            'analyzed_at': analysis.analyzed_at.isoformat() + 'Z',
            'ai_model_used': analysis.ai_model_used,
            'analysis_duration_ms': analysis.analysis_duration_ms,
            'saved_to_bigquery': True
        }
        
        # Add human-readable summary if available
        if analysis.summary:
            response_data['human_readable_summary'] = {
                'what_happened': analysis.summary.what_happened,
                'why_it_happened': analysis.summary.why_it_happened,
                'what_is_the_impact': analysis.summary.what_is_the_impact,
                'what_improvements_can_be_made': analysis.summary.what_improvements_can_be_made,
                'estimated_benefit_if_implemented': analysis.summary.estimated_benefit_if_implemented
            }
        
        logger.info(f"Analysis completed successfully for anomaly: {analysis.anomaly.anomaly_id}")
        
        return (json.dumps(response_data), 200, headers)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return (
            json.dumps({
                'error': 'Validation error',
                'message': str(e)
            }),
            400,
            headers
        )
    
    except Exception as e:
        logger.error(f"Error analyzing anomaly: {str(e)}", exc_info=True)
        return (
            json.dumps({
                'error': 'Internal server error',
                'message': str(e),
                'type': type(e).__name__
            }),
            500,
            headers
        )


@functions_framework.http
def health(request):
    """Health check endpoint"""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    try:
        # Test BigQuery connection
        config = get_config()
        analyzer = AnomalyAnalyzerAgent(config)
        
        # Get false positive rate as health metric
        fp_rate = analyzer.get_false_positive_rate()
        
        return (
            json.dumps({
                'status': 'healthy',
                'service': 'anomaly-analyzer',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'project_id': config.bigquery_project_id,
                'dataset_id': config.bigquery_dataset_id,
                'false_positive_rate': fp_rate
            }),
            200,
            headers
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return (
            json.dumps({
                'status': 'unhealthy',
                'service': 'anomaly-analyzer',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }),
            503,
            headers
        )