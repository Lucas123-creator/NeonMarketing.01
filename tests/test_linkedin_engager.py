import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from neonhub.agents.linkedin_engager import LinkedInEngager
from neonhub.schemas.linkedin_lead import LinkedInProfile, ConnectionStatus, MessageStatus

@pytest.fixture
def linkedin_engager():
    return LinkedInEngager()

@pytest.fixture
def sample_profile():
    return LinkedInProfile(
        profile_id="profile_123",
        name="John Doe",
        title="Software Engineer",
        company="Tech Corp",
        profile_url="https://linkedin.com/in/johndoe"
    )

@pytest.mark.asyncio
async def test_send_connection_request(linkedin_engager, sample_profile):
    """Test sending a connection request."""
    with patch("requests.post") as mock_post:
        # Mock PhantomBuster response
        mock_post.return_value.status_code = 200
        
        # Send connection request
        success = await linkedin_engager.send_connection_request(sample_profile)
        
        assert success is True
        assert sample_profile.connection_status == ConnectionStatus.PENDING
        assert sample_profile.connection_request_sent_at is not None
        
@pytest.mark.asyncio
async def test_send_message(linkedin_engager, sample_profile):
    """Test sending a message."""
    # Set profile as connected
    sample_profile.update_connection_status(ConnectionStatus.CONNECTED)
    
    with patch("requests.post") as mock_post:
        # Mock PhantomBuster response
        mock_post.return_value.status_code = 200
        
        # Send message
        success = await linkedin_engager.send_message(
            sample_profile,
            content="Hello!"
        )
        
        assert success is True
        assert len(sample_profile.messages) == 1
        assert sample_profile.messages[0].content == "Hello!"
        assert sample_profile.messages[0].status == MessageStatus.SENT
        
@pytest.mark.asyncio
async def test_check_messages(linkedin_engager, sample_profile):
    """Test checking for message replies."""
    # Add a sent message
    message = sample_profile.add_message("Hello!")
    message.status = MessageStatus.SENT
    
    with patch("requests.post") as mock_post:
        # Mock PhantomBuster response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "replies": {
                message.message_id: {
                    "content": "Hi there!",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        }
        
        # Check messages
        await linkedin_engager.check_messages(sample_profile)
        
        assert message.status == MessageStatus.REPLIED
        assert message.reply_content == "Hi there!"
        assert message.reply_at is not None
        
@pytest.mark.asyncio
async def test_retry_failed_actions(linkedin_engager, sample_profile):
    """Test retrying failed actions."""
    # Set up failed connection request
    sample_profile.update_connection_status(ConnectionStatus.PENDING)
    sample_profile.connection_request_sent_at = datetime.utcnow() - timedelta(hours=25)
    
    # Set up failed message
    message = sample_profile.add_message("Hello!")
    message.status = MessageStatus.FAILED
    message.sent_at = datetime.utcnow() - timedelta(hours=13)
    
    with patch.object(linkedin_engager, "send_connection_request") as mock_connect:
        with patch.object(linkedin_engager, "send_message") as mock_message:
            # Retry failed actions
            await linkedin_engager.retry_failed_actions(sample_profile)
            
            # Check that retries were attempted
            mock_connect.assert_called_once()
            mock_message.assert_called_once()
            
@pytest.mark.asyncio
async def test_rate_limiting(linkedin_engager, sample_profile):
    """Test rate limiting for connections and messages."""
    # Test connection rate limit
    with patch.object(linkedin_engager, "_check_connection_limits") as mock_check:
        mock_check.return_value = False
        
        success = await linkedin_engager.send_connection_request(sample_profile)
        assert success is False
        
    # Test message rate limit
    sample_profile.update_connection_status(ConnectionStatus.CONNECTED)
    
    with patch.object(linkedin_engager, "_check_message_limits") as mock_check:
        mock_check.return_value = False
        
        success = await linkedin_engager.send_message(sample_profile, "Hello!")
        assert success is False
        
@pytest.mark.asyncio
async def test_error_handling(linkedin_engager, sample_profile):
    """Test error handling in engagement operations."""
    with patch("requests.post") as mock_post:
        # Mock API error
        mock_post.side_effect = Exception("API Error")
        
        # Test connection request error
        success = await linkedin_engager.send_connection_request(sample_profile)
        assert success is False
        
        # Test message error
        sample_profile.update_connection_status(ConnectionStatus.CONNECTED)
        success = await linkedin_engager.send_message(sample_profile, "Hello!")
        assert success is False
        
@pytest.mark.asyncio
async def test_metrics_tracking(linkedin_engager, sample_profile):
    """Test that metrics are properly tracked."""
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        
        # Send connection request
        await linkedin_engager.send_connection_request(sample_profile)
        assert linkedin_engager.CONNECTIONS_SENT._value.get(("success",)) == 1
        
        # Send message
        sample_profile.update_connection_status(ConnectionStatus.CONNECTED)
        await linkedin_engager.send_message(sample_profile, "Hello!")
        assert linkedin_engager.MESSAGES_SENT._value.get(("success",)) == 1
        
        # Check for replies
        message = sample_profile.messages[0]
        mock_post.return_value.json.return_value = {
            "replies": {
                message.message_id: {
                    "content": "Hi!",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        }
        await linkedin_engager.check_messages(sample_profile)
        assert linkedin_engager.REPLIES_RECEIVED._value.get() == 1 