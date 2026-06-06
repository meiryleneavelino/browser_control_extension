import jwt
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_troque_em_producao")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 8))


def generate_token(user: dict) -> str:
    payload = {
        "sub":         str(user["id"]),
        "name":        user["name"],
        "email":       user["email"],
        "permissions": user["permissions"],
        "is_auditor":  user["is_auditor"],
        "iat":         datetime.now(timezone.utc),
        "exp":         datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


# ── Decorator: requer JWT válido ─────────────────────────────────────────────
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token não fornecido"}), 401
        try:
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Decorator: requer permissão específica ───────────────────────────────────
def require_permission(permission: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Token não fornecido"}), 401
            try:
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                request.user = payload
            except jwt.InvalidTokenError:
                return jsonify({"error": "Token inválido"}), 401

            if permission not in payload.get("permissions", []):
                return jsonify({"error": f"Permissão '{permission}' necessária"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Decorator: requer auditor ────────────────────────────────────────────────
def require_auditor(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token não fornecido"}), 401
        try:
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            request.user = payload
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401

        if not payload.get("is_auditor"):
            return jsonify({"error": "Acesso restrito a auditores"}), 403
        return f(*args, **kwargs)
    return decorated
