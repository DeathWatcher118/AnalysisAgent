"""
AI Agent for Anomaly Analysis and Recommendations

This agent analyzes detected anomalies and provides:
- Context about what the anomaly is
- Root cause analysis (why it occurred)
- Actionable recommendations based on anomaly type
- Impact assessment and mitigation strategies
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import time

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.cloud import bigquery

from ..models.anomaly import (
    Anomaly, AnomalyType, Severity,
    RootCause, Recommendation, AnomalyAnalysis, HumanReadableSummary
)
from ..utils.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnomalyAnalyzerAgent:
    """
    AI-powered agent for analyzing anomalies and generating recommendations
    
    Capabilities:
    - Contextual analysis of anomalies
    - Root cause identification
    - Type-specific recommendations (stability, performance, cost)
    - Impact assessment
    - Actionable mitigation strategies
    """
    
    def __init__(self, config=None):
        """
        Initialize the anomaly analyzer agent
        
        Args:
            config: Configuration object. If None, uses global config.
        """
        self.config = config or get_config()
        
        # Initialize Vertex AI
        try:
            vertexai.init(
                project=self.config.bigquery_project_id,
                location=self.config.get('bigquery.location', 'us-central1')
            )
            self.ai_available = True
            logger.info("Anomaly Analyzer Agent initialized with Vertex AI")
        except Exception as e:
            self.ai_available = False
            logger.warning(f"Vertex AI initialization failed: {e}")
            logger.info("Agent will use rule-based analysis")
        
        # Initialize BigQuery client
        self.bigquery_client = bigquery.Client(
            project=self.config.bigquery_project_id
        )
        
        logger.info(f"AI Model: {self.config.insight_model}")
        logger.info(f"Analysis Mode: {'AI-Powered' if self.ai_available else 'Rule-Based'}")
    
    def analyze_anomaly(self, anomaly: Anomaly) -> AnomalyAnalysis:
        """
        Perform complete analysis of an anomaly
        
        Args:
            anomaly: Detected anomaly to analyze
        
        Returns:
            AnomalyAnalysis with root cause and recommendations
        """
        start_time = time.time()
        logger.info(f"Analyzing anomaly: {anomaly.anomaly_id}")
        logger.info(f"Type: {anomaly.anomaly_type.value}, Severity: {anomaly.severity.value}")
        
        try:
            # Gather context
            context = self._gather_context(anomaly)
            
            # Perform root cause analysis
            root_cause = self._analyze_root_cause(anomaly, context)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(anomaly, root_cause, context)
            
            # Generate human-readable summary
            summary = self._generate_human_readable_summary(anomaly, root_cause, recommendations, context)
            
            # Create analysis result
            duration_ms = int((time.time() - start_time) * 1000)
            
            analysis = AnomalyAnalysis(
                anomaly=anomaly,
                root_cause=root_cause,
                recommendations=recommendations,
                analyzed_at=datetime.now(),
                analysis_duration_ms=duration_ms,
                ai_model_used=self.config.insight_model if self.ai_available else "rule-based",
                historical_context=context.get('historical_summary', ''),
                trend_analysis=context.get('trend_analysis', ''),
                predicted_impact=self._predict_impact(anomaly, root_cause),
                summary=summary
            )
            
            logger.info(f"Analysis complete in {duration_ms}ms")
            logger.info(f"Root cause: {root_cause.primary_cause}")
            logger.info(f"Recommendations: {len(recommendations)}")
            
            # Save analysis to BigQuery
            self._save_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    
    def _gather_context(self, anomaly: Anomaly) -> Dict[str, Any]:
        """
        Gather contextual information about the anomaly
        """
        logger.debug("Gathering context...")
        
        context = {
            'anomaly_details': anomaly.to_dict(),
            'time_range': {
                'start': anomaly.detected_at - timedelta(hours=24),
                'end': anomaly.detected_at
            }
        }
        
        try:
            # Query historical data
            historical_data = self._query_historical_metrics(
                anomaly.metric_name,
                context['time_range']['start'],
                context['time_range']['end']
            )
            context['historical_data'] = historical_data
            context['historical_summary'] = self._summarize_historical_data(historical_data)
            
            # Query related metrics
            related_metrics = self._query_related_metrics(anomaly)
            context['related_metrics'] = related_metrics
            
            # Check for migrations or changes
            recent_changes = self._query_recent_changes(
                context['time_range']['start'],
                context['time_range']['end']
            )
            context['recent_changes'] = recent_changes
            
            # Analyze migration impact
            migration_analysis = self._analyze_migration_impact(anomaly, recent_changes)
            context['migration_analysis'] = migration_analysis
            
            if migration_analysis['likely_cause']:
                logger.info(f"Migration likely caused anomaly: {migration_analysis['impact_summary']}")
            
            # Trend analysis
            context['trend_analysis'] = self._analyze_trend(historical_data)
            
        except Exception as e:
            logger.warning(f"Failed to gather some context: {e}")
        
        return context
    
    def _analyze_root_cause(self, anomaly: Anomaly, context: Dict[str, Any]) -> RootCause:
        """
        Determine the root cause of the anomaly using AI
        """
        logger.debug("Analyzing root cause...")
        
        if self.ai_available:
            try:
                return self._ai_root_cause_analysis(anomaly, context)
            except Exception as e:
                logger.warning(f"AI analysis failed: {e}, using rule-based")
        
        return self._rule_based_root_cause(anomaly, context)
    
    def _ai_root_cause_analysis(self, anomaly: Anomaly, context: Dict[str, Any]) -> RootCause:
        """
        Use AI to analyze root cause
        """
        prompt = self._build_root_cause_prompt(anomaly, context)
        
        model = GenerativeModel(self.config.insight_model)
        generation_config = GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        response_text = response.text.strip()
        
        # Parse JSON response
        if response_text.startswith('```json'):
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif response_text.startswith('```'):
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        result = json.loads(response_text)
        
        # Ensure migration analysis is included in correlation data
        correlation_data = result.get('correlation_data', {})
        if 'migration_analysis' not in correlation_data and context.get('migration_analysis'):
            correlation_data['migration_analysis'] = context['migration_analysis']
        
        return RootCause(
            primary_cause=result['primary_cause'],
            contributing_factors=result['contributing_factors'],
            confidence=result['confidence'],
            evidence=result['evidence'],
            correlation_data=correlation_data
        )
    
    def _build_root_cause_prompt(self, anomaly: Anomaly, context: Dict[str, Any]) -> str:
        """
        Build prompt for AI root cause analysis
        """
        return f"""
You are an expert cloud infrastructure analyst specializing in anomaly detection and root cause analysis.

ANOMALY DETAILS:
- Type: {anomaly.anomaly_type.value}
- Metric: {anomaly.metric_name}
- Current Value: {anomaly.current_value:.2f}
- Baseline Value: {anomaly.baseline_value:.2f}
- Deviation: {anomaly.deviation_sigma:.2f} sigma ({anomaly.deviation_percentage:.1f}%)
- Severity: {anomaly.severity.value}
- Detected At: {anomaly.detected_at.isoformat()}

CONTEXT:
- Historical Summary: {context.get('historical_summary', 'N/A')}
- Trend: {context.get('trend_analysis', 'N/A')}
- Recent Changes: {json.dumps(context.get('recent_changes', []), indent=2)}
- Related Metrics: {json.dumps(context.get('related_metrics', {}), indent=2)}

MIGRATION ANALYSIS:
{json.dumps(context.get('migration_analysis', {}), indent=2)}

TASK:
Analyze this anomaly and determine the root cause. Consider:
1. What is the PRIMARY cause of this anomaly?
2. What are the CONTRIBUTING factors?
3. What EVIDENCE supports your analysis?
4. Are there CORRELATIONS with other events?
5. **IMPORTANT**: Did recent MIGRATIONS cause this? Check for:
   - User migrations (additional users added to the system)
   - Functionality changes (new features requiring more resources)
   - Configuration changes
   - Resource requirement changes

RESPOND IN JSON FORMAT:
{{
  "primary_cause": "Clear, specific statement of the root cause",
  "contributing_factors": [
    "Factor 1",
    "Factor 2",
    "Factor 3"
  ],
  "confidence": 0.85,
  "evidence": [
    "Specific data point or observation 1",
    "Specific data point or observation 2",
    "Specific data point or observation 3"
  ],
  "correlation_data": {{
    "correlated_events": ["event1", "event2"],
    "temporal_correlation": 0.92,
    "migration_analysis": {{
      "likely_cause": true/false,
      "impact_summary": "Description of migration impact",
      "impact_factors": ["factor1", "factor2"]
    }}
  }}
}}

IMPORTANT:
- Be specific and data-driven
- Cite evidence from the provided context
- Focus on actionable insights
- **Pay special attention to migration events** - they are a common cause of anomalies
- If migrations added users or functionality, explain how that increased resource demands
- Consider both technical and operational factors
"""
    
    def _rule_based_root_cause(self, anomaly: Anomaly, context: Dict[str, Any]) -> RootCause:
        """
        Rule-based root cause analysis (fallback)
        """
        # Analyze based on anomaly type
        if anomaly.anomaly_type == AnomalyType.STABILITY:
            primary_cause = f"Elevated {anomaly.metric_name} indicating system instability"
            contributing_factors = [
                "Increased error rate beyond normal thresholds",
                "Potential resource contention",
                "Possible configuration changes"
            ]
        elif anomaly.anomaly_type == AnomalyType.PERFORMANCE:
            primary_cause = f"Performance degradation in {anomaly.metric_name}"
            contributing_factors = [
                "Increased workload or traffic",
                "Resource bottleneck",
                "Inefficient processing"
            ]
        elif anomaly.anomaly_type == AnomalyType.COST:
            primary_cause = f"Unexpected cost increase in {anomaly.metric_name}"
            contributing_factors = [
                "Over-provisioned resources",
                "Inefficient resource utilization",
                "Unnecessary redundancy"
            ]
        else:
            primary_cause = f"Anomalous behavior detected in {anomaly.metric_name}"
            contributing_factors = ["Deviation from established baseline"]
        
        # Check for recent changes
        if context.get('recent_changes'):
            contributing_factors.append("Recent system changes or migrations")
        
        evidence = [
            f"Current value ({anomaly.current_value:.2f}) deviates {anomaly.deviation_sigma:.2f} sigma from baseline ({anomaly.baseline_value:.2f})",
            f"Deviation represents {anomaly.deviation_percentage:.1f}% change",
            f"Confidence level: {anomaly.confidence:.0%}"
        ]
        
        return RootCause(
            primary_cause=primary_cause,
            contributing_factors=contributing_factors,
            confidence=0.75,
            evidence=evidence,
            correlation_data={}
        )
    
    def _generate_recommendations(
        self,
        anomaly: Anomaly,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """
        Generate actionable recommendations based on anomaly type
        """
        logger.debug("Generating recommendations...")
        
        if self.ai_available:
            try:
                return self._ai_generate_recommendations(anomaly, root_cause, context)
            except Exception as e:
                logger.warning(f"AI recommendation generation failed: {e}, using rule-based")
        
        return self._rule_based_recommendations(anomaly, root_cause)
    
    def _ai_generate_recommendations(
        self,
        anomaly: Anomaly,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """
        Use AI to generate recommendations
        """
        prompt = self._build_recommendation_prompt(anomaly, root_cause, context)
        
        model = GenerativeModel(self.config.insight_model)
        generation_config = GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        response_text = response.text.strip()
        
        # Parse JSON response
        if response_text.startswith('```json'):
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif response_text.startswith('```'):
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        result = json.loads(response_text)
        
        recommendations = []
        for rec_data in result['recommendations']:
            recommendations.append(Recommendation(
                priority=rec_data['priority'],
                action=rec_data['action'],
                rationale=rec_data['rationale'],
                expected_impact=rec_data['expected_impact'],
                implementation_steps=rec_data.get('implementation_steps', []),
                estimated_effort=rec_data.get('estimated_effort', ''),
                risk_level=rec_data.get('risk_level', 'low'),
                cost_impact=rec_data.get('cost_impact')
            ))
        
        return recommendations
    
    def _build_recommendation_prompt(
        self,
        anomaly: Anomaly,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> str:
        """
        Build prompt for AI recommendation generation
        """
        anomaly_type_guidance = {
            AnomalyType.STABILITY: """
STABILITY ISSUE - Focus on:
- How to restore system stability
- Preventing cascading failures
- Improving error handling and resilience
- Monitoring and alerting improvements
""",
            AnomalyType.PERFORMANCE: """
PERFORMANCE ISSUE - Focus on:
- How to improve response times
- Optimizing resource utilization
- Scaling strategies
- Caching and optimization opportunities
""",
            AnomalyType.COST: """
COST OPTIMIZATION - Focus on:
- Cost-saving opportunities
- Right-sizing resources
- Eliminating waste
- WHY changes won't negatively impact performance
- Cost-benefit analysis
"""
        }
        
        guidance = anomaly_type_guidance.get(anomaly.anomaly_type, "")
        
        return f"""
You are an expert cloud infrastructure consultant providing actionable recommendations.

ANOMALY:
- Type: {anomaly.anomaly_type.value}
- Severity: {anomaly.severity.value}
- Metric: {anomaly.metric_name}
- Deviation: {anomaly.deviation_percentage:.1f}%

ROOT CAUSE:
- Primary: {root_cause.primary_cause}
- Contributing Factors: {', '.join(root_cause.contributing_factors)}
- Confidence: {root_cause.confidence:.0%}

{guidance}

TASK:
Provide 2-4 specific, actionable recommendations to address this anomaly.

For EACH recommendation, provide:
1. **Priority**: critical/high/medium/low
2. **Action**: Specific action to take (be concrete)
3. **Rationale**: Why this action addresses the root cause
4. **Expected Impact**: What will improve and by how much
5. **Implementation Steps**: Detailed steps to implement
6. **Estimated Effort**: Time/resources required
7. **Risk Level**: low/medium/high
8. **Cost Impact**: (for cost anomalies) Savings estimate and performance impact

RESPOND IN JSON FORMAT:
{{
  "recommendations": [
    {{
      "priority": "high",
      "action": "Specific action to take",
      "rationale": "Why this addresses the root cause",
      "expected_impact": "What will improve (be specific with metrics)",
      "implementation_steps": [
        "Step 1: Detailed instruction",
        "Step 2: Detailed instruction",
        "Step 3: Detailed instruction"
      ],
      "estimated_effort": "15 minutes",
      "risk_level": "low",
      "cost_impact": "Save $X/month with no performance impact because..."
    }}
  ]
}}

IMPORTANT:
- Be specific and actionable
- Prioritize by impact and urgency
- Consider implementation complexity
- For cost recommendations, ALWAYS explain why performance won't be affected
- Provide concrete metrics where possible
"""
    
    def _rule_based_recommendations(
        self,
        anomaly: Anomaly,
        root_cause: RootCause
    ) -> List[Recommendation]:
        """
        Generate rule-based recommendations (fallback)
        """
        recommendations = []
        
        if anomaly.anomaly_type == AnomalyType.STABILITY:
            recommendations.extend([
                Recommendation(
                    priority="high",
                    action=f"Investigate and address elevated {anomaly.metric_name}",
                    rationale="High error rates indicate system instability that requires immediate attention",
                    expected_impact="Restore system stability and prevent cascading failures",
                    implementation_steps=[
                        "Review recent logs for error patterns",
                        "Check for resource constraints",
                        "Verify configuration changes",
                        "Implement additional error handling"
                    ],
                    estimated_effort="30-60 minutes",
                    risk_level="low"
                ),
                Recommendation(
                    priority="medium",
                    action="Implement enhanced monitoring and alerting",
                    rationale="Early detection prevents issues from escalating",
                    expected_impact="Faster incident response and reduced downtime",
                    implementation_steps=[
                        "Set up alerts for error rate thresholds",
                        "Configure log aggregation",
                        "Create dashboard for key metrics"
                    ],
                    estimated_effort="1-2 hours",
                    risk_level="low"
                )
            ])
        
        elif anomaly.anomaly_type == AnomalyType.PERFORMANCE:
            recommendations.extend([
                Recommendation(
                    priority="high",
                    action="Optimize resource allocation",
                    rationale="Performance degradation often indicates resource bottlenecks",
                    expected_impact="Improve response times by 20-40%",
                    implementation_steps=[
                        "Analyze resource utilization patterns",
                        "Identify bottlenecks (CPU, memory, I/O)",
                        "Scale resources appropriately",
                        "Implement caching where applicable"
                    ],
                    estimated_effort="1-3 hours",
                    risk_level="medium"
                ),
                Recommendation(
                    priority="medium",
                    action="Review and optimize queries/operations",
                    rationale="Inefficient operations compound under load",
                    expected_impact="Reduce latency and improve throughput",
                    implementation_steps=[
                        "Profile slow operations",
                        "Optimize database queries",
                        "Implement connection pooling",
                        "Add appropriate indexes"
                    ],
                    estimated_effort="2-4 hours",
                    risk_level="low"
                )
            ])
        
        elif anomaly.anomaly_type == AnomalyType.COST:
            recommendations.extend([
                Recommendation(
                    priority="high",
                    action="Right-size over-provisioned resources",
                    rationale="Resources are allocated beyond actual usage requirements",
                    expected_impact="Reduce costs by 20-40% without performance impact",
                    implementation_steps=[
                        "Analyze actual resource utilization",
                        "Identify over-provisioned instances",
                        "Gradually reduce resource allocation",
                        "Monitor performance during changes"
                    ],
                    estimated_effort="1-2 hours",
                    risk_level="low",
                    cost_impact="Performance will not be affected because current utilization is well below provisioned capacity"
                ),
                Recommendation(
                    priority="medium",
                    action="Implement auto-scaling policies",
                    rationale="Match resource allocation to actual demand",
                    expected_impact="Optimize costs while maintaining performance",
                    implementation_steps=[
                        "Define scaling metrics and thresholds",
                        "Configure auto-scaling groups",
                        "Set minimum and maximum limits",
                        "Test scaling behavior"
                    ],
                    estimated_effort="2-3 hours",
                    risk_level="medium",
                    cost_impact="Save 30-50% on compute costs during low-traffic periods"
                )
            ])
        
        return recommendations
    
    def _predict_impact(self, anomaly: Anomaly, root_cause: RootCause) -> str:
        """
        Predict the impact if the anomaly is not addressed
        """
        severity_impacts = {
            Severity.CRITICAL: "Immediate service disruption likely. User impact imminent.",
            Severity.HIGH: "Significant degradation expected within hours. Action required soon.",
            Severity.MEDIUM: "Gradual degradation over days. Should be addressed proactively.",
            Severity.LOW: "Minor impact. Monitor for escalation."
        }
        
        return severity_impacts.get(anomaly.severity, "Impact assessment pending")
    def _generate_human_readable_summary(
        self,
        anomaly: Anomaly,
        root_cause: RootCause,
        recommendations: List[Recommendation],
        context: Dict[str, Any]
    ) -> HumanReadableSummary:
        """
        Generate a plain language summary for non-technical audiences
        
        This summary answers four key questions:
        1. What happened?
        2. Why did it happen?
        3. What is the impact?
        4. What improvements can be made and what are the benefits?
        """
        logger.debug("Generating human-readable summary...")
        
        # 1. WHAT HAPPENED - Clear explanation of the issue
        what_happened = self._explain_what_happened(anomaly)
        
        # 2. WHY IT HAPPENED - Root cause in simple terms
        why_it_happened = self._explain_why_it_happened(anomaly, root_cause)
        
        # 3. WHAT IS THE IMPACT - Business/operational impact
        what_is_the_impact = self._explain_impact(anomaly, root_cause, context)
        
        # 4. WHAT IMPROVEMENTS CAN BE MADE - Recommended actions
        what_improvements_can_be_made = self._explain_improvements(recommendations)
        
        # 5. ESTIMATED BENEFIT IF IMPLEMENTED - Expected outcomes
        estimated_benefit = self._explain_benefits(anomaly, recommendations)
        
        return HumanReadableSummary(
            what_happened=what_happened,
            why_it_happened=why_it_happened,
            what_is_the_impact=what_is_the_impact,
            what_improvements_can_be_made=what_improvements_can_be_made,
            estimated_benefit_if_implemented=estimated_benefit
        )
    
    def _explain_what_happened(self, anomaly: Anomaly) -> str:
        """Explain what happened in plain language"""
        
        # Map metric types to human-readable descriptions
        metric_descriptions = {
            'error_rate': 'error rate',
            'task_execution_time': 'task completion time',
            'cpu_utilization': 'CPU usage',
            'memory_usage': 'memory usage',
            'request_latency': 'response time',
            'compute_cost': 'computing costs',
            'throughput': 'processing speed'
        }
        
        metric_desc = metric_descriptions.get(
            anomaly.metric_name.lower(),
            anomaly.metric_name.replace('_', ' ')
        )
        
        # Determine direction and magnitude
        if anomaly.current_value > anomaly.baseline_value:
            direction = "increased"
            comparison = "higher than"
        else:
            direction = "decreased"
            comparison = "lower than"
        
        # Format values based on metric type
        if 'rate' in anomaly.metric_type.lower() or '%' in anomaly.metric_type:
            current_str = f"{anomaly.current_value:.1f}%"
            baseline_str = f"{anomaly.baseline_value:.1f}%"
        elif 'cost' in anomaly.metric_type.lower() or 'usd' in anomaly.metric_type.lower():
            current_str = f"${anomaly.current_value:,.2f}"
            baseline_str = f"${anomaly.baseline_value:,.2f}"
        elif 'time' in anomaly.metric_type.lower() or 'ms' in anomaly.metric_type.lower():
            current_str = f"{anomaly.current_value:.0f}ms"
            baseline_str = f"{anomaly.baseline_value:.0f}ms"
        else:
            current_str = f"{anomaly.current_value:.1f}"
            baseline_str = f"{anomaly.baseline_value:.1f}"
        
        explanation = (
            f"We detected an unusual spike in your system's {metric_desc}. "
            f"The {metric_desc} {direction} to {current_str}, which is {abs(anomaly.deviation_percentage):.0f}% "
            f"{comparison} the normal level of {baseline_str}. "
            f"This change is significant - it's {anomaly.deviation_sigma:.1f} times larger than typical variations we see."
        )
        
        # Add affected resources if available
        if anomaly.affected_resources:
            resource_count = len(anomaly.affected_resources)
            if resource_count == 1:
                explanation += f" This issue is affecting 1 resource in your system."
            else:
                explanation += f" This issue is affecting {resource_count} resources in your system."
        
        return explanation
    
    def _explain_why_it_happened(self, anomaly: Anomaly, root_cause: RootCause) -> str:
        """Explain why it happened in simple terms"""
        
        # Start with the primary cause in plain language
        explanation = root_cause.primary_cause
        
        # Add contributing factors if available
        if root_cause.contributing_factors:
            explanation += "\n\nSeveral factors contributed to this issue:\n"
            for i, factor in enumerate(root_cause.contributing_factors[:3], 1):
                explanation += f"{i}. {factor}\n"
        
        # Add evidence if available
        if root_cause.evidence:
            explanation += "\nWe identified this by observing:\n"
            for i, evidence in enumerate(root_cause.evidence[:3], 1):
                explanation += f"• {evidence}\n"
        
        # Add migration context if relevant
        migration_context = root_cause.correlation_data.get('migration_analysis', {})
        if migration_context.get('likely_cause'):
            explanation += "\n**Migration Event Detected:**\n"
            explanation += migration_context.get('impact_summary', '')
            if migration_context.get('impact_factors'):
                explanation += "\n\nSpecific changes that may have caused this:\n"
                for factor in migration_context['impact_factors'][:3]:
                    explanation += f"• {factor}\n"
        
        # Add confidence statement
        confidence_pct = root_cause.confidence * 100
        if confidence_pct >= 90:
            confidence_str = "very confident"
        elif confidence_pct >= 75:
            confidence_str = "confident"
        elif confidence_pct >= 60:
            confidence_str = "reasonably confident"
        else:
            confidence_str = "moderately confident"
        
        explanation += f"\nWe are {confidence_str} ({confidence_pct:.0f}%) in this assessment based on the available data."
        
        return explanation.strip()
    
    def _explain_impact(self, anomaly: Anomaly, root_cause: RootCause, context: Dict[str, Any]) -> str:
        """Explain the business/operational impact"""
        
        impact_by_type = {
            AnomalyType.STABILITY: {
                Severity.CRITICAL: "Your system is experiencing critical stability issues that could lead to complete service outages. Users may be unable to access your services, and data integrity could be at risk. This requires immediate attention to prevent business disruption.",
                Severity.HIGH: "Your system's reliability is significantly degraded. Users are likely experiencing errors and service interruptions. If not addressed quickly, this could escalate to a complete outage and damage user trust.",
                Severity.MEDIUM: "Your system is showing signs of instability. Some users may experience occasional errors or degraded service. While not critical yet, this should be addressed soon to prevent escalation.",
                Severity.LOW: "Minor stability issues detected. Most users won't notice any problems, but monitoring is recommended to ensure it doesn't worsen."
            },
            AnomalyType.PERFORMANCE: {
                Severity.CRITICAL: "Your system is running extremely slowly, severely impacting user experience. Users are likely abandoning tasks due to long wait times. This is causing significant business impact and potential revenue loss.",
                Severity.HIGH: "Performance has degraded noticeably. Users are experiencing slow response times that are frustrating and may lead to reduced engagement or lost business opportunities.",
                Severity.MEDIUM: "System performance is slower than normal. While still functional, users may notice delays that could affect their satisfaction and productivity.",
                Severity.LOW: "Minor performance degradation detected. Most users won't notice significant differences, but efficiency could be improved."
            },
            AnomalyType.COST: {
                Severity.CRITICAL: f"Your computing costs have spiked dramatically to ${anomaly.current_value:,.2f}, which is {abs(anomaly.deviation_percentage):.0f}% higher than your normal spending of ${anomaly.baseline_value:,.2f}. This represents significant unexpected expenses that could impact your budget.",
                Severity.HIGH: f"Computing costs have increased substantially to ${anomaly.current_value:,.2f}, exceeding your normal budget by {abs(anomaly.deviation_percentage):.0f}%. This is causing unnecessary financial waste that should be addressed.",
                Severity.MEDIUM: f"Your costs have risen to ${anomaly.current_value:,.2f}, which is {abs(anomaly.deviation_percentage):.0f}% above normal. While not critical, this represents inefficient resource usage that could be optimized.",
                Severity.LOW: "Costs are slightly elevated but within acceptable ranges. However, optimization opportunities exist to improve efficiency."
            },
            AnomalyType.RESOURCE: {
                Severity.CRITICAL: "System resources are critically overloaded. This could lead to crashes, data loss, or complete service failure. Immediate action is required to prevent system collapse.",
                Severity.HIGH: "Resources are heavily strained. The system is at risk of becoming unstable or unresponsive. Performance degradation is likely affecting users.",
                Severity.MEDIUM: "Resource usage is higher than normal. While the system is still functioning, there's reduced capacity to handle additional load or unexpected spikes.",
                Severity.LOW: "Resource usage is slightly elevated. The system is stable but could benefit from optimization to improve efficiency."
            }
        }
        
        # Get base impact description
        impact = impact_by_type.get(anomaly.anomaly_type, {}).get(
            anomaly.severity,
            "This anomaly is affecting your system's normal operation and should be investigated."
        )
        
        # Add time-based urgency
        if anomaly.severity in [Severity.CRITICAL, Severity.HIGH]:
            impact += "\n\nTime is critical: The longer this issue persists, the greater the potential for business disruption, user dissatisfaction, and financial impact."
        
        return impact
    
    def _explain_improvements(self, recommendations: List[Recommendation]) -> str:
        """Explain what improvements can be made in plain language"""
        
        if not recommendations:
            return "We're still analyzing the best course of action. Please check back shortly for specific recommendations."
        
        explanation = "Based on our analysis, here are the actions we recommend:\n\n"
        
        for i, rec in enumerate(recommendations[:4], 1):  # Top 4 recommendations
            priority_emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(rec.priority.lower(), '•')
            
            explanation += f"{priority_emoji} **{rec.priority.upper()} PRIORITY**: {rec.action}\n"
            explanation += f"   Why: {rec.rationale}\n"
            
            if rec.implementation_steps:
                explanation += f"   How to do it:\n"
                for step in rec.implementation_steps[:3]:  # Top 3 steps
                    explanation += f"   • {step}\n"
            
            if rec.estimated_effort:
                explanation += f"   Time needed: {rec.estimated_effort}\n"
            
            explanation += "\n"
        
        return explanation.strip()
    
    def _explain_benefits(self, anomaly: Anomaly, recommendations: List[Recommendation]) -> str:
        """Explain the expected benefits if improvements are implemented"""
        
        if not recommendations:
            return "Benefits will be determined once specific recommendations are available."
        
        benefits = []
        
        # Type-specific benefits
        if anomaly.anomaly_type == AnomalyType.STABILITY:
            benefits.append(
                "**Improved Reliability**: By implementing these recommendations, you can expect to significantly reduce errors "
                "and restore system stability to normal levels. This means fewer service interruptions and improved user experience."
            )
            benefits.append(
                "**Reduced Downtime**: Proactive fixes will help prevent potential outages, reducing downtime and "
                "the associated costs of lost productivity and revenue."
            )
        
        elif anomaly.anomaly_type == AnomalyType.PERFORMANCE:
            # Only provide specific numbers for baseline (which is certain)
            benefits.append(
                f"**Faster Response Times**: These optimizations will help bring response times back toward "
                f"normal levels (baseline: {anomaly.baseline_value:.0f}ms). The exact improvement will depend on "
                f"implementation and system conditions."
            )
            benefits.append(
                "**Better User Experience**: Faster systems lead to higher user satisfaction and increased engagement. "
                "Performance improvements typically result in better business outcomes."
            )
        
        elif anomaly.anomaly_type == AnomalyType.COST:
            # Cost can be calculated with certainty - provide specific numbers
            excess_cost = anomaly.current_value - anomaly.baseline_value
            monthly_savings = excess_cost * 30  # Approximate monthly
            
            benefits.append(
                f"**Quantifiable Cost Savings**: By right-sizing resources and eliminating waste, you can save "
                f"**${excess_cost:,.2f} per day** (approximately **${monthly_savings:,.2f} per month**). "
                f"This is based on returning to your baseline cost of ${anomaly.baseline_value:,.2f}."
            )
            
            # Check if any recommendation mentions performance impact
            has_performance_note = any('performance' in rec.cost_impact.lower() if rec.cost_impact else False for rec in recommendations)
            
            if has_performance_note:
                benefits.append(
                    "**No Performance Trade-off**: Our analysis shows that these cost optimizations can be implemented "
                    "without negatively impacting system performance. You'll save money while maintaining the same level of service."
                )
            else:
                benefits.append(
                    "**Improved Efficiency**: These changes will optimize resource usage, reducing waste while maintaining "
                    "or improving system performance."
                )
        
        elif anomaly.anomaly_type == AnomalyType.RESOURCE:
            benefits.append(
                "**Better Resource Utilization**: Optimizing resource usage will free up capacity for growth, improve system "
                "stability, and reduce the risk of resource-related failures."
            )
            # Don't provide specific percentage for cost savings - it's uncertain
            benefits.append(
                "**Cost Efficiency**: Better resource management will lead to cost savings while improving "
                "overall system performance and reliability. Specific savings will depend on implementation."
            )
        
        # Add timeline benefit
        if anomaly.severity in [Severity.CRITICAL, Severity.HIGH]:
            benefits.append(
                "**Quick Wins**: Many of these improvements can be implemented quickly (within hours to days) and will "
                "show immediate positive results."
            )
        
        # Add long-term benefit
        benefits.append(
            "**Long-term Stability**: Addressing this issue now prevents it from recurring and establishes better "
            "practices for system health monitoring and maintenance."
        )
        
        return "\n\n".join(benefits)
    
    
    def _query_historical_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Query historical metric data
        """
        # Placeholder - implement actual BigQuery query
        return []
    
    def _query_related_metrics(self, anomaly: Anomaly) -> Dict[str, float]:
        """
        Query metrics related to the anomaly
        """
        # Placeholder - implement actual BigQuery query
        return {}
    
    def _query_recent_changes(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Query recent system changes or migrations from BigQuery
        
        Checks the migrations table for:
        - User migrations (additional users added)
        - Functionality changes (new features requiring resources)
        - Configuration changes
        - Deployment events
        """
        try:
            query = f"""
            SELECT
                migration_id,
                migration_type,
                migration_timestamp,
                source_system,
                target_system,
                user_count_change,
                resource_requirements,
                description,
                status
            FROM `{self.config.bigquery_project_id}.hackaton.migrations`
            WHERE migration_timestamp BETWEEN @start_time AND @end_time
            ORDER BY migration_timestamp DESC
            LIMIT 50
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
                    bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time),
                ]
            )
            
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            migrations = []
            for row in results:
                migration = {
                    'migration_id': row.migration_id,
                    'type': row.migration_type,
                    'timestamp': row.migration_timestamp,
                    'source': row.source_system,
                    'target': row.target_system,
                    'user_count_change': row.user_count_change if hasattr(row, 'user_count_change') else 0,
                    'resource_requirements': row.resource_requirements if hasattr(row, 'resource_requirements') else {},
                    'description': row.description if hasattr(row, 'description') else '',
                    'status': row.status
                }
                migrations.append(migration)
            
            logger.info(f"Found {len(migrations)} recent migrations/changes")
            return migrations
            
        except Exception as e:
            logger.warning(f"Failed to query migrations: {e}")
            return []
    
    def _analyze_migration_impact(
        self,
        anomaly: Anomaly,
        migrations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze if recent migrations caused or contributed to the anomaly
        
        Returns:
            Dictionary with migration analysis including:
            - likely_cause: bool - if migration likely caused the anomaly
            - related_migrations: List of relevant migrations
            - impact_summary: str - explanation of migration impact
        """
        if not migrations:
            return {
                'likely_cause': False,
                'related_migrations': [],
                'impact_summary': 'No recent migrations detected'
            }
        
        related_migrations = []
        impact_factors = []
        
        for migration in migrations:
            # Check if migration timing correlates with anomaly
            time_diff = (anomaly.detected_at - migration['timestamp']).total_seconds() / 3600  # hours
            
            if time_diff < 0 or time_diff > 24:  # Only consider migrations within 24h before anomaly
                continue
            
            # Analyze migration type and impact
            migration_impact = {
                'migration': migration,
                'time_before_anomaly_hours': time_diff,
                'potential_impact': []
            }
            
            # Check for user count changes
            if migration.get('user_count_change', 0) > 0:
                user_increase = migration['user_count_change']
                migration_impact['potential_impact'].append(
                    f"Added {user_increase} users, increasing system load"
                )
                impact_factors.append(f"User migration added {user_increase} users {time_diff:.1f}h before anomaly")
            
            # Check for functionality changes
            if 'functionality' in migration.get('type', '').lower() or 'feature' in migration.get('type', '').lower():
                migration_impact['potential_impact'].append(
                    "New functionality may require additional resources"
                )
                impact_factors.append(f"New functionality deployed {time_diff:.1f}h before anomaly")
            
            # Check resource requirements
            resource_reqs = migration.get('resource_requirements', {})
            if resource_reqs:
                if resource_reqs.get('cpu_increase'):
                    migration_impact['potential_impact'].append(
                        f"Requires {resource_reqs['cpu_increase']}% more CPU"
                    )
                if resource_reqs.get('memory_increase'):
                    migration_impact['potential_impact'].append(
                        f"Requires {resource_reqs['memory_increase']}% more memory"
                    )
                impact_factors.append(f"Resource requirements changed {time_diff:.1f}h before anomaly")
            
            if migration_impact['potential_impact']:
                related_migrations.append(migration_impact)
        
        # Determine if migrations are likely cause
        likely_cause = len(related_migrations) > 0 and any(
            m['time_before_anomaly_hours'] < 6 for m in related_migrations
        )
        
        # Generate impact summary
        if not related_migrations:
            impact_summary = "No migrations found that correlate with the anomaly timing."
        elif likely_cause:
            impact_summary = (
                f"Found {len(related_migrations)} recent migration(s) that likely contributed to this anomaly. "
                f"The migration(s) occurred shortly before the anomaly was detected and involved changes that "
                f"could explain the observed behavior: {'; '.join(impact_factors[:3])}"
            )
        else:
            impact_summary = (
                f"Found {len(related_migrations)} migration(s) in the time window, but timing suggests "
                f"they may not be the primary cause. However, they should be considered as potential "
                f"contributing factors."
            )
        
        return {
            'likely_cause': likely_cause,
            'related_migrations': related_migrations,
            'impact_summary': impact_summary,
            'impact_factors': impact_factors
        }
    
    def _summarize_historical_data(self, data: List[Dict[str, Any]]) -> str:
        """
        Summarize historical data
        """
        if not data:
            return "No historical data available"
        return f"Historical data shows {len(data)} data points"
    
    def _analyze_trend(self, data: List[Dict[str, Any]]) -> str:
        """
        Analyze trend in historical data
        """
        if not data:
            return "Insufficient data for trend analysis"
        return "Trend analysis pending"
    
    def _save_analysis(self, analysis: AnomalyAnalysis):
        """
        Save analysis results to BigQuery with user feedback tracking
        
        Saves to: ccibt-hack25ww7-730.hackaton.anomaly_analysis
        
        This table includes:
        - Complete analysis results
        - User feedback fields (is_false_positive, reviewed_by, review_notes)
        - Reliability tracking (feedback helps improve future analysis)
        """
        try:
            import uuid
            
            # Generate unique analysis ID
            analysis_id = str(uuid.uuid4())
            
            # Prepare data for BigQuery
            row = {
                'analysis_id': analysis_id,
                'anomaly_id': analysis.anomaly.anomaly_id,
                'analyzed_at': analysis.analyzed_at.isoformat(),
                
                # Anomaly details
                'anomaly_detected_at': analysis.anomaly.detected_at.isoformat(),
                'metric_name': analysis.anomaly.metric_name,
                'metric_type': analysis.anomaly.metric_type,
                'current_value': analysis.anomaly.current_value,
                'baseline_value': analysis.anomaly.baseline_value,
                'deviation_sigma': analysis.anomaly.deviation_sigma,
                'deviation_percentage': analysis.anomaly.deviation_percentage,
                'anomaly_type': analysis.anomaly.anomaly_type.value,
                'severity': analysis.anomaly.severity.value,
                'confidence': analysis.anomaly.confidence,
                
                # Root cause
                'root_cause_primary': analysis.root_cause.primary_cause,
                'root_cause_factors': analysis.root_cause.contributing_factors,
                'root_cause_confidence': analysis.root_cause.confidence,
                'root_cause_evidence': analysis.root_cause.evidence,
                
                # Recommendations (JSON)
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
                    for rec in analysis.recommendations
                ],
                
                # Human-readable summary
                'summary_what_happened': analysis.summary.what_happened if analysis.summary else None,
                'summary_why_happened': analysis.summary.why_it_happened if analysis.summary else None,
                'summary_impact': analysis.summary.what_is_the_impact if analysis.summary else None,
                'summary_improvements': analysis.summary.what_improvements_can_be_made if analysis.summary else None,
                'summary_benefits': analysis.summary.estimated_benefit_if_implemented if analysis.summary else None,
                
                # Analysis metadata
                'ai_model_used': analysis.ai_model_used,
                'analysis_duration_ms': analysis.analysis_duration_ms,
                
                # Migration context
                'migration_detected': analysis.root_cause.correlation_data.get('migration_analysis', {}).get('likely_cause', False),
                'migration_summary': analysis.root_cause.correlation_data.get('migration_analysis', {}).get('impact_summary'),
                
                # User feedback fields (initially null)
                'is_false_positive': None,  # User will set to True/False
                'reviewed_by': None,  # User email/ID
                'reviewed_at': None,  # Timestamp of review
                'review_notes': None,  # User comments
                'feedback_category': None,  # Why false positive: 'expected_behavior', 'incorrect_baseline', 'data_quality', 'other'
                
                # Reliability tracking
                'notified': False,  # Has notification been sent
                'notification_attempts': 0
            }
            
            # Insert into BigQuery
            table_id = f"{self.config.bigquery_project_id}.hackaton.anomaly_analysis"
            errors = self.bigquery_client.insert_rows_json(table_id, [row])
            
            if errors:
                logger.error(f"Failed to insert analysis into BigQuery: {errors}")
            else:
                logger.info(f"Analysis saved to BigQuery: {analysis_id}")
                logger.info(f"Anomaly ID: {analysis.anomaly.anomaly_id}")
                
        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")
            # Don't raise - analysis should continue even if save fails
    
    def get_false_positive_rate(self, days: int = 30) -> Dict[str, Any]:
        """
        Calculate false positive rate based on user feedback
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with false positive statistics
        """
        try:
            query = f"""
            SELECT
                COUNT(*) as total_analyses,
                COUNTIF(is_false_positive = TRUE) as false_positives,
                COUNTIF(is_false_positive = FALSE) as true_positives,
                COUNTIF(is_false_positive IS NULL) as not_reviewed,
                SAFE_DIVIDE(COUNTIF(is_false_positive = TRUE),
                           COUNTIF(is_false_positive IS NOT NULL)) as false_positive_rate,
                
                -- By anomaly type
                COUNTIF(is_false_positive = TRUE AND anomaly_type = 'stability') as fp_stability,
                COUNTIF(is_false_positive = TRUE AND anomaly_type = 'performance') as fp_performance,
                COUNTIF(is_false_positive = TRUE AND anomaly_type = 'cost') as fp_cost,
                
                -- By severity
                COUNTIF(is_false_positive = TRUE AND severity = 'critical') as fp_critical,
                COUNTIF(is_false_positive = TRUE AND severity = 'high') as fp_high,
                COUNTIF(is_false_positive = TRUE AND severity = 'medium') as fp_medium
                
            FROM `{self.config.bigquery_project_id}.hackaton.anomaly_analysis`
            WHERE analyzed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
            """
            
            query_job = self.bigquery_client.query(query)
            results = list(query_job.result())
            
            if results:
                row = results[0]
                return {
                    'total_analyses': row.total_analyses,
                    'false_positives': row.false_positives,
                    'true_positives': row.true_positives,
                    'not_reviewed': row.not_reviewed,
                    'false_positive_rate': row.false_positive_rate or 0.0,
                    'reliability_score': 1.0 - (row.false_positive_rate or 0.0),
                    'by_type': {
                        'stability': row.fp_stability,
                        'performance': row.fp_performance,
                        'cost': row.fp_cost
                    },
                    'by_severity': {
                        'critical': row.fp_critical,
                        'high': row.fp_high,
                        'medium': row.fp_medium
                    }
                }
            
            return {'error': 'No data available'}
            
        except Exception as e:
            logger.error(f"Failed to calculate false positive rate: {e}")
            return {'error': str(e)}


if __name__ == "__main__":
    # Test the agent
    from ..models.anomaly import Anomaly, AnomalyType, Severity
    
    # Create test anomaly
    test_anomaly = Anomaly(
        anomaly_id="test-001",
        detected_at=datetime.now(),
        metric_name="error_rate",
        metric_type="Error_Rate _%_",
        current_value=45.0,
        baseline_value=22.8,
        deviation_sigma=5.3,
        deviation_percentage=97.4,
        anomaly_type=AnomalyType.STABILITY,
        severity=Severity.CRITICAL,
        confidence=0.95
    )
    
    # Analyze
    agent = AnomalyAnalyzerAgent()
    analysis = agent.analyze_anomaly(test_anomaly)
    
    print("\n" + "=" * 80)
    print("ANOMALY ANALYSIS RESULT")
    print("=" * 80)
    print(json.dumps(analysis.to_dict(), indent=2))