# GridOS Adapter Status

This document is intentionally conservative.

For the current lightweight release of GridOS, adapter breadth is **not** the primary launch promise. The repository contains adapter-related work for several protocols, but these modules should be understood as **evolving integration building blocks** rather than a finished production-grade adapter matrix.

## Current Positioning

| Protocol Area | Current Position |
|---|---|
| Modbus-related work | Experimental / evolving |
| MQTT-related work | Experimental / evolving |
| DNP3-related work | Stub / not launch scope |
| IEC 61850-related work | Stub / not launch scope |
| OPC-UA-related work | Experimental / evolving |

## This Document

The current launch version of GridOS is centered on the local API, model flow, local storage and cache behavior, digital-twin experimentation, and a smaller analytical path. Broad protocol support may become an important part of the project later, but it should not be treated as part of the primary product promise until each supported adapter has a reliable configuration story, repeatable tests, and a validated end-to-end example.

## Guidance for Users

If you are evaluating GridOS today, focus first on the core local-first workflow:

| Recommended First Step | Why |
|---|---|
| Start the API and open `/docs` | Confirms the base platform is running |
| Send telemetry through the documented API | Validates the main data path |
| Explore digital-twin and scheduling flows | Reflects the current practical direction |

If you are exploring adapter development, treat this area as a technical foundation rather than a stable public interface.
