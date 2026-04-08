"""
Docker health and connectivity tests.

Run these tests to diagnose issues with Docker containers and networking.
"""

import pytest
import httpx
import asyncio
import docker
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta


@pytest.fixture
def docker_client():
    """Create Docker client for testing."""
    return docker.from_env()


class TestDockerContainerHealth:
    """Test Docker container health and status."""

    def test_containers_running(self, docker_client):
        """Verify both containers are running."""
        containers = docker_client.containers.list()
        container_names = [c.name for c in containers]

        assert "restaurant-ai" in container_names, "App container not running"
        assert "restaurant-ai-llama" in container_names, "Llama server container not running"

    def test_containers_on_same_network(self, docker_client):
        """Verify containers are on the same Docker network."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_networks = list(app_container.attrs["NetworkSettings"]["Networks"].keys())
        llama_networks = list(llama_container.attrs["NetworkSettings"]["Networks"].keys())

        # Find common networks
        common_networks = set(app_networks) & set(llama_networks)

        assert len(common_networks) > 0, f"No common networks. App: {app_networks}, Llama: {llama_networks}"
        assert "restaurant-ai-chatbot_restaurant-network" in common_networks, "Not on expected network"

    def test_container_health_status(self, docker_client):
        """Check container health status."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_health = app_container.attrs.get("State", {}).get("Health", {}).get("Status")
        llama_health = llama_container.attrs.get("State", {}).get("Health", {}).get("Status")

        print(f"App container health: {app_health}")
        print(f"Llama container health: {llama_health}")

        # Print last health check logs
        if app_health != "healthy":
            app_logs = app_container.attrs.get("State", {}).get("Health", {}).get("Log", [])
            if app_logs:
                print(f"App health check failed: {app_logs[-1]}")

        if llama_health != "healthy":
            llama_logs = llama_container.attrs.get("State", {}).get("Health", {}).get("Log", [])
            if llama_logs:
                print(f"Llama health check failed: {llama_logs[-1]}")

    def test_port_mappings(self, docker_client):
        """Verify port mappings are correct."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_ports = app_container.attrs["NetworkSettings"]["Ports"]
        llama_ports = llama_container.attrs["NetworkSettings"]["Ports"]

        # Check app port 8000
        assert "8000/tcp" in app_ports, "App port 8000 not exposed"
        assert app_ports["8000/tcp"][0]["HostPort"] == "8000", "App port mapping incorrect"

        # Check llama port 8080
        assert "8080/tcp" in llama_ports, "Llama port 8080 not exposed"
        assert llama_ports["8080/tcp"][0]["HostPort"] == "8080", "Llama port mapping incorrect"

    def test_container_restart_count(self, docker_client):
        """Check if containers have been restarting (indicates crashes)."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_restart_count = app_container.attrs.get("RestartCount", 0)
        llama_restart_count = llama_container.attrs.get("RestartCount", 0)

        print(f"App container restart count: {app_restart_count}")
        print(f"Llama container restart count: {llama_restart_count}")

        if app_restart_count > 5:
            print(f"⚠️  App container has restarted {app_restart_count} times - possible instability")
        if llama_restart_count > 5:
            print(f"⚠️  Llama container has restarted {llama_restart_count} times - possible instability")

    def test_container_uptime(self, docker_client):
        """Check how long containers have been running."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_started = app_container.attrs["State"]["StartedAt"]
        llama_started = llama_container.attrs["State"]["StartedAt"]

        print(f"App container started: {app_started}")
        print(f"Llama container started: {llama_started}")

        # Parse and check if containers are very new (might still be initializing)
        app_start_time = datetime.fromisoformat(app_started.replace("Z", "+00:00"))
        llama_start_time = datetime.fromisoformat(llama_started.replace("Z", "+00:00"))

        now = datetime.now(app_start_time.tzinfo)
        app_uptime = now - app_start_time
        llama_uptime = now - llama_start_time

        print(f"App uptime: {app_uptime}")
        print(f"Llama uptime: {llama_uptime}")

        if app_uptime < timedelta(seconds=30):
            print("⚠️  App container recently started - might still be initializing")
        if llama_uptime < timedelta(minutes=2):
            print("⚠️  Llama container recently started - model might still be loading")

    def test_container_exit_code(self, docker_client):
        """Check if containers have exited with errors."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_exit_code = app_container.attrs["State"].get("ExitCode")
        llama_exit_code = llama_container.attrs["State"].get("ExitCode")

        print(f"App exit code: {app_exit_code}")
        print(f"Llama exit code: {llama_exit_code}")

        if app_exit_code and app_exit_code != 0:
            print(f"⚠️  App container exited with error code: {app_exit_code}")
        if llama_exit_code and llama_exit_code != 0:
            print(f"⚠️  Llama container exited with error code: {llama_exit_code}")


class TestDockerNetwork:
    """Docker network-specific tests."""

    def test_network_exists(self, docker_client):
        """Verify the restaurant network exists."""
        networks = docker_client.networks.list()
        network_names = [n.name for n in networks]

        assert "restaurant-ai-chatbot_restaurant-network" in network_names, "Restaurant network not found"

    def test_network_driver(self, docker_client):
        """Verify network is using bridge driver."""
        network = docker_client.networks.get("restaurant-ai-chatbot_restaurant-network")
        assert network.attrs["Driver"] == "bridge", f"Expected bridge driver, got {network.attrs['Driver']}"

    def test_dns_resolution_between_containers(self, docker_client):
        """Test DNS resolution from app container to llama-server."""
        app_container = docker_client.containers.get("restaurant-ai")

        # Try to resolve llama-server hostname
        exit_code, output = app_container.exec_run(
            "python -c \"import socket; print(socket.gethostbyname('llama-server'))\"",
            demux=True
        )

        stdout, stderr = output

        if exit_code != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            pytest.fail(f"DNS resolution failed: {error_msg}")

        ip_address = stdout.decode().strip()
        print(f"llama-server resolves to: {ip_address}")

        # Verify it's a valid IP
        assert ip_address.count(".") == 3, f"Invalid IP address: {ip_address}"

    def test_network_connectivity_ping(self, docker_client):
        """Test basic network connectivity using Python socket."""
        app_container = docker_client.containers.get("restaurant-ai")

        # Test if we can establish a socket connection to llama-server:8080
        exit_code, output = app_container.exec_run(
            "python -c \"import socket; s=socket.socket(); s.settimeout(5); s.connect(('llama-server', 8080)); s.close(); print('Connected')\"",
            demux=True
        )

        stdout, stderr = output

        if exit_code != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            pytest.fail(f"Network connectivity test failed: {error_msg}")

        assert b"Connected" in stdout, "Failed to establish socket connection"

    def test_container_ip_addresses(self, docker_client):
        """Display and verify container IP addresses."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        network_name = "restaurant-ai-chatbot_restaurant-network"

        app_ip = app_container.attrs["NetworkSettings"]["Networks"][network_name]["IPAddress"]
        llama_ip = llama_container.attrs["NetworkSettings"]["Networks"][network_name]["IPAddress"]

        print(f"App container IP: {app_ip}")
        print(f"Llama container IP: {llama_ip}")

        assert app_ip, "App container has no IP address"
        assert llama_ip, "Llama container has no IP address"
        assert app_ip != llama_ip, "Containers have the same IP address"


class TestDockerResources:
    """Test Docker resource limits and usage."""

    def test_memory_limits(self, docker_client):
        """Check if memory limits are set correctly."""
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        memory_limit = llama_container.attrs["HostConfig"].get("Memory", 0)
        memory_reservation = llama_container.attrs["HostConfig"].get("MemoryReservation", 0)

        print(f"Memory limit: {memory_limit / (1024**3):.2f} GB" if memory_limit else "No memory limit")
        print(f"Memory reservation: {memory_reservation / (1024**3):.2f} GB" if memory_reservation else "No memory reservation")

    def test_cpu_limits(self, docker_client):
        """Check CPU limits."""
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        cpu_quota = llama_container.attrs["HostConfig"].get("CpuQuota", 0)
        cpu_period = llama_container.attrs["HostConfig"].get("CpuPeriod", 0)

        if cpu_quota and cpu_period:
            cpu_limit = cpu_quota / cpu_period
            print(f"CPU limit: {cpu_limit:.2f} cores")
        else:
            print("No CPU limit set")

    def test_container_stats(self, docker_client):
        """Get real-time container resource usage."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        # Get stats (stream=False returns one snapshot)
        app_stats = app_container.stats(stream=False)
        llama_stats = llama_container.stats(stream=False)

        # Memory usage
        app_memory = app_stats["memory_stats"].get("usage", 0) / (1024**2)
        llama_memory = llama_stats["memory_stats"].get("usage", 0) / (1024**2)

        print(f"App container memory usage: {app_memory:.2f} MB")
        print(f"Llama container memory usage: {llama_memory:.2f} MB")

        # CPU usage
        print(f"App CPU stats: {app_stats.get('cpu_stats', {})}")
        print(f"Llama CPU stats: {llama_stats.get('cpu_stats', {})}")


class TestDockerVolumes:
    """Test Docker volume mounts."""

    def test_volume_mounts(self, docker_client):
        """Verify volume mounts are configured correctly."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_mounts = app_container.attrs["Mounts"]
        llama_mounts = llama_container.attrs["Mounts"]

        print("=== App Container Mounts ===")
        for mount in app_mounts:
            print(f"  {mount['Source']} -> {mount['Destination']} (RW: {mount.get('RW', True)})")

        print("\n=== Llama Container Mounts ===")
        for mount in llama_mounts:
            print(f"  {mount['Source']} -> {mount['Destination']} (RW: {mount.get('RW', True)})")

        # Verify critical mounts exist
        llama_model_mount = any(m["Destination"] == "/models" for m in llama_mounts)
        assert llama_model_mount, "Llama container missing /models mount"

    def test_model_file_exists(self, docker_client):
        """Verify model file exists in llama container."""
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        exit_code, output = llama_container.exec_run(
            "ls -lh /models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
            demux=True
        )

        stdout, stderr = output

        if exit_code != 0:
            error_msg = stderr.decode() if stderr else "Model file not found"
            pytest.fail(f"Model file check failed: {error_msg}")

        file_info = stdout.decode()
        print(f"Model file: {file_info}")


class TestLlamaServerConnectivity:
    """Test connectivity to llama-server from different locations."""

    @pytest.mark.asyncio
    async def test_llama_server_from_host(self):
        """Test accessing llama-server from host machine."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get("http://localhost:8080/v1/models")
                assert response.status_code == 200, f"Unexpected status: {response.status_code}"
                data = response.json()
                assert "data" in data, "Invalid response format"
                assert len(data["data"]) > 0, "No models loaded"
            except httpx.TimeoutException:
                pytest.fail("Timeout connecting to llama-server from host")
            except Exception as e:
                pytest.fail(f"Error connecting to llama-server: {e}")

    @pytest.mark.asyncio
    async def test_llama_server_from_app_container(self, docker_client):
        """Test accessing llama-server from app container using container hostname."""
        app_container = docker_client.containers.get("restaurant-ai")

        # Execute Python command inside app container
        exit_code, output = app_container.exec_run(
            "python -c \"import urllib.request; print(urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read().decode())\"",
            demux=True
        )

        stdout, stderr = output

        if exit_code != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            pytest.fail(f"Failed to connect from app container: {error_msg}")

        assert stdout is not None, "No output from container"
        response_text = stdout.decode()
        assert "data" in response_text, f"Invalid response: {response_text}"

    @pytest.mark.asyncio
    async def test_llama_server_chat_completion(self):
        """Test llama-server chat completion endpoint."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "http://localhost:8080/v1/chat/completions",
                    json={
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": "Say 'test successful' and nothing else."}
                        ],
                        "max_tokens": 10,
                        "temperature": 0.1,
                    }
                )
                assert response.status_code == 200, f"Unexpected status: {response.status_code}"
                data = response.json()
                assert "choices" in data, "Invalid response format"
                assert len(data["choices"]) > 0, "No completions returned"

                content = data["choices"][0].get("message", {}).get("content", "")
                print(f"AI response: {content}")

            except httpx.TimeoutException:
                pytest.fail("Timeout during chat completion")
            except Exception as e:
                pytest.fail(f"Error during chat completion: {e}")

    @pytest.mark.asyncio
    async def test_llama_server_response_time(self):
        """Measure llama-server response time."""
        times = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(3):
                start = time.time()
                try:
                    response = await client.get("http://localhost:8080/v1/models")
                    elapsed = time.time() - start
                    times.append(elapsed)
                    print(f"Request {i+1} took {elapsed:.3f}s")
                except Exception as e:
                    print(f"Request {i+1} failed: {e}")

        if times:
            avg_time = sum(times) / len(times)
            print(f"Average response time: {avg_time:.3f}s")

            if avg_time > 5:
                print("⚠️  Slow response times detected")


class TestAppConnectivity:
    """Test app endpoint connectivity."""

    @pytest.mark.asyncio
    async def test_app_health_endpoint(self):
        """Test app health endpoint."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get("http://localhost:8000/health")
                assert response.status_code == 200, f"Health check failed: {response.status_code}"
                data = response.json()
                assert data.get("status") == "healthy", f"Unhealthy status: {data}"
            except Exception as e:
                pytest.fail(f"Error accessing health endpoint: {e}")

    @pytest.mark.asyncio
    async def test_app_root_endpoint(self):
        """Test app root endpoint."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get("http://localhost:8000/")
                assert response.status_code == 200, f"Root endpoint failed: {response.status_code}"
            except Exception as e:
                pytest.fail(f"Error accessing root endpoint: {e}")

    @pytest.mark.asyncio
    async def test_app_chat_endpoint_with_ai_disabled(self):
        """Test chat endpoint when USE_LOCAL_AI=false (template mode)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    "http://localhost:8000/chat",
                    json={"message": "Hello"}
                )
                assert response.status_code == 200, f"Chat failed: {response.status_code}"
                data = response.json()
                assert "response" in data, "No response field"
                assert "session_id" in data, "No session_id field"
                print(f"Chat response: {data['response']}")
            except Exception as e:
                pytest.fail(f"Error during chat: {e}")


class TestEnvironmentConfiguration:
    """Test environment configuration and settings."""

    def test_use_local_ai_setting(self, docker_client):
        """Check USE_LOCAL_AI environment variable."""
        app_container = docker_client.containers.get("restaurant-ai")
        env_vars = app_container.attrs["Config"]["Env"]

        use_local_ai = None
        llama_server_url = None

        for var in env_vars:
            if var.startswith("USE_LOCAL_AI="):
                use_local_ai = var.split("=", 1)[1]
            if var.startswith("LLAMA_SERVER_URL="):
                llama_server_url = var.split("=", 1)[1]

        print(f"USE_LOCAL_AI: {use_local_ai}")
        print(f"LLAMA_SERVER_URL: {llama_server_url}")

        if use_local_ai == "false":
            print("WARNING: USE_LOCAL_AI is set to 'false' - AI features are disabled!")

        if llama_server_url:
            assert "llama-server:8080" in llama_server_url, f"Incorrect llama server URL: {llama_server_url}"

    def test_all_environment_variables(self, docker_client):
        """Display all environment variables for debugging."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        print("=== App Container Environment ===")
        for var in app_container.attrs["Config"]["Env"]:
            print(f"  {var}")

        print("\n=== Llama Container Environment ===")
        for var in llama_container.attrs["Config"]["Env"]:
            print(f"  {var}")


class TestContainerLogs:
    """Analyze container logs for errors."""

    def test_app_container_logs(self, docker_client):
        """Check app container logs for errors."""
        app_container = docker_client.containers.get("restaurant-ai")
        logs = app_container.logs(tail=100).decode()

        print("=== APP CONTAINER LOGS (last 100 lines) ===")
        print(logs)

        # Look for specific error patterns
        error_patterns = [
            "Error calling llama-server",
            "Falling back to template responses",
            "TimeoutException",
            "ConnectionError",
        ]

        for pattern in error_patterns:
            if pattern in logs:
                print(f"⚠️  Found error pattern: {pattern}")

    def test_llama_container_logs(self, docker_client):
        """Check llama container logs for errors."""
        llama_container = docker_client.containers.get("restaurant-ai-llama")
        logs = llama_container.logs(tail=100).decode()

        print("=== LLAMA CONTAINER LOGS (last 100 lines) ===")
        print(logs)

        # Check if server started successfully
        if "Uvicorn running on" in logs:
            print("✓ Llama server started successfully")
        else:
            print("⚠️  Llama server may not have started properly")

    def test_logs_for_oom_errors(self, docker_client):
        """Check for Out of Memory errors in logs."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_logs = app_container.logs(tail=500).decode()
        llama_logs = llama_container.logs(tail=500).decode()

        oom_patterns = ["out of memory", "OOM", "MemoryError", "killed"]

        for pattern in oom_patterns:
            if pattern.lower() in app_logs.lower():
                print(f"⚠️  Possible OOM in app container: {pattern}")
            if pattern.lower() in llama_logs.lower():
                print(f"⚠️  Possible OOM in llama container: {pattern}")


class TestDockerCompose:
    """Test docker-compose configuration."""

    def test_compose_project_name(self, docker_client):
        """Verify containers belong to the correct compose project."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_labels = app_container.labels
        llama_labels = llama_container.labels

        app_project = app_labels.get("com.docker.compose.project")
        llama_project = llama_labels.get("com.docker.compose.project")

        print(f"App project: {app_project}")
        print(f"Llama project: {llama_project}")

        assert app_project == llama_project, "Containers belong to different projects"
        assert app_project == "restaurant-ai-chatbot", f"Unexpected project name: {app_project}"

    def test_compose_service_names(self, docker_client):
        """Verify compose service names are correct."""
        app_container = docker_client.containers.get("restaurant-ai")
        llama_container = docker_client.containers.get("restaurant-ai-llama")

        app_service = app_container.labels.get("com.docker.compose.service")
        llama_service = llama_container.labels.get("com.docker.compose.service")

        print(f"App service name: {app_service}")
        print(f"Llama service name: {llama_service}")

        assert app_service == "app", f"Unexpected app service name: {app_service}"
        assert llama_service == "llama-server", f"Unexpected llama service name: {llama_service}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
