# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Gate exceptions."""

class GateError(Exception):
    """Raised when an action is blocked by the SovereignGate."""


class GateNotApproved(GateError):
    """Action has not been approved by the operator."""


class GateExpired(GateError):
    """Action approval window has expired."""


class GateInvalidSignature(GateError):
    """HMAC signature does not match."""
