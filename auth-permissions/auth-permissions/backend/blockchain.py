import os
import json
import logging
from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware
except ImportError:
    from web3.middleware import geth_poa_middleware as ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)

# ── ABI do contrato (apenas as funções que o backend usa) ────────────────────
CONTRACT_ABI = json.loads("""
[
  {
    "inputs": [
      {"internalType": "string", "name": "_userId",             "type": "string"},
      {"internalType": "string", "name": "_userName",           "type": "string"},
      {"internalType": "string", "name": "_action",             "type": "string"},
      {"internalType": "string", "name": "_permissionsInToken", "type": "string"}
    ],
    "name": "recordViolation",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "getAllViolations",
    "outputs": [
      {
        "components": [
          {"internalType": "string",  "name": "userId",             "type": "string"},
          {"internalType": "string",  "name": "userName",           "type": "string"},
          {"internalType": "string",  "name": "action",             "type": "string"},
          {"internalType": "string",  "name": "permissionsInToken", "type": "string"},
          {"internalType": "uint256", "name": "timestamp",          "type": "uint256"},
          {"internalType": "address", "name": "reportedBy",         "type": "address"}
        ],
        "internalType": "struct ViolationLogger.Violation[]",
        "name": "",
        "type": "tuple[]"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{"internalType": "string", "name": "_userId", "type": "string"}],
    "name": "getViolationsByUser",
    "outputs": [
      {
        "components": [
          {"internalType": "string",  "name": "userId",             "type": "string"},
          {"internalType": "string",  "name": "userName",           "type": "string"},
          {"internalType": "string",  "name": "action",             "type": "string"},
          {"internalType": "string",  "name": "permissionsInToken", "type": "string"},
          {"internalType": "uint256", "name": "timestamp",          "type": "uint256"},
          {"internalType": "address", "name": "reportedBy",         "type": "address"}
        ],
        "internalType": "struct ViolationLogger.Violation[]",
        "name": "",
        "type": "tuple[]"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "getTotalViolations",
    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{"internalType": "address", "name": "_auditor", "type": "address"}],
    "name": "addAuditor",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  }
]
""")


class BlockchainService:

    def __init__(self):
        self.rpc_url          = os.getenv("POLYGON_RPC_URL", "")
        self.private_key      = os.getenv("WALLET_PRIVATE_KEY", "")
        self.wallet_address   = os.getenv("WALLET_ADDRESS", "")
        self.contract_address = os.getenv("CONTRACT_ADDRESS", "")
        self.w3               = None
        self.contract         = None
        self._connected       = False
        self._connect()

    def _connect(self):
        if not self.rpc_url or not self.private_key or not self.contract_address:
            logger.warning("Blockchain não configurada — violações serão logadas apenas localmente.")
            return
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            # Polygon usa POA (Proof of Authority) — middleware necessário
            try:
                self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            except Exception:
                pass
            if not self.w3.is_connected():
                logger.error("Falha ao conectar na RPC do Polygon Amoy.")
                return
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=CONTRACT_ABI
            )
            self._connected = True
            logger.info(f"Blockchain conectada. Contrato: {self.contract_address}")
        except Exception as e:
            logger.error(f"Erro ao conectar blockchain: {e}")

    @property
    def is_connected(self):
        return self._connected

    # ── Gravar violação na chain ─────────────────────────────────────────────
    def record_violation(self, user_id: str, user_name: str, action: str, permissions_in_token: list) -> dict:
        if not self._connected:
            return {"ok": False, "error": "Blockchain não configurada", "tx_hash": None}
        try:
            nonce = self.w3.eth.get_transaction_count(
                Web3.to_checksum_address(self.wallet_address)
            )
            tx = self.contract.functions.recordViolation(
                str(user_id),
                user_name,
                action,
                ",".join(permissions_in_token)
            ).build_transaction({
                "from":     Web3.to_checksum_address(self.wallet_address),
                "nonce":    nonce,
                "gas":      200_000,
                "gasPrice": self.w3.eth.gas_price,
            })
            signed = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return {
                "ok":           True,
                "tx_hash":      tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used":     receipt.gasUsed,
            }
        except Exception as e:
            logger.error(f"Erro ao gravar violação na blockchain: {e}")
            return {"ok": False, "error": str(e), "tx_hash": None}

    # ── Consultar todas as violações ─────────────────────────────────────────
    def get_all_violations(self) -> list:
        if not self._connected:
            return []
        try:
            raw = self.contract.functions.getAllViolations().call({
                "from": Web3.to_checksum_address(self.wallet_address)
            })
            return [self._parse_violation(v) for v in raw]
        except Exception as e:
            logger.error(f"Erro ao consultar violações: {e}")
            return []

    # ── Consultar violações por usuário ──────────────────────────────────────
    def get_violations_by_user(self, user_id: str) -> list:
        if not self._connected:
            return []
        try:
            raw = self.contract.functions.getViolationsByUser(str(user_id)).call({
                "from": Web3.to_checksum_address(self.wallet_address)
            })
            return [self._parse_violation(v) for v in raw]
        except Exception as e:
            logger.error(f"Erro ao consultar violações do usuário: {e}")
            return []

    # ── Total de violações ────────────────────────────────────────────────────
    def get_total(self) -> int:
        if not self._connected:
            return 0
        try:
            return self.contract.functions.getTotalViolations().call()
        except Exception as e:
            logger.error(f"Erro ao contar violações: {e}")
            return 0

    @staticmethod
    def _parse_violation(v) -> dict:
        return {
            "userId":             v[0],
            "userName":           v[1],
            "action":             v[2],
            "permissionsInToken": v[3].split(",") if v[3] else [],
            "timestamp":          v[4],
            "reportedBy":         v[5],
        }


# Singleton
blockchain = BlockchainService()
