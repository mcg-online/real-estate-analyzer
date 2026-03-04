# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting significant technical decisions in the Real Estate Analyzer project.

## What is an ADR?

An Architecture Decision Record (ADR) is a lightweight document that captures an important architectural or technical decision along with its context, consequences, and alternatives considered.

**Format**: Each ADR follows the standard template:
- **Status**: Accepted, Proposed, Deprecated, Superseded
- **Context**: Why the decision was needed
- **Decision**: What was decided
- **Consequences**: Positive/negative outcomes
- **Alternatives**: Other options considered

## ADRs

### [001: MongoDB as Primary Database](001-mongodb-as-primary-database.md)

**Status**: Accepted (v1.0.0+)

Chosen MongoDB for its flexible schema, native JSON support, and powerful aggregation pipeline for market analysis.

**Key Points**:
- Flexible schema accommodates varying property attributes
- Native JSON alignment with REST APIs
- Aggregation pipeline for complex market analysis
- Horizontal scaling via sharding

---

### [002: JWT Authentication](002-jwt-authentication.md)

**Status**: Accepted (v1.0.0+)

Implemented JWT token-based authentication with Flask-JWT-Extended for stateless, scalable user authentication.

**Key Points**:
- Stateless tokens work across multiple backend instances
- Token expiration after 1 hour (configurable)
- Token revocation via Redis-backed blocklist
- Property ownership tracked in JWT claims
- Passwords hashed with bcrypt

---

### [003: API Versioning Strategy](003-api-versioning-strategy.md)

**Status**: Accepted (v1.5.0+)

Adopted dual-path versioning with `/api/v1/*` and `/api/*` routes for backward compatibility.

**Key Points**:
- Every endpoint available at both `/api/v1/*` and `/api/*`
- Simple, standard URL-based versioning
- Gradual migration path for consumers
- Support window: 12-18 months per major version

---

### [004: Redis Integration](004-redis-integration.md)

**Status**: Accepted (v1.5.0+)

Integrated Redis for distributed caching, rate limiting, and JWT token blocklist with graceful fallback to in-memory.

**Key Points**:
- Caching for expensive queries (top markets, aggregations)
- Distributed rate limiting (200/day, 50/hour per IP)
- JWT token revocation (logout) works across instances
- Works without Redis (in-memory fallback for development)
- Configurable via `REDIS_URL` environment variable

---

## Using These ADRs

### For Developers

1. **Before making major decisions**: Review related ADRs to understand context
2. **When implementing features**: Follow patterns documented in relevant ADRs
3. **When creating new ADRs**: Use the standard template (see below)

### For Architects

1. **Onboarding new team members**: Share relevant ADRs to explain design decisions
2. **Code reviews**: Reference ADRs when discussing design patterns
3. **Technical discussions**: Use ADRs as starting point for deeper conversations

### For Project Decisions

1. **Reevaluate decisions**: Review ADR status periodically
2. **Deprecate decisions**: Update status to "Superseded" with replacement ADR
3. **New directions**: Create ADRs for major architectural changes

## Creating New ADRs

### Template

```markdown
# ADR NNN: Title

**Status**: Proposed | Accepted | Deprecated | Superseded

**Date**: YYYY-MM-DD

**Deciders**: Team members involved

## Context

Describe the issue/challenge that motivated this decision.

## Decision

Describe what was decided.

## Consequences

### Positive
- Benefit 1
- Benefit 2

### Negative
- Cost 1
- Cost 2

## Alternatives Considered

### Option A
Pros: ...
Cons: ...

### Option B
Pros: ...
Cons: ...

## References

- [Link 1](...)
- [Link 2](...)

## Related Decisions

- ADR NNN: ...
```

### Process

1. **Create Draft**: Write ADR with Proposed status
2. **Review**: Present to team and discuss
3. **Approve**: Update status to Accepted
4. **Implement**: Follow decision in code
5. **Document**: Link to ADR in relevant code comments or docs

## Status Definitions

- **Proposed**: Under discussion, not yet decided
- **Accepted**: Decision made, implement per this ADR
- **Deprecated**: Replaced by newer approach, phase out gradually
- **Superseded**: Replaced by another ADR (link to replacement)

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- [README.md](../../README.md) - Project overview
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contribution guidelines

## References

- [ADR: Architecture Decision Records](https://adr.github.io/)
- [Lightweight ADR Tools](https://adr.github.io/madr/)
- [Microservices ADR Catalog](https://microservices.io/patterns/index.html)
