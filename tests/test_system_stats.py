import platform

from ticked.utils.system_stats import get_system_info


def test_get_system_info():
    info = get_system_info()

    assert "os_name" in info
    assert "os_version" in info
    assert "python_version" in info
    assert "memory_total" in info
    assert "memory_available" in info
    assert "cpu_percent" in info

    assert info["os_name"] == platform.system()
    assert isinstance(info["memory_total"], (int, float))
    assert info["memory_total"] > 0
    assert isinstance(info["memory_available"], (int, float))
    assert 0 <= info["cpu_percent"] <= 100
