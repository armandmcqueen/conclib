import conclib
import requests

healthcheck_url = "http://localhost:8000/healthz"
rest_daemon = conclib.start_api(
    fast_api_command="uvicorn conclib.utils.apid.example_api:app  --port 8000",
    healthcheck_url=healthcheck_url,
    startup_healthcheck_timeout=10,
)

response = requests.get(healthcheck_url)
print(response.json())

# DO STUFF
print("🎉 Server launched successfully, now shutting down")


# Shut down the REST API when you are done to prevent blocking the main process shutting down
rest_daemon.shutdown()

print("👋 Goodbye")
