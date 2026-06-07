# auth-permissions

MVP de controle de acesso com registro de violações na blockchain usando Hardhat local.

---

## Estrutura

```
auth-permissions/
├── ../../blockchain/
│   ├── contracts/ViolationLogger.sol
│   ├── scripts/deploy.ts
│   ├── hardhat.config.ts
│   └── package.json
├── backend/
│   ├── app.py            # Flask — rotas principais
│   ├── models.py         # SQLite — usuários
│   ├── auth.py           # JWT — geração e decorators
│   ├── blockchain.py     # web3.py — integração com contrato Hardhat
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── index.html            # Interface completa
```

---

## 1. Configurar o backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual (Linux/Mac)
source venv/bin/activate

# Ativar ambiente virtual (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt

# Copiar e editar o .env
# Linux/Mac
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

---

## 2. Subir blockchain local (Hardhat)

```bash
cd ../../blockchain
npm install
npx hardhat node
```

Em outro terminal:

```bash
cd ../../blockchain
npx hardhat run scripts/deploy.ts --network localhost
```

Copie o endereço exibido e configure no `.env` do backend:

```
CONTRACT_ADDRESS=0x...
```

---

## 3. Configurar o .env

Edite o arquivo `backend/.env`:

### JWT
```
JWT_SECRET=coloque_uma_string_longa_e_secreta_aqui
```

### Blockchain local (Hardhat)

Use os valores padrão do Hardhat para desenvolvimento:

```
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
WALLET_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
WALLET_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
CONTRACT_ADDRESS=0x...   # endereço retornado no deploy
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

## Sem blockchain (modo dev)

O sistema funciona mesmo sem o `.env` configurado.
Violações são apenas logadas no terminal com um aviso.
Configure o `.env` quando quiser integrar de verdade.
