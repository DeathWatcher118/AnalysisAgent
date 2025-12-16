-- Create table for storing anomaly analysis results with user feedback
-- Project: ccibt-hack25ww7-730
-- Dataset: hackaton
-- Table: anomaly_analysis

CREATE TABLE IF NOT EXISTS `ccibt-hack25ww7-730.hackaton.anomaly_analysis` (
    -- Analysis identification
    analysis_id STRING NOT NULL,
    anomaly_id STRING NOT NULL,
    analyzed_at TIMESTAMP NOT NULL,
    
    -- Anomaly details
    anomaly_detected_at TIMESTAMP NOT NULL,
    metric_name STRING NOT NULL,
    metric_type STRING NOT NULL,
    current_value FLOAT64 NOT NULL,
    baseline_value FLOAT64 NOT NULL,
    deviation_sigma FLOAT64 NOT NULL,
    deviation_percentage FLOAT64 NOT NULL,
    anomaly_type STRING NOT NULL,  -- stability, performance, cost, resource
    severity STRING NOT NULL,  -- critical, high, medium, low, info
    confidence FLOAT64 NOT NULL,
    
    -- Root cause analysis
    root_cause_primary STRING NOT NULL,
    root_cause_factors ARRAY<STRING>,
    root_cause_confidence FLOAT64 NOT NULL,
    root_cause_evidence ARRAY<STRING>,
    
    -- Recommendations (JSON array)
    recommendations JSON NOT NULL,
    
    -- Human-readable summary
    summary_what_happened STRING,
    summary_why_happened STRING,
    summary_impact STRING,
    summary_improvements STRING,
    summary_benefits STRING,
    
    -- Analysis metadata
    ai_model_used STRING NOT NULL,
    analysis_duration_ms INT64 NOT NULL,
    
    -- Migration context
    migration_detected BOOL DEFAULT FALSE,
    migration_summary STRING,
    
    -- USER FEEDBACK FIELDS (for false positive tracking)
    is_false_positive BOOL,  -- NULL = not reviewed, TRUE = false positive, FALSE = true positive
    reviewed_by STRING,  -- Email or user ID of reviewer
    reviewed_at TIMESTAMP,  -- When the review was done
    review_notes STRING,  -- User comments about the anomaly
    feedback_category STRING,  -- Why false positive: 'expected_behavior', 'incorrect_baseline', 'data_quality', 'migration_related', 'other'
    
    -- Notification tracking
    notified BOOL DEFAULT FALSE,
    notification_attempts INT64 DEFAULT 0
)
PARTITION BY DATE(analyzed_at)
CLUSTER BY anomaly_type, severity, is_false_positive
OPTIONS(
    description="Anomaly analysis results with user feedback for reliability tracking",
    labels=[("component", "ai_agent"), ("purpose", "anomaly_analysis")]
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_anomaly_id 
ON `ccibt-hack25ww7-730.hackaton.anomaly_analysis`(anomaly_id);

CREATE INDEX IF NOT EXISTS idx_reviewed 
ON `ccibt-hack25ww7-730.hackaton.anomaly_analysis`(is_false_positive);

-- Create view for unreviewed anomalies
CREATE OR REPLACE VIEW `ccibt-hack25ww7-730.hackaton.unreviewed_anomalies` AS
SELECT 
    analysis_id,
    anomaly_id,
    analyzed_at,
    anomaly_detected_at,
    metric_name,
    anomaly_type,
    severity,
    confidence,
    root_cause_primary,
    summary_what_happened,
    summary_why_happened,
    summary_impact,
    summary_improvements
FROM `ccibt-hack25ww7-730.hackaton.anomaly_analysis`
WHERE is_false_positive IS NULL
ORDER BY analyzed_at DESC;

-- Create view for false positive analysis
CREATE OR REPLACE VIEW `ccibt-hack25ww7-730.hackaton.false_positive_stats` AS
SELECT 
    anomaly_type,
    severity,
    COUNT(*) as total_count,
    COUNTIF(is_false_positive = TRUE) as false_positive_count,
    COUNTIF(is_false_positive = FALSE) as true_positive_count,
    COUNTIF(is_false_positive IS NULL) as unreviewed_count,
    SAFE_DIVIDE(COUNTIF(is_false_positive = TRUE), 
                COUNTIF(is_false_positive IS NOT NULL)) as false_positive_rate,
    1.0 - SAFE_DIVIDE(COUNTIF(is_false_positive = TRUE), 
                      COUNTIF(is_false_positive IS NOT NULL)) as reliability_score
FROM `ccibt-hack25ww7-730.hackaton.anomaly_analysis`
WHERE analyzed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY anomaly_type, severity
ORDER BY anomaly_type, severity;

-- Create view for reliability dashboard
CREATE OR REPLACE VIEW `ccibt-hack25ww7-730.hackaton.analysis_reliability` AS
SELECT 
    DATE(analyzed_at) as analysis_date,
    COUNT(*) as total_analyses,
    COUNTIF(is_false_positive = TRUE) as false_positives,
    COUNTIF(is_false_positive = FALSE) as true_positives,
    COUNTIF(is_false_positive IS NULL) as unreviewed,
    SAFE_DIVIDE(COUNTIF(is_false_positive = TRUE), 
                COUNTIF(is_false_positive IS NOT NULL)) as daily_fp_rate,
    AVG(root_cause_confidence) as avg_confidence,
    AVG(confidence) as avg_detection_confidence
FROM `ccibt-hack25ww7-730.hackaton.anomaly_analysis`
WHERE analyzed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY analysis_date
ORDER BY analysis_date DESC;