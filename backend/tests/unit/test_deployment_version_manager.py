"""Unit tests for Deployment Version Manager and Rollback."""

import pytest
from backend.app.services.deployment_version_manager import deployment_version_manager


def test_deployment_registration_and_versioning():
    """Test registering deployments and generating semantic versions."""
    d1 = deployment_version_manager.register_deployment(
        name="release-1",
        model_version_id="qwen2.5-0.5b-instruct",
        configuration={"thread_count": 4, "batch_size": 16},
    )
    assert d1["id"] is not None
    assert d1["deployment_version"].startswith("v1.0.")
    assert d1["config_version"].startswith("cfg-")

    d2 = deployment_version_manager.register_deployment(
        name="release-2",
        model_version_id="qwen2.5-0.5b-instruct",
        configuration={"thread_count": 8, "batch_size": 32},
    )
    assert d2["deployment_version"] != d1["deployment_version"]


def test_promotion_and_rollback():
    """Test promoting deployments and performing rollback to previous working release."""
    d1 = deployment_version_manager.register_deployment(
        name="rel-1",
        model_version_id="qwen2.5-0.5b-instruct",
        configuration={"thread_count": 4},
    )
    deployment_version_manager.promote_to_active(d1["id"])

    active_1 = deployment_version_manager.get_active_deployment()
    assert active_1["id"] == d1["id"]
    assert active_1["is_active"] is True

    d2 = deployment_version_manager.register_deployment(
        name="rel-2",
        model_version_id="qwen2.5-0.5b-instruct",
        configuration={"thread_count": 8},
    )
    deployment_version_manager.promote_to_active(d2["id"])

    active_2 = deployment_version_manager.get_active_deployment()
    assert active_2["id"] == d2["id"]

    # Execute Rollback
    restored, curr = deployment_version_manager.execute_rollback(
        current_deployment_id=d2["id"], reason="Test rollback"
    )
    assert restored["id"] == d1["id"]
    assert curr["id"] == d2["id"]
    assert curr["status"] == "ROLLED_BACK"
    assert restored["is_active"] is True

    # Audit events check
    events = deployment_version_manager.list_events_for_deployment(curr["id"])
    assert any(ev["event_type"] == "ROLLBACK" for ev in events)
