import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from neonhub.services.sequence_manager import SequenceManager
from neonhub.schemas.lead_state import LeadState, LeadStatus, SequenceStage

@pytest.fixture
def sequence_manager():
    return SequenceManager()

@pytest.fixture
def sample_sequence():
    return {
        "stages": [
            {
                "id": "intro",
                "template_id": "demo_outreach_email",
                "delay_hours": 24,
                "max_attempts": 3
            },
            {
                "id": "follow_up",
                "template_id": "follow_up_email",
                "delay_hours": 48,
                "max_attempts": 2
            },
            {
                "id": "case_study",
                "template_id": "case_study_email",
                "delay_hours": 72,
                "max_attempts": 1
            }
        ]
    }

@pytest.fixture
def sample_lead():
    return {
        "id": "lead_123",
        "email": "test@example.com",
        "first_name": "John",
        "company_name": "Test Corp"
    }

@pytest.mark.asyncio
async def test_initialize_lead_sequence(sequence_manager, sample_sequence, sample_lead):
    """Test initializing a lead's sequence."""
    state = await sequence_manager.initialize_lead_sequence(
        sample_lead["id"],
        "campaign_1",
        sample_sequence
    )
    
    assert state.lead_id == sample_lead["id"]
    assert state.campaign_id == "campaign_1"
    assert state.status == LeadStatus.ACTIVE
    assert len(state.sequence_stages) == 3
    assert state.current_stage == 0
    
@pytest.mark.asyncio
async def test_get_next_action(sequence_manager, sample_sequence, sample_lead):
    """Test getting the next action for a lead."""
    # Initialize sequence
    await sequence_manager.initialize_lead_sequence(
        sample_lead["id"],
        "campaign_1",
        sample_sequence
    )
    
    # Get first action
    action = await sequence_manager.get_next_action(
        sample_lead["id"],
        "campaign_1"
    )
    
    assert action is not None
    assert action["stage_id"] == "intro"
    assert action["template_id"] == "demo_outreach_email"
    assert "content" in action
    assert "metadata" in action
    
@pytest.mark.asyncio
async def test_complete_stage(sequence_manager, sample_sequence, sample_lead):
    """Test completing a sequence stage."""
    # Initialize sequence
    await sequence_manager.initialize_lead_sequence(
        sample_lead["id"],
        "campaign_1",
        sample_sequence
    )
    
    # Complete first stage
    await sequence_manager.complete_stage(
        sample_lead["id"],
        "campaign_1",
        success=True
    )
    
    # Get next action
    action = await sequence_manager.get_next_action(
        sample_lead["id"],
        "campaign_1"
    )
    
    assert action is not None
    assert action["stage_id"] == "follow_up"
    assert action["template_id"] == "follow_up_email"
    
@pytest.mark.asyncio
async def test_stage_delay(sequence_manager, sample_sequence, sample_lead):
    """Test stage delay functionality."""
    # Initialize sequence
    await sequence_manager.initialize_lead_sequence(
        sample_lead["id"],
        "campaign_1",
        sample_sequence
    )
    
    # Complete first stage
    await sequence_manager.complete_stage(
        sample_lead["id"],
        "campaign_1",
        success=True
    )
    
    # Try to get next action immediately
    action = await sequence_manager.get_next_action(
        sample_lead["id"],
        "campaign_1"
    )
    
    assert action is None  # Should be None due to delay
    
@pytest.mark.asyncio
async def test_pause_resume_sequence(sequence_manager, sample_sequence, sample_lead):
    """Test pausing and resuming a sequence."""
    # Initialize sequence
    await sequence_manager.initialize_lead_sequence(
        sample_lead["id"],
        "campaign_1",
        sample_sequence
    )
    
    # Pause sequence
    await sequence_manager.pause_sequence(sample_lead["id"])
    
    # Try to get next action
    action = await sequence_manager.get_next_action(
        sample_lead["id"],
        "campaign_1"
    )
    
    assert action is None  # Should be None due to paused status
    
    # Resume sequence
    await sequence_manager.resume_sequence(sample_lead["id"])
    
    # Get next action
    action = await sequence_manager.get_next_action(
        sample_lead["id"],
        "campaign_1"
    )
    
    assert action is not None  # Should work after resume
    
@pytest.mark.asyncio
async def test_terminate_sequence(sequence_manager, sample_sequence, sample_lead):
    """Test terminating a sequence."""
    # Initialize sequence
    await sequence_manager.initialize_lead_sequence(
        sample_lead["id"],
        "campaign_1",
        sample_sequence
    )
    
    # Terminate sequence
    await sequence_manager.terminate_sequence(
        sample_lead["id"],
        reason="unsubscribe"
    )
    
    # Try to get next action
    action = await sequence_manager.get_next_action(
        sample_lead["id"],
        "campaign_1"
    )
    
    assert action is None  # Should be None due to terminated status
    
@pytest.mark.asyncio
async def test_max_attempts(sequence_manager, sample_sequence, sample_lead):
    """Test max attempts functionality."""
    # Initialize sequence
    await sequence_manager.initialize_lead_sequence(
        sample_lead["id"],
        "campaign_1",
        sample_sequence
    )
    
    # Fail first stage multiple times
    for _ in range(3):
        await sequence_manager.complete_stage(
            sample_lead["id"],
            "campaign_1",
            success=False
        )
    
    # Try to get next action
    action = await sequence_manager.get_next_action(
        sample_lead["id"],
        "campaign_1"
    )
    
    assert action is None  # Should be None due to max attempts reached
    
@pytest.mark.asyncio
async def test_sequence_completion(sequence_manager, sample_sequence, sample_lead):
    """Test sequence completion."""
    # Initialize sequence
    await sequence_manager.initialize_lead_sequence(
        sample_lead["id"],
        "campaign_1",
        sample_sequence
    )
    
    # Complete all stages
    for _ in range(3):
        await sequence_manager.complete_stage(
            sample_lead["id"],
            "campaign_1",
            success=True
        )
    
    # Try to get next action
    action = await sequence_manager.get_next_action(
        sample_lead["id"],
        "campaign_1"
    )
    
    assert action is None  # Should be None due to completed sequence 