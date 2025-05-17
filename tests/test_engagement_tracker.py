import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import json
from pathlib import Path

from neonhub.services.engagement_tracker import EngagementTracker
from neonhub.schemas.lead_state import LeadState, LeadStatus, SequenceStage

@pytest.fixture
def engagement_tracker():
    return EngagementTracker()

@pytest.fixture
def sample_lead_state():
    return LeadState(
        lead_id="lead_123",
        campaign_id="campaign_1",
        sequence_stages=[
            SequenceStage(
                stage_id="intro",
                template_id="demo_outreach_email",
                delay_hours=24
            )
        ]
    )

@pytest.mark.asyncio
async def test_track_event(engagement_tracker, sample_lead_state):
    """Test tracking an engagement event."""
    # Save initial state
    engagement_tracker.save_lead_state(sample_lead_state)
    
    # Track email open event
    await engagement_tracker.track_event(
        sample_lead_state.lead_id,
        "email_open",
        {"campaign_id": sample_lead_state.campaign_id}
    )
    
    # Get updated state
    updated_state = engagement_tracker.get_lead_state(sample_lead_state.lead_id)
    
    assert updated_state is not None
    assert updated_state.engagement_score == 1  # email_open = +1
    assert len(updated_state.engagement_history) == 1
    assert updated_state.engagement_history[0].event_type == "email_open"
    
@pytest.mark.asyncio
async def test_multiple_events(engagement_tracker, sample_lead_state):
    """Test tracking multiple engagement events."""
    # Save initial state
    engagement_tracker.save_lead_state(sample_lead_state)
    
    # Track multiple events
    events = [
        ("email_open", 1),
        ("email_click", 3),
        ("email_reply", 5)
    ]
    
    for event_type, score_delta in events:
        await engagement_tracker.track_event(
            sample_lead_state.lead_id,
            event_type,
            {"campaign_id": sample_lead_state.campaign_id}
        )
    
    # Get updated state
    updated_state = engagement_tracker.get_lead_state(sample_lead_state.lead_id)
    
    assert updated_state is not None
    assert updated_state.engagement_score == 9  # 1 + 3 + 5
    assert len(updated_state.engagement_history) == 3
    
@pytest.mark.asyncio
async def test_negative_events(engagement_tracker, sample_lead_state):
    """Test tracking negative engagement events."""
    # Save initial state
    engagement_tracker.save_lead_state(sample_lead_state)
    
    # Track positive then negative event
    await engagement_tracker.track_event(
        sample_lead_state.lead_id,
        "email_open",
        {"campaign_id": sample_lead_state.campaign_id}
    )
    
    await engagement_tracker.track_event(
        sample_lead_state.lead_id,
        "unsubscribe",
        {"campaign_id": sample_lead_state.campaign_id}
    )
    
    # Get updated state
    updated_state = engagement_tracker.get_lead_state(sample_lead_state.lead_id)
    
    assert updated_state is not None
    assert updated_state.engagement_score == -9  # 1 - 10
    assert len(updated_state.engagement_history) == 2
    
@pytest.mark.asyncio
async def test_should_pause_lead(engagement_tracker, sample_lead_state):
    """Test lead pausing based on engagement score."""
    # Save initial state
    engagement_tracker.save_lead_state(sample_lead_state)
    
    # Track negative events
    await engagement_tracker.track_event(
        sample_lead_state.lead_id,
        "unsubscribe",
        {"campaign_id": sample_lead_state.campaign_id}
    )
    
    # Check if should pause
    should_pause = await engagement_tracker.should_pause_lead(
        sample_lead_state.lead_id,
        min_score=0
    )
    
    assert should_pause is True
    
@pytest.mark.asyncio
async def test_get_engagement_history(engagement_tracker, sample_lead_state):
    """Test retrieving engagement history."""
    # Save initial state
    engagement_tracker.save_lead_state(sample_lead_state)
    
    # Track multiple events
    events = ["email_open", "email_click", "email_reply"]
    for event_type in events:
        await engagement_tracker.track_event(
            sample_lead_state.lead_id,
            event_type,
            {"campaign_id": sample_lead_state.campaign_id}
        )
    
    # Get history
    history = await engagement_tracker.get_engagement_history(sample_lead_state.lead_id)
    
    assert len(history) == 3
    assert [event["event_type"] for event in history] == events
    
@pytest.mark.asyncio
async def test_reset_lead_score(engagement_tracker, sample_lead_state):
    """Test resetting a lead's engagement score."""
    # Save initial state
    engagement_tracker.save_lead_state(sample_lead_state)
    
    # Track some events
    await engagement_tracker.track_event(
        sample_lead_state.lead_id,
        "email_open",
        {"campaign_id": sample_lead_state.campaign_id}
    )
    
    # Reset score
    await engagement_tracker.reset_lead_score(sample_lead_state.lead_id)
    
    # Get updated state
    updated_state = engagement_tracker.get_lead_state(sample_lead_state.lead_id)
    
    assert updated_state is not None
    assert updated_state.engagement_score == 0
    assert len(updated_state.engagement_history) == 0
    
@pytest.mark.asyncio
async def test_invalid_lead(engagement_tracker):
    """Test handling of invalid lead IDs."""
    # Try to track event for non-existent lead
    await engagement_tracker.track_event(
        "non_existent_lead",
        "email_open",
        {"campaign_id": "campaign_1"}
    )
    
    # Try to get score for non-existent lead
    score = await engagement_tracker.get_lead_score("non_existent_lead")
    assert score == 0
    
    # Try to get history for non-existent lead
    history = await engagement_tracker.get_engagement_history("non_existent_lead")
    assert history == []
    
@pytest.mark.asyncio
async def test_metrics_tracking(engagement_tracker, sample_lead_state):
    """Test that metrics are properly updated."""
    # Save initial state
    engagement_tracker.save_lead_state(sample_lead_state)
    
    # Track event
    await engagement_tracker.track_event(
        sample_lead_state.lead_id,
        "email_open",
        {"campaign_id": sample_lead_state.campaign_id}
    )
    
    # Get updated state
    updated_state = engagement_tracker.get_lead_state(sample_lead_state.lead_id)
    
    assert updated_state is not None
    assert updated_state.engagement_score == 1
    
    # Check that metrics were updated
    assert engagement_tracker.ENGAGEMENT_EVENTS._value.get(("email_open",)) == 1 