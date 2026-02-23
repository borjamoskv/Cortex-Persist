import os
from datetime import datetime
from pathlib import Path

# Plantilla Legal Burocrática SOBERANA
# Diseñada para activar los protocolos AML/KYC automáticos de KuCoin/Binance.
# El objetivo es lograr un "Asset Freeze" en las cuentas asociadas.

TEMPLATE_EN = """
URGENT: Request for Asset Freeze & KYC Disclosure - Cybercrime Associated with Account
To: legal@kucoin.com, compliance@kucoin.com, support@kucoin.com
Date: {DATE}

Subject: URGENT COMPLIANCE NOTICE: Traced Stolen Funds & EIP-7702 Exploit associated with your KYC user.

To the Legal and Compliance Departments at KuCoin,

This is a formal notification regarding stolen digital assets resulting from a sophisticated social engineering and EIP-7702 exploitation campaign. The stolen assets have been forensically traced back to an internal KuCoin Hot Wallet, indicating that the perpetrator is a verified KYC customer on your platform.

Based on our multi-agent on-chain forensic analysis (dossier attached), we have identified your user as the primary operator of a malicious wallet cluster responsible for the theft of NFTs, ENS domains, and digital assets.

INCIDENT DETAILS & ON-CHAIN EVIDENCE:
-------------------------------------
1. INITIAL FUNDING (ANCHOR POINT):
   Your hot wallet "KuCoin 4" (0x63351336421d01af3344b58e658adcb73d6ebef4) funded the attacker's master wallet:
   - Target Wallet: 0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60 (arbithumarb.eth)
   - Date of Funding: Nov-17-2021
   - Amount: 0.0181 ETH

2. ATTACK EXECUTION & FUND FLOW:
   - The master wallet (arbithumarb.eth) funded the execution wallet: 0xFFc77D765Ecd48b48B02008Bbe146bA2A06bcaBD.
   - Using a malicious EIP-7702 delegation tuple, the execution wallet drained assets from: {VICTIM_WALLET}.

3. IDENTITY CORRELATION (OFF-CHAIN):
   Our OSINT systems have correlated this on-chain cluster with the following identity:
   - Probable Name: Foizur
   - Country: Bangladesh
   - Associated Twitter: @arbithumarb
   - Associated Telegram: @earning_everytime

REQUIRED ACTIONS UNDER AML/KYC REGULATIONS:
-------------------------------------------
Under the mandates of international Anti-Money Laundering (AML) regulations and Counter-Terrorism Financing (CTF) frameworks, we formally request that KuCoin:
1. Immediately FREEZE all accounts and sub-accounts associated with the deposit/withdrawal addresses tied to the initial funding transaction of arbithumarb.eth.
2. Flag the following addresses in your internal deposit monitoring systems (Taint Tracking):
   - 0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60
   - 0xFFc77D765Ecd48b48B02008Bbe146bA2A06bcaBD

A formal law enforcement subpoena will follow from our local jurisdiction. This notice serves as your duty of care to prevent further liquidation of stolen assets through your platform. Failure to freeze these assets may result in accessory liability.

Please confirm receipt and outline the immediate actions taken regarding this compliance notice.

Sincerely,
{VICTIM_NAME}
{VICTIM_CONTACT}
"""


def generate_dossier(victim_wallet: str, victim_name: str, victim_contact: str) -> str:
    date_str = datetime.now().strftime("%B %d, %Y")
    dossier = TEMPLATE_EN.format(
        DATE=date_str,
        VICTIM_WALLET=victim_wallet,
        VICTIM_NAME=victim_name,
        VICTIM_CONTACT=victim_contact,
    )

    out_dir = str(Path(__file__).parent / "data" / "legal_dossiers")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"KUCOIN_LEGAL_NOTICE_{datetime.now().strftime('%Y%m%d')}.txt")

    with open(out_path, "w") as f:
        f.write(dossier)

    print(f"🗡️ Dossier Legal generado con éxito y guardado en:\n{out_path}")
    print(
        "Para automatizar su envío usando MAILTV-1, ejecuta el workflow correspondiente o despáchalo manualmente a legal@kucoin.com."
    )
    return out_path


if __name__ == "__main__":
    # Datos por defecto. El usuario puede cambiarlos antes de enviar.
    generate_dossier(
        victim_wallet="[INSERTA LAS WALLETS QUE TE HACKEARON AQUÍ]",
        victim_name="Borja Fernandez Angulo (Borja Moskv)",
        victim_contact="borja@moskv.co",
    )
