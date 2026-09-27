---
id: pavilion
title: "Pavilion (Badminton Session & Skill-Rating Platform)"
role: "Solo Developer"
url: "https://github.com/ChujiaGuo/pavilion"
demo: "https://pavilion.chujia.dev"
start_date: "2026-05"
end_date: "Present"
skills:
  - Next.js
  - Hono
  - PostgreSQL
  - Domain-Driven Design
  - Concurrency Control
  - Ranking Algorithms
  - Automated Testing
bullets:
  - id: pavilion-b1
    text: "Architected a domain-driven modular monolith using Next.js, Hono, and PostgreSQL to isolate 5 core domains for seamless microservices migration."
    skills: [Next.js, Hono, PostgreSQL, Domain-Driven Design, Microservices]
    archetypes: [backend, fullstack, system-design]
    strength: 4
    metric: "5 isolated core domains"
  - id: pavilion-b2
    text: "Guaranteed zero double-booking anomalies and verified 100% of accessible database routes under concurrent load, authoring 61 automated tests and a live PostgreSQL testing container using pessimistic locking."
    skills: [PostgreSQL, Concurrency Control, Pessimistic Locking, Automated Testing, Docker]
    archetypes: [backend, testing, reliability]
    strength: 5
    metric: "Zero double-bookings; 100% database-route coverage; 61 automated tests"
  - id: pavilion-b3
    text: "Designed a weighted ranking algorithm that converges player ratings within 3–5 placement matches, incorporating volatility damping and time-decay factors validated across 25 unit and integration tests."
    skills: [Ranking Algorithms, Statistical Modeling, Algorithm Design, Testing]
    archetypes: [algorithms, machine-learning, data-science]
    strength: 4
    metric: "Rating convergence in 3–5 matches; 25 tests"
  - id: pavilion-b4
    text: "Implemented geospatial venue discovery utilizing PostGIS geography points, ST_DWithin distance queries, and server-side Google Places API proxying with session-token billing lifecycle management."
    skills: [PostGIS, PostgreSQL, TypeScript, REST APIs]
    archetypes: [backend, fullstack]
    strength: 4
  - id: pavilion-b5
    text: "Constructed multi-tiered administrative access controls spanning 4 hierarchical roles, complete with field-level change audit logging and a unified cross-domain audit trail."
    skills: [TypeScript, Hono, PostgreSQL, Authorization]
    archetypes: [backend, security]
    strength: 3
    metric: "4 hierarchical roles"
---
