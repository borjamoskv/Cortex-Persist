# [C5-REAL] Exergy-Maximized
"""
macOS Security Control Domain
Audits and verifies 6 critical subsystems: Gatekeeper, SIP, FileVault, Firewall, XProtect, Ports.
"""

import asyncio
import logging
import plistlib
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("cortex_extensions.mac_maestro.security_control")

__all__ = ["SecurityControl", "SecurityState"]


@dataclass(frozen=True)
class SecurityState:
    """Deterministic representation of a Security Control audit state."""
    domain: str
    status: str
    is_secure: bool
    raw_output: str


class SecurityControl:
    """C5-REAL Security Auditor for macOS.
    
    Verifies physical system state by interacting directly with macOS 
    security binaries and parsing system plists.
    """

    async def _run_cmd(self, *args: str) -> tuple[int, str, str]:
        """Runs a subprocess command safely without shell expansion."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            return proc.returncode or 0, stdout.decode().strip(), stderr.decode().strip()
        except Exception as e:
            return -1, "", str(e)

    async def audit_gatekeeper(self) -> SecurityState:
        """Verify Gatekeeper status (spctl)."""
        code, out, err = await self._run_cmd("spctl", "--status")
        is_secure = "assessments enabled" in out
        status = "enabled" if is_secure else "disabled"
        return SecurityState("Gatekeeper", status, is_secure, out or err)

    async def audit_sip(self) -> SecurityState:
        """Verify System Integrity Protection (csrutil)."""
        code, out, err = await self._run_cmd("csrutil", "status")
        is_secure = "System Integrity Protection status: enabled" in out
        status = "enabled" if is_secure else "disabled/custom"
        return SecurityState("SIP", status, is_secure, out or err)

    async def audit_filevault(self) -> SecurityState:
        """Verify FileVault Encryption (fdesetup)."""
        code, out, err = await self._run_cmd("fdesetup", "status")
        is_secure = "FileVault is On." in out
        status = "On" if is_secure else ("Off" if "FileVault is Off" in out else "Transitional")
        return SecurityState("FileVault", status, is_secure, out or err)

    async def audit_firewall(self) -> SecurityState:
        """Verify Application Firewall (socketfilterfw)."""
        fw_path = "/usr/libexec/ApplicationFirewall/socketfilterfw"
        code, out, err = await self._run_cmd(fw_path, "--getglobalstate")
        is_secure = "Firewall is enabled." in out
        status = "enabled" if is_secure else "disabled"
        return SecurityState("Firewall", status, is_secure, out or err)

    async def audit_xprotect(self) -> SecurityState:
        """Verify XProtect version from system plist."""
        plist_path = Path("/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/XProtect.meta.plist")
        if not plist_path.exists():
            return SecurityState("XProtect", "Not Found", False, "File missing")
        
        try:
            with open(plist_path, "rb") as f:
                data = plistlib.load(f)
            version = data.get("Version", "Unknown")
            return SecurityState("XProtect", f"v{version}", True, f"Version: {version}")
        except Exception as e:
            return SecurityState("XProtect", "Error parsing", False, str(e))

    async def audit_ports(self) -> SecurityState:
        """List open listening ports (lsof)."""
        code, out, err = await self._run_cmd("lsof", "-i", "-P", "-n")
        lines = out.splitlines()
        listening = [line for line in lines if "LISTEN" in line]
        
        # For now, observing counts as valid (true secure state depends on a whitelist).
        raw_out = "\n".join(listening[:10])
        if len(listening) > 10:
            raw_out += f"\n... and {len(listening) - 10} more"
            
        return SecurityState(
            domain="Ports", 
            status=f"{len(listening)} open ports", 
            is_secure=True, 
            raw_output=raw_out
        )

    async def audit_all(self) -> list[SecurityState]:
        """Executes all security audits concurrently."""
        results = await asyncio.gather(
            self.audit_gatekeeper(),
            self.audit_sip(),
            self.audit_filevault(),
            self.audit_firewall(),
            self.audit_xprotect(),
            self.audit_ports(),
            return_exceptions=True
        )
        
        # Handle potential exceptions from asyncio.gather
        clean_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Audit {i} failed: {res}")
                clean_results.append(SecurityState(f"Domain_{i}", "Error", False, str(res)))
            else:
                clean_results.append(res)
                
        return clean_results
