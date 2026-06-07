import os
import json
import logging
from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware
except ImportError:
    from web3.middleware import geth_poa_middleware as ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)

_HARDHAT_RPC_URL = "http://127.0.0.1:8545"
_HARDHAT_ACCOUNT_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
_HARDHAT_ACCOUNT_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_ARTIFACT_REL_PATH = os.path.join(
        "..",
        "..",
        "..",
        "blockchain",
        "artifacts",
        "contracts",
        "ViolationLogger.sol",
        "ViolationLogger.json",
)


def _load_contract_abi():
        artifact_path = os.path.join(os.path.dirname(__file__), _ARTIFACT_REL_PATH)
        with open(artifact_path, "r", encoding="utf-8") as f:
                artifact = json.load(f)
        return artifact["abi"]


class BlockchainService:

    def __init__(self):
        self.rpc_url          = os.getenv("BLOCKCHAIN_RPC_URL") or os.getenv("POLYGON_RPC_URL") or _HARDHAT_RPC_URL
        self.private_key      = os.getenv("WALLET_PRIVATE_KEY") or _HARDHAT_ACCOUNT_PRIVATE_KEY
        self.wallet_address   = os.getenv("WALLET_ADDRESS") or _HARDHAT_ACCOUNT_ADDRESS
        self.contract_address = os.getenv("CONTRACT_ADDRESS", "")
        self.contract_abi     = None
        self.w3               = None
        self.contract         = None
        self._connected       = False
        self._connect()

    def _connect(self):
        if not self.rpc_url or not self.private_key or not self.wallet_address or not self.contract_address:
            logger.warning("Blockchain não configurada — violações serão logadas apenas localmente.")
            return
        try:
            self.contract_abi = _load_contract_abi()
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            # Mantém compatibilidade com redes POA (ex.: Polygon)
            try:
                self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            except Exception:
                pass
            if not self.w3.is_connected():
                logger.error(f"Falha ao conectar na RPC ({self.rpc_url}).")
                return
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=self.contract_abi
            )
            self._connected = True
            logger.info(f"Blockchain conectada. RPC: {self.rpc_url} | Contrato: {self.contract_address}")
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
            payload_string = f"{user_id}|{user_name}|{action}|{','.join(permissions_in_token)}"
            logical_payload_bytes = len(payload_string.encode("utf-8"))
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
                "chainId":  self.w3.eth.chain_id,
                "gas":      200_000,
                "gasPrice": self.w3.eth.gas_price,
            })
            tx_data = tx.get("data", "")
            tx_input_size_bytes = max((len(tx_data) - 2) // 2, 0) if isinstance(tx_data, str) and tx_data.startswith("0x") else None
            signed = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            effective_gas_price = receipt.get("effectiveGasPrice") if isinstance(receipt, dict) else getattr(receipt, "effectiveGasPrice", None)
            gas_price_wei = int(effective_gas_price or tx.get("gasPrice") or self.w3.eth.gas_price)
            estimated_cost_wei = int(receipt.gasUsed) * gas_price_wei
            estimated_cost_matic = float(self.w3.from_wei(estimated_cost_wei, "ether"))
            return {
                "ok":           True,
                "tx_hash":      tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used":     receipt.gasUsed,
                "gas_price_wei": gas_price_wei,
                "estimated_cost_wei": estimated_cost_wei,
                "estimated_cost_matic": estimated_cost_matic,
                "logical_payload_bytes": logical_payload_bytes,
                "tx_input_size_bytes": tx_input_size_bytes,
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
