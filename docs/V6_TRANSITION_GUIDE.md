# CORTEX v6: Sovereign Cloud Transition Guide

## 1. The Vision: From Daemon to Platform

CORTEX v5 established the foundation for a truly sovereign local AI agent system. It proved that complex cognitive memory, multi-model routing, and autonomous goal-seeking can run entirely on-device.

**v6 is the scale-up.** We are transitioning from a single-user local daemon to an enterprise-grade, multi-tenant "Sovereign Cloud" platform.

### Key Objectives

- **Multi-Tenancy:** Secure data isolation at every layer (L1, L2, L3).
- **Enterprise Security:** Full Role-Based Access Control (RBAC) and Audit Logging.
- **Global Availability:** Migration from local SQLite/embedded stores to distributed databases (AlloyDB, PostgreSQL) and high-availability vector clusters (Remote Qdrant).
- **Infinite Memory:** Scaling semantic recall across trillions of tokens without latency degradation.

---

## 2. Technical Roadmap

### Phase 1: Foundation (Current)

- [x] Injection of `tenant_id` into `CortexMemoryManager`.
- [/] Implementation of RBAC engine prototypes.
- [ ] Migration of the `EventLedgerL3` to support PostgreSQL as a backend option.

### Phase 2: Orchestration

- [ ] GraphQL API for cross-language integration (replacing raw JSON-RPC/Local sockets).
- [ ] Distributed Event Bus (NATS or Redis Stream) for swarm orchestration.

### Phase 3: Sovereign Cloud

- [ ] Deployment blueprints for GCP (AlloyDB + GKE + Qdrant Cloud).
- [ ] Zero-Knowledge encryption for user memories at rest.

---

## 3. For Developers: What Changes?

### Memory Interaction
In v5, `tenant_id` was ignored. In v6, every interaction **must** provide a `tenant_id` and a valid session scope.

```python
# v5 (Legacy)
await manager.process_interaction(role="user", content="...")

# v6 (Current Standard)
await manager.process_interaction(
    role="user", 
    content="...", 
    tenant_id="enterprise-customer-id"
)
```

### Data Isolation
All recall operations are now scoped by `tenant_id` by default. It is mathematically impossible (by policy) for Tenant A to retrieve vectors belonging to Tenant B.

---

## 4. Why "Sovereign"?
Even as we move to the cloud, the core mission remains: **User-owned Intelligence.** v6 will support hybrid-cloud deployments where compute happens in the cloud but the "Master Keys" stay on the user's hardware.
