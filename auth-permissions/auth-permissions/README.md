# auth-permissions

MVP de controle de acesso com registro de violações na blockchain (Polygon Amoy Testnet).

---

## Estrutura

```
auth-permissions/
├── backend/
│   ├── app.py            # Flask — rotas principais
│   ├── models.py         # SQLite — usuários
│   ├── auth.py           # JWT — geração e decorators
│   ├── blockchain.py     # web3.py — integração Polygon
│   ├── deploy.py         # script de deploy do contrato
│   ├── requirements.txt
│   └── .env.example
├── contracts/
│   └── ViolationLogger.sol   # Smart contract Solidity
└── frontend/
    └── index.html            # Interface completa
```

---

## 1. Configurar o backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
# ou: venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Copiar e editar o .env
cp .env.example .env
```

---

## 2. Configurar o .env

Edite o arquivo `backend/.env`:

### JWT
```
JWT_SECRET=coloque_uma_string_longa_e_secreta_aqui
```

### Polygon Amoy Testnet

**Passo 1 — RPC gratuita:**
- Acesse https://www.alchemy.com → crie uma conta → New App → Polygon Amoy
- Copie a URL HTTPS e cole em `POLYGON_RPC_URL`

**Passo 2 — Carteira:**
- Instale MetaMask (https://metamask.io)
- Crie uma carteira nova (use exclusivamente para este projeto)
- Exporte a Private Key: MetaMask → ... → Account Details → Export Private Key
- Cole em `WALLET_PRIVATE_KEY` e o endereço em `WALLET_ADDRESS`

**Passo 3 — MATIC de teste (gratuito):**
- Acesse https://faucet.polygon.technology
- Conecte a carteira → selecione Amoy → solicite MATIC
- Aguarde ~1 min para receber

---

## 3. Deploy do contrato

```bash
cd backend
python deploy.py
```

Copie o endereço exibido e coloque no `.env`:
```
CONTRACT_ADDRESS=0x...
```

---

## 4. Rodar o Flask

```bash
cd backend
python app.py
```

API disponível em: http://localhost:5000

---

## 5. Abrir o frontend

Abra `frontend/index.html` no browser diretamente.

O frontend se conecta automaticamente em `http://localhost:5000`.

---

## Endpoints da API

| Método | Rota                        | Auth       | Descrição                          |
|--------|-----------------------------|------------|------------------------------------|
| POST   | /api/auth/register          | —          | Cadastrar usuário com permissões   |
| POST   | /api/auth/login             | —          | Login → retorna JWT                |
| POST   | /api/violation              | JWT válido | Registrar violação na blockchain   |
| GET    | /api/violations             | Auditor    | Listar todas as violações          |
| GET    | /api/violations/\<user_id\> | Auditor    | Violações de um usuário            |
| GET    | /api/violations/count       | JWT válido | Total de violações                 |
| GET    | /api/users                  | Auditor    | Listar usuários                    |
| GET    | /api/health                 | —          | Status da API e blockchain         |

---

## Exemplo de payload JWT

```json
{
  "sub": "1",
  "name": "João Silva",
  "email": "joao@email.com",
  "permissions": ["read", "write"],
  "is_auditor": false,
  "iat": 1700000000,
  "exp": 1700028800
}
```

---

## Visualizar transações

Após gravar uma violação, acesse:
```
https://amoy.polygonscan.com/tx/<tx_hash>
```

---

## Sem blockchain (modo dev)

O sistema funciona mesmo sem o `.env` configurado.
Violações são apenas logadas no terminal com um aviso.
Configure o `.env` quando quiser integrar de verdade.
