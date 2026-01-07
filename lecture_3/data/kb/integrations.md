# Integrations (SignalSpring)

## HubSpot
SignalSpring is not a CRM. We do not provide a native HubSpot UI integration in this workshop.

## Webhooks
You can send outputs to external systems using a webhook pattern:
- Your pipeline posts JSON to a URL you control
- The receiving service handles authentication, retries, and writing into the destination system

## Best practices
- Allow-list destinations
- Validate payload schemas
- Log requests and responses (without sensitive content)


