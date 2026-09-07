"""Tests for Docker container health used by /dev and Home diagnostics."""

from __future__ import annotations

from app.services.docker_health_service import _normalize_container, list_stack_containers


def test_normalize_flags_unhealthy_running_container() -> None:
    container = _normalize_container(
        {
            "Names": ["/correlcore-postgres"],
            "State": "running",
            "Status": "Up 3 hours (unhealthy)",
            "Labels": {"com.docker.compose.service": "postgres"},
        }
    )
    assert container.service == "postgres"
    assert container.health == "unhealthy"
    assert container.issue == "unhealthy"


def test_normalize_flags_stopped_worker() -> None:
    container = _normalize_container(
        {
            "Names": "correlcore-worker",
            "State": "exited",
            "Status": "Exited (137) 4 minutes ago",
            "Labels": "com.docker.compose.service=worker",
        }
    )
    assert container.service == "worker"
    assert container.exit_code == 137
    assert container.issue == "stopped"


def test_normalize_ignores_clean_migrate_exit() -> None:
    container = _normalize_container(
        {
            "Names": ["/correlcore-quickstart-migrate"],
            "State": "exited",
            "Status": "Exited (0) 2 days ago",
            "Labels": {"com.docker.compose.service": "migrate"},
        }
    )
    assert container.service == "migrate"
    assert container.exit_code == 0
    assert container.issue == "none"


def test_list_stack_containers_filters_foreign_names(monkeypatch) -> None:
    from app.services import docker_health_service

    monkeypatch.setattr(
        docker_health_service,
        "_load_raw_containers",
        lambda: [
            {
                "Names": ["/unrelated-nginx"],
                "State": "exited",
                "Status": "Exited (1) 1 second ago",
            },
            {
                "Names": ["/correlcore-redis"],
                "State": "exited",
                "Status": "Exited (1) 1 second ago",
            },
        ],
    )
    containers = list_stack_containers()
    assert [item.name for item in containers] == ["correlcore-redis"]
    assert containers[0].issue == "stopped"
