# ArmServe Test Suite

This directory points to the primary automated unit, integration, and performance test suites located in `backend/tests/`.

## Running Tests

```bash
# Execute all unit tests
pytest backend/tests/unit -v

# Execute integration test suite
pytest backend/tests/integration -v

# Execute specific phase hardening tests
pytest backend/tests/unit/test_phase12_reliability_security.py -v
```
