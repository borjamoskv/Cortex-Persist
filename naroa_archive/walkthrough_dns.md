# ⚡ Walkthrough: cortexpersist.org DNS & Project Alignment

**Reality Level:** `C5-REAL` (Epistemic & Network Verification)
**Target:** `cortexpersist.org` DNS Configuration
**Walkthrough ID:** `5ad02cd8`

## 1. Network Discovery & WHOIS Audit
A live query of the global DNS registry and Namecheap registrar databases was executed:
*   **Registrar:** NameCheap, Inc.
*   **Registry Expiry:** 2027-02-24
*   **Delegated Name Servers:**
    *   `connie.ns.cloudflare.com`
    *   `ken.ns.cloudflare.com`
*   **Status:** `clientTransferProhibited` (Active & Registered)

## 2. Name Server Interrogation & Failure Mode Isolation
Direct queries to the assigned Cloudflare name servers were executed:
```bash
dig @connie.ns.cloudflare.com cortexpersist.org A
dig @ken.ns.cloudflare.com cortexpersist.org A
```
*   **Result (Both Name Servers):** `status: REFUSED`
*   **Diagnostic:** Cloudflare's name servers are actively rejecting queries for `cortexpersist.org`. This indicates that the zone is either not configured, has been deleted, or is assigned to a different set of custom name servers in the active Cloudflare account.
*   **Global Impact:** All recursive resolvers return `SERVFAIL` due to the broken delegation path.

## 3. Corrective Action Plan
To restore domain resolution and transition to full `C5-REAL` hosting:
1.  **Cloudflare Zone Verification:** Verify if `cortexpersist.org` is active in the Cloudflare dashboard.
2.  **Name Server Matching:** Check if the name servers assigned by Cloudflare match `connie` and `ken`. If Cloudflare assigned a different pair, update the registrar settings in the Namecheap console.
3.  **Record Mapping:** Re-establish A/CNAME mappings once nameserver delegation is verified.
