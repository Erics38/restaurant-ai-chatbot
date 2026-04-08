#!/usr/bin/env python3
"""
Quick Docker diagnostics script.
Run this to get a snapshot of Docker container health without pytest.

Usage:
    python docker_diagnostic.py
"""

import docker
import sys
from datetime import datetime
from typing import Dict, Any


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def check_containers_running(client: docker.DockerClient) -> bool:
    """Check if both containers are running."""
    print_section("Container Status")

    try:
        containers = client.containers.list(all=True)
        container_dict = {c.name: c for c in containers}

        app_container = container_dict.get("restaurant-ai")
        llama_container = container_dict.get("restaurant-ai-llama")

        if not app_container:
            print("❌ App container 'restaurant-ai' not found")
            return False

        if not llama_container:
            print("❌ Llama container 'restaurant-ai-llama' not found")
            return False

        app_status = app_container.status
        llama_status = llama_container.status

        print(f"App container: {app_status}")
        print(f"Llama container: {llama_status}")

        if app_status != "running":
            print(f"❌ App container not running (status: {app_status})")
            return False

        if llama_status != "running":
            print(f"❌ Llama container not running (status: {llama_status})")
            return False

        print("✓ Both containers are running")
        return True

    except Exception as e:
        print(f"❌ Error checking containers: {e}")
        return False


def check_health_status(client: docker.DockerClient):
    """Check container health status."""
    print_section("Health Status")

    try:
        app_container = client.containers.get("restaurant-ai")
        llama_container = client.containers.get("restaurant-ai-llama")

        app_health = app_container.attrs.get("State", {}).get("Health", {})
        llama_health = llama_container.attrs.get("State", {}).get("Health", {})

        app_status = app_health.get("Status", "no healthcheck")
        llama_status = llama_health.get("Status", "no healthcheck")

        print(f"App container health: {app_status}")
        print(f"Llama container health: {llama_status}")

        # Show last health check log
        if app_status != "healthy":
            app_logs = app_health.get("Log", [])
            if app_logs:
                last_log = app_logs[-1]
                print(f"\nApp last health check:")
                print(f"  Exit code: {last_log.get('ExitCode')}")
                print(f"  Output: {last_log.get('Output', 'N/A')[:200]}")

        if llama_status != "healthy":
            llama_logs = llama_health.get("Log", [])
            if llama_logs:
                last_log = llama_logs[-1]
                print(f"\nLlama last health check:")
                print(f"  Exit code: {last_log.get('ExitCode')}")
                print(f"  Output: {last_log.get('Output', 'N/A')[:200]}")

        if app_status == "healthy" and llama_status == "healthy":
            print("\n✓ Both containers are healthy")
        else:
            print("\n⚠️  One or more containers unhealthy")

    except Exception as e:
        print(f"❌ Error checking health: {e}")


def check_network(client: docker.DockerClient):
    """Check network configuration."""
    print_section("Network Configuration")

    try:
        app_container = client.containers.get("restaurant-ai")
        llama_container = client.containers.get("restaurant-ai-llama")

        app_networks = list(app_container.attrs["NetworkSettings"]["Networks"].keys())
        llama_networks = list(llama_container.attrs["NetworkSettings"]["Networks"].keys())

        print(f"App networks: {app_networks}")
        print(f"Llama networks: {llama_networks}")

        common_networks = set(app_networks) & set(llama_networks)

        if common_networks:
            print(f"✓ Containers share network(s): {list(common_networks)}")

            # Show IP addresses
            for network in common_networks:
                app_ip = app_container.attrs["NetworkSettings"]["Networks"][network]["IPAddress"]
                llama_ip = llama_container.attrs["NetworkSettings"]["Networks"][network]["IPAddress"]
                print(f"\n  Network: {network}")
                print(f"    App IP: {app_ip}")
                print(f"    Llama IP: {llama_ip}")
        else:
            print("❌ Containers are not on the same network!")

    except Exception as e:
        print(f"❌ Error checking network: {e}")


def check_environment(client: docker.DockerClient):
    """Check environment variables."""
    print_section("Environment Configuration")

    try:
        app_container = client.containers.get("restaurant-ai")
        env_vars = app_container.attrs["Config"]["Env"]

        important_vars = {}
        for var in env_vars:
            if "=" in var:
                key, value = var.split("=", 1)
                if key in ["USE_LOCAL_AI", "LLAMA_SERVER_URL", "ENVIRONMENT", "LOG_LEVEL"]:
                    important_vars[key] = value

        print("Important environment variables:")
        for key, value in important_vars.items():
            print(f"  {key}: {value}")

        # Check critical settings
        use_local_ai = important_vars.get("USE_LOCAL_AI", "false")
        llama_url = important_vars.get("LLAMA_SERVER_URL", "")

        if use_local_ai.lower() == "false":
            print("\n⚠️  USE_LOCAL_AI is 'false' - AI features are disabled!")
            print("   Set USE_LOCAL_AI=true in docker-compose.yml or .env")
        else:
            print("\n✓ USE_LOCAL_AI is enabled")

        if llama_url:
            if "llama-server:8080" in llama_url:
                print(f"✓ LLAMA_SERVER_URL correctly set to: {llama_url}")
            else:
                print(f"⚠️  LLAMA_SERVER_URL may be incorrect: {llama_url}")
        else:
            print("⚠️  LLAMA_SERVER_URL not set")

    except Exception as e:
        print(f"❌ Error checking environment: {e}")


def check_ports(client: docker.DockerClient):
    """Check port mappings."""
    print_section("Port Mappings")

    try:
        app_container = client.containers.get("restaurant-ai")
        llama_container = client.containers.get("restaurant-ai-llama")

        app_ports = app_container.attrs["NetworkSettings"]["Ports"]
        llama_ports = llama_container.attrs["NetworkSettings"]["Ports"]

        print("App ports:")
        for container_port, host_binding in app_ports.items():
            if host_binding:
                host_port = host_binding[0]["HostPort"]
                print(f"  {container_port} -> {host_port}")

        print("\nLlama ports:")
        for container_port, host_binding in llama_ports.items():
            if host_binding:
                host_port = host_binding[0]["HostPort"]
                print(f"  {container_port} -> {host_port}")

        # Verify expected ports
        if "8000/tcp" in app_ports and app_ports["8000/tcp"]:
            print("\n✓ App port 8000 correctly exposed")
        else:
            print("\n❌ App port 8000 not exposed")

        if "8080/tcp" in llama_ports and llama_ports["8080/tcp"]:
            print("✓ Llama port 8080 correctly exposed")
        else:
            print("❌ Llama port 8080 not exposed")

    except Exception as e:
        print(f"❌ Error checking ports: {e}")


def check_resources(client: docker.DockerClient):
    """Check resource usage."""
    print_section("Resource Usage")

    try:
        app_container = client.containers.get("restaurant-ai")
        llama_container = client.containers.get("restaurant-ai-llama")

        # Get stats
        app_stats = app_container.stats(stream=False)
        llama_stats = llama_container.stats(stream=False)

        # Memory
        app_memory_mb = app_stats["memory_stats"].get("usage", 0) / (1024**2)
        llama_memory_mb = llama_stats["memory_stats"].get("usage", 0) / (1024**2)

        print(f"App memory usage: {app_memory_mb:.2f} MB")
        print(f"Llama memory usage: {llama_memory_mb:.2f} MB")

        # Check if llama has memory limit
        memory_limit = llama_container.attrs["HostConfig"].get("Memory", 0)
        if memory_limit:
            limit_gb = memory_limit / (1024**3)
            usage_percent = (llama_memory_mb / 1024) / limit_gb * 100
            print(f"Llama memory limit: {limit_gb:.2f} GB ({usage_percent:.1f}% used)")

        if llama_memory_mb > 8000:
            print("⚠️  Llama using significant memory (>8GB)")

    except Exception as e:
        print(f"❌ Error checking resources: {e}")


def check_recent_logs(client: docker.DockerClient):
    """Check recent logs for errors."""
    print_section("Recent Logs")

    try:
        app_container = client.containers.get("restaurant-ai")
        llama_container = client.containers.get("restaurant-ai-llama")

        # Get last 20 lines
        app_logs = app_container.logs(tail=20).decode(errors='ignore')
        llama_logs = llama_container.logs(tail=20).decode(errors='ignore')

        print("App container (last 20 lines):")
        print("-" * 60)
        print(app_logs)

        print("\nLlama container (last 20 lines):")
        print("-" * 60)
        print(llama_logs)

        # Check for error patterns
        error_patterns = ["error", "Error", "ERROR", "exception", "Exception", "failed", "timeout"]

        print("\nError pattern check:")
        app_errors = sum(1 for pattern in error_patterns if pattern in app_logs)
        llama_errors = sum(1 for pattern in error_patterns if pattern in llama_logs)

        print(f"  App errors: {app_errors} patterns found")
        print(f"  Llama errors: {llama_errors} patterns found")

        if app_errors == 0 and llama_errors == 0:
            print("✓ No obvious errors in recent logs")
        else:
            print("⚠️  Error patterns detected - review logs above")

    except Exception as e:
        print(f"❌ Error checking logs: {e}")


def test_connectivity(client: docker.DockerClient):
    """Test container connectivity."""
    print_section("Connectivity Test")

    try:
        app_container = client.containers.get("restaurant-ai")

        # Test DNS resolution
        print("Testing DNS resolution...")
        exit_code, output = app_container.exec_run(
            "python -c \"import socket; print(socket.gethostbyname('llama-server'))\"",
            demux=True
        )

        stdout, stderr = output

        if exit_code == 0 and stdout:
            ip = stdout.decode().strip()
            print(f"✓ llama-server resolves to: {ip}")
        else:
            error = stderr.decode() if stderr else "Unknown error"
            print(f"❌ DNS resolution failed: {error}")

        # Test HTTP connection
        print("\nTesting HTTP connection...")
        exit_code, output = app_container.exec_run(
            "python -c \"import urllib.request; print(urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read().decode())\"",
            demux=True
        )

        stdout, stderr = output

        if exit_code == 0 and stdout:
            response = stdout.decode()
            if "data" in response:
                print("✓ Successfully connected to llama-server API")
                # Parse and show model info
                import json
                try:
                    data = json.loads(response)
                    models = data.get("data", [])
                    if models:
                        print(f"  Loaded model: {models[0].get('id', 'unknown')}")
                except:
                    pass
            else:
                print(f"⚠️  Unexpected response: {response[:100]}")
        else:
            error = stderr.decode() if stderr else "Unknown error"
            print(f"❌ HTTP connection failed: {error}")

    except Exception as e:
        print(f"❌ Error testing connectivity: {e}")


def main():
    """Run all diagnostics."""
    print("\n" + "="*60)
    print("  Restaurant AI Docker Diagnostics")
    print("="*60)

    try:
        client = docker.from_env()
        print("✓ Connected to Docker")
    except Exception as e:
        print(f"❌ Failed to connect to Docker: {e}")
        print("\nMake sure Docker is running and you have proper permissions.")
        sys.exit(1)

    # Run all checks
    containers_ok = check_containers_running(client)

    if not containers_ok:
        print("\n⚠️  Containers are not running properly.")
        print("Run 'docker-compose up -d' to start them.")
        sys.exit(1)

    check_health_status(client)
    check_network(client)
    check_environment(client)
    check_ports(client)
    check_resources(client)
    test_connectivity(client)
    check_recent_logs(client)

    print_section("Diagnostic Complete")
    print("Check the output above for any ❌ or ⚠️ symbols")
    print("\nCommon issues:")
    print("  1. USE_LOCAL_AI=false - AI is disabled")
    print("  2. Unhealthy containers - check health check logs")
    print("  3. Network issues - verify containers on same network")
    print("  4. Connection timeouts - llama-server may still be loading model")


if __name__ == "__main__":
    main()
