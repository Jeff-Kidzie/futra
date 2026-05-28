"""Tests for /api/alerts endpoint."""
import pytest
from python.dashboard.db import get_db


class TestAlerts:
    """GET /api/alerts and POST /api/alerts/{id}/acknowledge."""

    def test_returns_alerts(self, client, auth_headers, test_db):
        """Test 11: Returns alerts from SQLite alerts table."""
        test_db.execute(
            "INSERT INTO alerts (type, message, severity) VALUES (?, ?, ?)",
            ("drawdown", "Drawdown 5.2%", "warning"),
        )
        test_db.execute(
            "INSERT INTO alerts (type, message, severity) VALUES (?, ?, ?)",
            ("connection_lost", "MT5 disconnected", "critical"),
        )
        test_db.commit()

        response = client.get("/api/alerts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_alerts_ordered_by_created_at(self, client, auth_headers, test_db):
        """Alerts are returned in created_at DESC order."""
        test_db.execute(
            "INSERT INTO alerts (type, message, severity, created_at) VALUES (?, ?, ?, ?)",
            ("test", "older", "info", "2026-01-01T00:00:00"),
        )
        test_db.execute(
            "INSERT INTO alerts (type, message, severity, created_at) VALUES (?, ?, ?, ?)",
            ("test", "newer", "info", "2026-05-26T00:00:00"),
        )
        test_db.commit()

        response = client.get("/api/alerts", headers=auth_headers)
        data = response.json()
        assert data[0]["message"] == "newer"

    def test_filter_by_acknowledged(self, client, auth_headers, test_db):
        """Can filter alerts by acknowledged status."""
        test_db.execute(
            "INSERT INTO alerts (type, message, severity, acknowledged) VALUES (?, ?, ?, 1)",
            ("test", "acked", "info"),
        )
        test_db.execute(
            "INSERT INTO alerts (type, message, severity, acknowledged) VALUES (?, ?, ?, 0)",
            ("test", "unacked", "info"),
        )
        test_db.commit()

        response = client.get("/api/alerts?acknowledged=true", headers=auth_headers)
        data = response.json()
        assert len(data) == 1
        assert data[0]["message"] == "acked"

        response = client.get("/api/alerts?acknowledged=false", headers=auth_headers)
        data = response.json()
        assert len(data) == 1
        assert data[0]["message"] == "unacked"

    def test_acknowledge_alert(self, client, auth_headers, test_db):
        """Test 12: POST /api/alerts/{id}/acknowledge marks alert as acknowledged."""
        cursor = test_db.execute(
            "INSERT INTO alerts (type, message, severity) VALUES (?, ?, ?)",
            ("drawdown", "Test alert", "warning"),
        )
        test_db.commit()
        alert_id = cursor.lastrowid

        response = client.post(f"/api/alerts/{alert_id}/acknowledge", headers=auth_headers)
        assert response.status_code == 200

        # Verify it was acknowledged
        row = test_db.execute(
            "SELECT acknowledged FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        assert row["acknowledged"] == 1

    def test_acknowledge_nonexistent_alert(self, client, auth_headers):
        """Acknowledging non-existent alert returns 404."""
        response = client.post("/api/alerts/99999/acknowledge", headers=auth_headers)
        assert response.status_code == 404

    def test_requires_auth(self, client):
        """Returns 401 without token."""
        response = client.get("/api/alerts")
        assert response.status_code == 401

    def test_alert_has_required_fields(self, client, auth_headers, test_db):
        """Alert objects contain all expected fields."""
        test_db.execute(
            "INSERT INTO alerts (type, message, severity) VALUES (?, ?, ?)",
            ("drawdown", "Test", "warning"),
        )
        test_db.commit()

        response = client.get("/api/alerts", headers=auth_headers)
        data = response.json()
        alert = data[0]
        expected = ["id", "type", "message", "severity", "acknowledged", "created_at"]
        for field in expected:
            assert field in alert, f"Missing field: {field}"
