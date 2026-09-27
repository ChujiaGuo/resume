---
id: bluebot
title: "BlueBot"
role: "Founder & Lead Developer"
url: "https://github.com/ChujiaGuo/blueBot"
start_date: "2020-03"
end_date: "2025-05"
skills:
  - Node.js
  - Event-Driven Architecture
  - Google Cloud Vision
  - Tesseract OCR
  - Levenshtein Distance
  - Persistence
  - Moderation Systems
bullets:
  - id: proj-b1
    text: "Engineered an asynchronous, event-driven bot architecture scaling to 10k+ members; implemented a hot-reload command system via runtime module cache-clearing and a process manager to block concurrent executions and prevent race conditions on shared state."
    skills: [Node.js, Event-Driven Architecture, Concurrency, Hot Reloading]
    archetypes: [backend, distributed-systems, performance]
    strength: 5
    metric: "Scaled to 10k+ members"
  - id: proj-b2
    text: "Automated player identity verification with >95% accuracy in under 10 seconds, integrating Google Cloud Vision and Tesseract OCR pipelines with Levenshtein distance matching across 10k+ player records."
    skills: [OCR, Google Cloud Vision, Tesseract, Levenshtein Distance, Data Matching]
    archetypes: [machine-learning, computer-vision, data-processing]
    strength: 5
    metric: ">95% accuracy in under 10 seconds across 10k+ records"
  - id: proj-b3
    text: "Architected a crash-resilient moderation subsystem using synchronous disk persistence to commit role state, suspension expirations, and active audit records across bot reboots."
    skills: [Persistence, Reliability, Moderation Systems, Audit Logging]
    archetypes: [backend, reliability, security]
    strength: 3
    metric: "Preserved moderation state and audit records across reboots"
---
