"""
Deploy do ViolationLogger.sol na Polygon Amoy Testnet.

Pré-requisitos:
    pip install web3 py-solc-x python-dotenv

Uso:
    python deploy.py

Após o deploy, copie o endereço exibido e cole em .env como CONTRACT_ADDRESS.
"""

import os
import sys
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

load_dotenv()

# ── Instalar e usar o compilador Solidity ────────────────────────────────────
try:
    from solcx import compile_standard, install_solc
except ImportError:
    print("Instalando py-solc-x...")
    os.system(f"{sys.executable} -m pip install py-solc-x")
    from solcx import compile_standard, install_solc

SOLC_VERSION = "0.8.20"
install_solc(SOLC_VERSION)

# ── Ler o contrato ───────────────────────────────────────────────────────────
contract_path = os.path.join(os.path.dirname(__file__), "..", "contracts", "ViolationLogger.sol")
with open(contract_path, "r") as f:
    source = f.read()

# ── Compilar ─────────────────────────────────────────────────────────────────
print("Compilando ViolationLogger.sol...")
compiled = compile_standard({
    "language": "Solidity",
    "sources": {"ViolationLogger.sol": {"content": source}},
    "settings": {
        "outputSelection": {
            "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}
        }
    },
}, solc_version=SOLC_VERSION)

abi      = compiled["contracts"]["ViolationLogger.sol"]["ViolationLogger"]["abi"]
bytecode = compiled["contracts"]["ViolationLogger.sol"]["ViolationLogger"]["evm"]["bytecode"]["object"]

# ── Conectar Polygon Amoy ─────────────────────────────────────────────────────
rpc_url     = os.getenv("POLYGON_RPC_URL")
private_key = os.getenv("WALLET_PRIVATE_KEY")
address     = os.getenv("WALLET_ADDRESS")

if not rpc_url or not private_key or not address:
    print("\n❌  Configure POLYGON_RPC_URL, WALLET_PRIVATE_KEY e WALLET_ADDRESS no .env\n")
    sys.exit(1)

w3 = Web3(Web3.HTTPProvider(rpc_url))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    print("❌  Não foi possível conectar na RPC. Verifique POLYGON_RPC_URL.")
    sys.exit(1)

print(f"✓ Conectado | Saldo da carteira: {w3.from_wei(w3.eth.get_balance(address), 'ether')} MATIC")

# ── Deploy ────────────────────────────────────────────────────────────────────
ViolationLogger = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(Web3.to_checksum_address(address))

tx = ViolationLogger.constructor().build_transaction({
    "from":     Web3.to_checksum_address(address),
    "nonce":    nonce,
    "gas":      2_000_000,
    "gasPrice": w3.eth.gas_price,
})

signed  = w3.eth.account.sign_transaction(tx, private_key=private_key)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

print(f"\nAguardando confirmação... tx: {tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

print(f"""
✅  Contrato deployado com sucesso!
    Endereço:     {receipt.contractAddress}
    Bloco:        {receipt.blockNumber}
    Gas usado:    {receipt.gasUsed}
    Tx hash:      {tx_hash.hex()}

Adicione ao .env:
    CONTRACT_ADDRESS={receipt.contractAddress}

Visualize no explorer:
    https://amoy.polygonscan.com/tx/{tx_hash.hex()}
""")

# Salva o ABI para referência
import json
with open(os.path.join(os.path.dirname(__file__), "contract_abi.json"), "w") as f:
    json.dump(abi, f, indent=2)
print("ABI salvo em backend/contract_abi.json")
