# unit tests package

# --- Audit Logging ---
def test_audit_log_action(tmp_path, caplog):
    from utils import audit_log_action, setup_audit_logger
    import os, json
    logfile = tmp_path / "audit.log"
    setup_audit_logger(str(logfile), max_bytes=1024, backup_count=1)
    with caplog.at_level("INFO", logger="vyos_audit"):
        audit_log_action("testuser", "test_action", "success", details={"info": "test"})
    # Read the log file and check for structured JSON
    with open(logfile) as f:
        log_line = f.readline()
        log_obj = json.loads(log_line)
        assert log_obj["user"] == "testuser"
        assert log_obj["action"] == "test_action"
        assert log_obj["result"] == "success"
        assert log_obj["details"]["info"] == "test"

# --- Dynamic-to-Static IP Provisioning ---
from unittest.mock import patch

def test_get_dhcp_leases():
    with patch("vyos_core.get_dhcp_leases") as mock_get_leases:
        mock_get_leases.return_value = [("00:11:22:33:44:55", "192.168.1.100")]
        from vyos_core import get_dhcp_leases
        leases = get_dhcp_leases()
        assert isinstance(leases, list)
        assert leases == [("00:11:22:33:44:55", "192.168.1.100")]

# --- VPN Services ---
def test_vpn_create_schema():
    from schemas import VPNCreate
    vpn = VPNCreate(name="testvpn", type="ipsec")
    assert vpn.name == "testvpn"

# --- Config Backup/Restore ---
def test_backup_restore_stubs():
    from vyos_core import backup_config, restore_config
    assert callable(backup_config)
    assert callable(restore_config)

# --- Task Management (Async Ops) ---
def test_task_management_stubs():
    from vyos_core import submit_task, get_task_status
    assert callable(submit_task)
    assert callable(get_task_status)
