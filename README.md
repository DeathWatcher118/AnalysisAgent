# Anomaly Analysis Agent Service

This directory contains ONLY the AI-powered anomaly analysis agent files needed for deployment.

## Contents

```
analysis-agent/
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   └── anomaly_analyzer.py    # Main AI agent (1,310 lines)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── anomaly.py             # Anomaly data models
│   │   └── baseline.py            # Baseline data models
│   └── utils/
│       ├── __init__.py
│       └── config.py               # Configuration utilities
├── config.yaml                     # Service configuration
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables
├── create_anomaly_analysis_table.sql  # BigQuery schema
├── Dockerfile                      # Container build instructions
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
```

## What's Included

✅ **Anomaly Analyzer Agent** - AI-powered analysis engine (1,310 lines)
✅ **Data Models** - Anomaly, RootCause, Recommendation, Analysis structures
✅ **Vertex AI Integration** - Gemini for intelligent root cause analysis
✅ **BigQuery Persistence** - Save analyses with user feedback tracking
✅ **Migration Analysis** - Detect if user changes caused anomalies
✅ **Human-Readable Output** - Plain language summaries for all audiences
✅ **False Positive Tracking** - User feedback loop for reliability
✅ **Configuration** - YAML config and utilities
✅ **Dependencies** - All required Python packages
✅ **SQL Schema** - BigQuery table creation script

## What's NOT Included

❌ Baseline calculator (separate service)
❌ Notification system (separate component)
❌ Documentation files
❌ Scripts
❌ Test files

## Key Features

### 1. AI-Powered Analysis
- Uses Vertex AI Gemini for intelligent root cause identification
- Fallback to rule-based analysis for reliability
- Evidence collection with confidence scoring

### 2. Context Gathering
- Historical data comparison
- Related metrics analysis
- Recent changes and migrations review
- Temporal pattern identification

### 3. Type-Specific Recommendations
- **Stability**: Error handling, retry logic, circuit breakers
- **Performance**: Optimization, caching, resource allocation
- **Cost**: Right-sizing, reserved instances, cleanup
- **Resource**: Scaling, limits, monitoring

### 4. Migration Impact Analysis
- Queries BigQuery migrations table
- Analyzes user additions and functionality changes
- Determines temporal correlation with anomalies
- Integrates findings into root cause explanation

### 5. Human-Readable Output
Every analysis includes 5 clear sections:
1. **What Happened** - Plain language explanation
2. **Why It Happened** - Root cause in simple terms
3. **What Is The Impact** - Business/operational consequences
4. **What Improvements Can Be Made** - Actionable recommendations
5. **Estimated Benefit If Implemented** - Expected outcomes

### 6. User Feedback System
- Mark false positives
- Track reliability metrics
- Calculate false positive rates
- Continuous improvement loop

## Deploy to GCP

### Option 1: Build and Deploy Locally

```bash
# Navigate to this directory
cd analysis-agent

# Build Docker image
docker build -t gcr.io/ccibt-hack25ww7-730/anomaly-analyzer:latest .

# Push to Container Registry
docker push gcr.io/ccibt-hack25ww7-730/anomaly-analyzer:latest

# Deploy to Cloud Run
gcloud run deploy anomaly-analyzer \
  --image=gcr.io/ccibt-hack25ww7-730/anomaly-analyzer:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=900 \
  --set-env-vars=GCP_PROJECT_ID=ccibt-hack25ww7-730,GCP_REGION=us-central1,PYTHONUNBUFFERED=1 \
  --project=ccibt-hack25ww7-730
```

### Option 2: Deploy via Cloud Build

```bash
# From parent directory
cd ..
gcloud builds submit analysis-agent \
  --tag=gcr.io/ccibt-hack25ww7-730/anomaly-analyzer:latest \
  --project=ccibt-hack25ww7-730
```

## Setup BigQuery Table

Before deploying, create the BigQuery table:

```bash
# Run the SQL schema
bq query --use_legacy_sql=false < create_anomaly_analysis_table.sql
```

Or via GCP Console:
1. Go to BigQuery: https://console.cloud.google.com/bigquery?project=ccibt-hack25ww7-730
2. Open SQL workspace
3. Paste contents of `create_anomaly_analysis_table.sql`
4. Click "RUN"

## Test Locally

```bash
# Build image
docker build -t anomaly-analyzer .

# Run container
docker run -p 8080:8080 \
  -e GCP_PROJECT_ID=ccibt-hack25ww7-730 \
  -e GCP_REGION=us-central1 \
  anomaly-analyzer
```

## Usage

### Analyze an Anomaly

```python
from src.agent.anomaly_analyzer import AnomalyAnalyzerAgent
from src.models.anomaly import Anomaly, AnomalyType, Severity

# Initialize agent
agent = AnomalyAnalyzerAgent()

# Create anomaly object
anomaly = Anomaly(
    anomaly_id="anom_001",
    detected_at=datetime.now(),
    metric_name="error_rate",
    metric_type="error_rate",
    current_value=15.5,
    baseline_value=2.3,
    deviation_sigma=5.2,
    deviation_percentage=574.0,
    anomaly_type=AnomalyType.STABILITY,
    severity=Severity.HIGH,
    # ... other fields
)

# Analyze
analysis = agent.analyze_anomaly(anomaly)

# Get human-readable summary
print(analysis.human_readable_summary.what_happened)
print(analysis.human_readable_summary.why_it_happened)
print(analysis.human_readable_summary.what_is_the_impact)
print(analysis.human_readable_summary.what_improvements_can_be_made)
print(analysis.human_readable_summary.estimated_benefit_if_implemented)
```

## Configuration

Edit `config.yaml` to customize:
- AI optimization settings
- Confidence thresholds
- BigQuery dataset and table names
- Analysis parameters

## Environment Variables

Required environment variables (set in `.env` or deployment):
- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_REGION` - Deployment region (us-central1)
- `PYTHONUNBUFFERED` - Python output buffering (1)

## Service Details

- **Service Name**: anomaly-analyzer
- **Region**: us-central1
- **Memory**: 2GB
- **CPU**: 2 vCPUs
- **Timeout**: 900 seconds
- **Authentication**: Public (unauthenticated)

## Integration

This service receives anomalies from detection systems via the standardized interface defined in the main repository's `docs/ANOMALY_DETECTOR_INTERFACE.md`.

## Support

For full documentation, see parent directory:
- `docs/AI_AGENT_GUIDE.md` - Complete architecture and usage
- `docs/ANOMALY_DETECTOR_INTERFACE.md` - Data contract specification
- `docs/ANALYSIS_OUTPUT_EXAMPLE.md` - Output examples
- `docs/MIGRATION_ANALYSIS.md` - Migration tracking details
- `docs/USER_FEEDBACK_SYSTEM.md` - Feedback loop documentation