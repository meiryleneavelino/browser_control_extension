import os
import logging
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS

from models import init_db, create_user, get_user_by_email, get_all_users, hash_password, VALID_PERMISSIONS
from auth import generate_token, require_auth, require_auditor
from blockchain import blockchain

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # permite o frontend chamar a API

init_db()


# ════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════

@app.post("/api/auth/register")
def register():
    """Cadastra um novo usuário com permissões definidas."""
    data = request.get_json(silent=True) or {}
    name        = (data.get("name") or "").strip()
    email       = (data.get("email") or "").strip().lower()
    password    = data.get("password") or ""
    permissions = data.get("permissions") or []
    is_auditor  = bool(data.get("is_auditor", False))

    if not name or not email or not password:
        return jsonify({"error": "Nome, e-mail e senha são obrigatórios"}), 400

    if len(password) < 6:
        return jsonify({"error": "Senha deve ter ao menos 6 caracteres"}), 400

    invalid = [p for p in permissions if p not in VALID_PERMISSIONS]
    if invalid:
        return jsonify({"error": f"Permissões inválidas: {invalid}"}), 400

    result = create_user(name, email, password, permissions, is_auditor)
    if not result["ok"]:
        return jsonify({"error": result["error"]}), 409

    logger.info(f"Usuário cadastrado: {email} | perms: {permissions}")
    return jsonify({"message": f"Usuário '{name}' cadastrado com sucesso"}), 201


@app.post("/api/auth/login")
def login():
    """Autentica o usuário e retorna um JWT com as permissões."""
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "E-mail e senha são obrigatórios"}), 400

    user = get_user_by_email(email)
    if not user or user["password"] != hash_password(password):
        return jsonify({"error": "E-mail ou senha incorretos"}), 401

    token = generate_token(user)
    logger.info(f"Login: {email}")
    return jsonify({
        "token": token,
        "user": {
            "id":          user["id"],
            "name":        user["name"],
            "email":       user["email"],
            "permissions": user["permissions"],
            "is_auditor":  user["is_auditor"],
        }
    })


# ════════════════════════════════════════════════════════════
#  VIOLATIONS
# ════════════════════════════════════════════════════════════

@app.post("/api/violation")
@require_auth
def record_violation():
    """
    Registra uma tentativa de acesso negado.
    O frontend envia quando o usuário clica em um botão sem permissão.
    """
    data   = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip()

    if not action:
        return jsonify({"error": "Campo 'action' é obrigatório"}), 400

    user        = request.user
    user_id     = user["sub"]
    user_name   = user["name"]
    token_perms = user.get("permissions", [])

    # Confirma que o usuário realmente NÃO tem a permissão
    if action in token_perms:
        return jsonify({"error": "Usuário possui essa permissão — nada a registrar"}), 400

    logger.warning(f"VIOLAÇÃO: {user_name} (id={user_id}) tentou '{action}' | perms: {token_perms}")

    # Grava na blockchain
    result = blockchain.record_violation(user_id, user_name, action, token_perms)

    if result["ok"]:
        return jsonify({
            "message":      "Violação registrada na blockchain",
            "tx_hash":      result["tx_hash"],
            "block_number": result["block_number"],
            "gas_used":     result["gas_used"],
        }), 201
    else:
        # Blockchain fora do ar ou não configurada — retorna aviso mas não falha o front
        return jsonify({
            "message": "Violação detectada (blockchain indisponível — apenas logada localmente)",
            "error":   result.get("error"),
            "tx_hash": None,
        }), 202


# ════════════════════════════════════════════════════════════
#  AUDIT (somente auditores)
# ════════════════════════════════════════════════════════════

@app.get("/api/violations")
@require_auditor
def get_violations():
    """Retorna todas as violações da blockchain."""
    violations = blockchain.get_all_violations()
    return jsonify({"violations": violations, "total": len(violations)})


@app.get("/api/violations/<user_id>")
@require_auditor
def get_violations_by_user(user_id):
    """Retorna violações de um usuário específico."""
    violations = blockchain.get_violations_by_user(user_id)
    return jsonify({"violations": violations, "total": len(violations)})


@app.get("/api/violations/count")
@require_auth
def get_total():
    """Total de violações registradas."""
    return jsonify({"total": blockchain.get_total()})


# ════════════════════════════════════════════════════════════
#  UTILS
# ════════════════════════════════════════════════════════════

@app.get("/api/users")
@require_auditor
def list_users():
    """Lista todos os usuários cadastrados (só auditores)."""
    return jsonify({"users": get_all_users()})


@app.get("/api/health")
def health():
    return jsonify({
        "status":     "ok",
        "blockchain": blockchain.is_connected,
    })


# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    logger.info(f"Iniciando Flask na porta {port}")
    logger.info(f"Blockchain conectada: {blockchain.is_connected}")
    app.run(debug=True, port=port)
