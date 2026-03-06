# Changelog

All notable changes to GridOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-03-06

### Added

- **Core Models**: Pydantic v2 data models for DER telemetry, device info, and control commands
- **Protocol Adapters**: Base adapter framework with Modbus TCP, MQTT, DNP3, IEC 61850, and OPC-UA implementations
- **Storage Backends**: InfluxDB 2.x and TimescaleDB storage backends with async interfaces
- **Digital Twin Engine**: Physics-based models for Bus, Line, Transformer, Load, PV, Battery, and EV Charger
- **Power Flow Solver**: Simplified backward/forward sweep for radial distribution networks
- **ML Forecasting**: LSTM-based time-series forecaster with PyTorch (persistence fallback)
- **Anomaly Detection**: Isolation Forest detector with scikit-learn (threshold fallback)
- **MILP Optimiser**: PuLP-based energy management scheduler with greedy heuristic fallback
- **Real-time Dispatch**: Schedule-to-device dispatch engine via adapter layer
- **REST API**: FastAPI-based API with device, telemetry, control, forecast, and optimisation endpoints
- **WebSocket**: Live telemetry streaming with per-device subscriptions
- **Edge Support**: SQLite store-and-forward cache with cloud sync
- **Security**: API key and JWT authentication with role-based access control
- **Utilities**: Structured JSON logging, Prometheus metrics, helper functions
- **Docker**: Multi-stage Dockerfile and Docker Compose with InfluxDB
- **Kubernetes**: Deployment manifests with HPA auto-scaling
- **CI/CD**: GitHub Actions workflows for linting, testing, security scanning, and Docker builds
- **Documentation**: Architecture guide, API reference, deployment guide
- **Sample Data**: Load profile and solar irradiance CSV datasets
- **Quick Start**: Demo script showcasing all major features
