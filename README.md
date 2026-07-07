# EdgePulse
### Edge AI Vehicle Health & Predictive Maintenance System

> An edge-cloud cooperative AI system for intelligent vehicle diagnostics, predictive maintenance, and explainable vehicle health reasoning.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![Edge AI](https://img.shields.io/badge/Edge-AI-orange)
![LLM](https://img.shields.io/badge/LLM-TinyLlama%20%7C%20Phi--3-purple)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## Overview

Modern vehicles generate thousands of sensor readings every minute, yet most onboard diagnostic systems continue to rely on fixed threshold-based rules. While these systems detect isolated failures, they often fail to recognize gradual wear patterns or complex multi-sensor anomalies until significant damage has already occurred.

**EdgePulse** is an Edge AI powered vehicle intelligence platform that continuously reasons over structured vehicle telemetry to deliver predictive maintenance recommendations, explainable diagnostics, and early anomaly detection without requiring continuous cloud connectivity.

Unlike traditional diagnostic systems that react after faults occur, EdgePilot proactively interprets relationships between multiple sensor signals to identify potential issues before they become critical.

---

## Motivation

Current vehicle diagnostics face two major limitations:

- Maintenance schedules are based on fixed mileage rather than actual driving behaviour.
- Threshold-based alerts cannot identify complex failure patterns that emerge across multiple sensors.

EdgePilot addresses these challenges through an edge-first reasoning architecture capable of providing real-time, explainable recommendations while remaining operational even in low-connectivity environments.

---

# Key Features

✔ Edge AI reasoning using lightweight LLMs

✔ Predictive maintenance recommendations

✔ Multi-sensor anomaly detection

✔ Explainable AI diagnostics

✔ Edge-cloud cooperative verification

✔ Offline-first operation

✔ Synthetic vehicle telemetry simulation

✔ Real-time monitoring dashboard

---

# System Architecture

<p align="center">

(Add Architecture Diagram Here)

</p>

The architecture consists of four primary components.

### Edge Reasoning Engine

Runs continuously on the vehicle using a lightweight language model (TinyLlama / Phi-3 Mini) to analyse structured telemetry streams and generate immediate recommendations.

---

### Cloud Verification Layer

When internet connectivity is available, a larger cloud-hosted model independently validates edge decisions.

This asynchronous verification improves confidence while generating feedback for future model refinement without affecting real-time inference.

---

### FastAPI Orchestrator

Coordinates telemetry ingestion, local reasoning, cloud verification and diagnostic output through a lightweight API layer.

---

### Dashboard

Displays

- Live telemetry
- Diagnostic reasoning
- Maintenance recommendations
- Verification results
- System status

---

# Architecture Philosophy

EdgePilot is inspired by the concept of **Speculative Decoding** used in modern LLM inference.

Instead of accelerating text generation, the same principle is adapted to vehicle diagnostics:

```
Small Local Model
        │
Immediate Vehicle Diagnosis
        │
        ▼
Large Cloud Model
        │
Asynchronous Verification
        │
Continuous Improvement
```

This allows immediate responses while maintaining high-quality validation whenever connectivity exists.

---

# Technology Stack

## Artificial Intelligence

- TinyLlama
- Phi-3 Mini
- Llama.cpp
- Ollama

## Backend

- Python
- FastAPI

## Cloud

- Groq API
- Together AI

## Data

- Synthetic OBD-II Telemetry Generator
- JSON Streaming

## Dashboard

- HTML
- JavaScript
- Plotly

---

# Project Structure

```
EdgePilot/

├── backend/
│ ├── app.py
│ ├── orchestrator.py
│ ├── edge_reasoning.py
│ ├── cloud_verification.py
│ └── telemetry_generator.py
│
├── dashboard/
│
├── docs/
│ ├── System Architecture.pdf
│ └── Project Presentation.pdf
│
├── screenshots/
│
├── requirements.txt
│
└── README.md

```

---

# Demo video

https://github.com/user-attachments/assets/7a45ffba-becc-4bc3-a8bb-c5bcd4f6aeb5

---

# Example Workflow

```
Vehicle Telemetry

↓

Edge Model

↓

Maintenance Recommendation

↓

Cloud Verification

↓

Agreement / Disagreement Logging

↓

Future Model Improvement
```

---

# Example Output

```json
{
  "diagnosis": "Potential Brake Wear",
  "confidence": 0.93,
  "reasoning": [
    "Brake temperature increasing",
    "Brake pressure inconsistent",
    "Driving pattern indicates heavy braking"
  ],
  "recommendation": "Schedule inspection within 300 km"
}
```

---

# Why Edge AI?

Traditional cloud-only vehicle intelligence suffers from

- Internet dependency
- High latency
- Increased operational cost
- Reduced reliability in remote environments

EdgePilot performs primary reasoning locally, ensuring

- Low latency
- Continuous operation
- Reduced cloud usage
- Improved privacy

---

# Current Prototype Status

This repository contains a functional proof-of-concept demonstrating the architecture and reasoning workflow.

Current implementation includes

- Edge inference prototype
- FastAPI backend
- Synthetic telemetry generation
- Dashboard visualisation

Future work includes

- CAN Bus integration
- OBD-II live data ingestion
- Fleet-wide analytics
- Automotive SoC deployment
- Embedded NPU optimisation

---

# Applications

- Intelligent Transportation Systems (ITS)
- Connected Vehicles
- Fleet Management
- Predictive Maintenance
- Automotive Diagnostics
- Smart Mobility
- Commercial Vehicle Monitoring

---

# Future Enhancements

- Reinforcement Learning for maintenance optimisation
- Digital Twin integration
- Multi-vehicle fleet intelligence
- OTA model updates
- Driver behaviour profiling
- Edge TPU / Qualcomm AI Hub deployment

---

# License

MIT License

---

# Author

**Thaarunya Anantharaman**

B.E. Electronics & Communication Engineering

Artificial Intelligence • Edge AI • Machine Learning • Intelligent Transportation Systems







