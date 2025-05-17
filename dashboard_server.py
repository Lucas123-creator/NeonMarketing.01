from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
from datetime import datetime
import csv
import io
import time
import psutil

from monitoring.agent_status_tracker import AgentStatusTracker
from monitoring.metrics_collector import MetricsCollector
from monitoring.log_viewer import LogViewer
from neonhub.services.engagement_tracker import EngagementTracker
from neonhub.schemas.lead_state import LeadState
from analytics.growth_insights import GrowthInsights

app = FastAPI(title="NeonHub Dashboard API")

agent_status_tracker = AgentStatusTracker()
metrics_collector = MetricsCollector()
log_viewer = LogViewer()
engagement_tracker = EngagementTracker()
growth_insights = GrowthInsights()

app_start_time = time.time()

@app.get("/status/agents")
def get_agent_status():
    return agent_status_tracker.get_all_statuses()

@app.get("/status/agents/high-error")
def get_high_error_agents(threshold: int = 3):
    return agent_status_tracker.get_high_error_agents(threshold)

@app.get("/metrics/email")
def get_email_metrics():
    return metrics_collector.summarize_email_metrics()

@app.get("/metrics/linkedin")
def get_linkedin_metrics():
    return metrics_collector.summarize_linkedin_metrics()

@app.get("/metrics/content")
def get_content_metrics():
    # Wrap in dict for UI compatibility
    return {"top_templates": metrics_collector.summarize_content_metrics()}

@app.get("/sequences/{lead_id}")
def get_lead_sequence(lead_id: str):
    state = engagement_tracker.get_lead_state(lead_id)
    if not state:
        raise HTTPException(status_code=404, detail="Lead not found")
    return state.dict()

@app.get("/logs")
def get_logs(
    agent_id: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'since' format. Use ISO8601.")
    logs = log_viewer.get_logs(agent_id=agent_id, level=level, since=since_dt, limit=limit)
    return logs

@app.get("/insights/top-performing-templates")
def get_top_templates():
    # Placeholder: In production, aggregate from content metrics
    return {"top_templates": []}

@app.get("/export/leads.csv")
def export_leads_csv():
    # Example: Export all lead states as CSV
    # In production, this would pull from a DB or persistent store
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["lead_id", "campaign_id", "engagement_score", "status", "last_touch"])
    # For demo, scan a directory or use a mock
    # Here, we just return an empty CSV
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"}
    )

@app.get("/growth/ugc")
def get_growth_ugc(limit: int = 20):
    # Wrap in dict for UI compatibility
    return {"ugc_feed": growth_insights.get_ugc_feed(limit=limit)}

@app.get("/growth/influencers")
def get_growth_influencers(limit: int = 20):
    # Wrap in dict for UI compatibility
    return {"influencers": growth_insights.get_influencers(limit=limit)}

@app.get("/growth/referrals")
def get_growth_referrals(limit: int = 20):
    # Wrap in dict for UI compatibility
    return {"referrals": growth_insights.get_referrals(limit=limit)}

@app.get("/growth/top-content")
def get_growth_top_content(limit: int = 10):
    return growth_insights.get_top_content(limit=limit)

@app.get("/health")
def health():
    return {"status": "ok", "uptime_seconds": int(time.time() - app_start_time)}

@app.get("/uptime")
def uptime():
    return {"uptime_seconds": int(time.time() - app_start_time)}

@app.get("/metrics/full")
def metrics_full():
    process = psutil.Process()
    mem = process.memory_info()
    cpu = process.cpu_percent(interval=0.1)
    return JSONResponse({
        "status": "ok",
        "uptime_seconds": int(time.time() - app_start_time),
        "memory_mb": mem.rss // 1024 // 1024,
        "cpu_percent": cpu,
        # Add queue lengths, agent status, etc. as needed
    }) 