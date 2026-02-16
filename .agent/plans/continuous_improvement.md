# CORTEX & LiveNotch: Continuous Improvement Plan

## 1. CORTEX Stability & Refactoring
- [x] **Fix Tests**: Resolve `vec0` issues in `test_improvements.py` and ensure `migrations.py` refactor is stable. (Done)
- [x] **Verify Sync**: Ensure `snapshot.py` and `write.py` split works correctly. (Tests Passed)
- [x] **Test Coverage**: Run full test suite to ensure no regression. (Done)

## 2. Feature: Time Tracking
- [x] **Schema**: Verify `CREATE_TIME_ENTRIES` and `HEARTBEATS` in `schema.py` (Already present).
- [x] **Daemon**: Implement `TimeTracker` in `cortex/daemon/` (Added flush capability to `core.py`).
- [ ] **API**: Expose time tracking endpoints or CLI commands. (API exists, CLI pending)

## 3. LiveNotch Launch
- [x] **Build**: Use `/build` workflow to compile and run LiveNotch. (Running in background)
- [ ] **Integration**: Ensure LiveNotch can talk to CORTEX (if applicable).
- [ ] **BrainDump**: Review `BrainDumpManager.swift` (user has it open).

## 4. Moskv Swarm
- [ ] **Review**: Check `moskv-swarm` files the user has open (`cloud_brain.py`, `mission-planner.js`).
- [ ] **Optimize**: Apply MEJORAlo patterns if needed.

## 5. Review & Polish ("Repasa todo")
- [ ] **Code Quality**: Check for lint errors and "Psi" markers. (Ongoing)
- [ ] **Documentation**: Update system docs if needed.

**Timeframe**: 1 hour session.
