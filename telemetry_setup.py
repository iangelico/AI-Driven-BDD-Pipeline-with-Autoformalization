import os
import logging

try:
    from google.adk.telemetry.google_cloud import get_gcp_exporters, get_gcp_resource
    from google.adk.telemetry.setup import maybe_set_otel_providers
    HAS_ADK_TELEMETRY = True
except ImportError:
    HAS_ADK_TELEMETRY = False

def initialize_otel_tracing():
    """
    Initializes OpenTelemetry tracing.
    If GOOGLE_CLOUD_PROJECT is configured, registers Google Cloud Trace exporter.
    """
    if not HAS_ADK_TELEMETRY:
        logging.warning("ADK Telemetry module not available. Tracing skipped.")
        return
        
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    
    if project_id:
        print(f"Configuring Google Cloud Trace telemetry for GCP project: {project_id}...")
        try:
            # Enable cloud tracing export
            exporters = get_gcp_exporters(
                enable_cloud_tracing=True,
                enable_cloud_metrics=False,
                enable_cloud_logging=False
            )
            resource = get_gcp_resource(project_id=project_id)
            maybe_set_otel_providers([exporters], otel_resource=resource)
            
            # Configure ADK-level telemetry environment variables
            os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "true"
            os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
            print("Google Cloud Trace telemetry successfully initialized!")
        except Exception as e:
            logging.error(f"Failed to initialize OTel providers: {e}")
    else:
        # Default local/no-op configuration
        os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "false"
        logging.info("GOOGLE_CLOUD_PROJECT not set. Google Cloud Trace skipped.")
