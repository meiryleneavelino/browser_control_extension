# browser_control_extension

A browser extension that integrates a lightweight frontend, a backend service for authentication and permission management, and a smart contract for event and violation logging.

## Overview

This application combines three main components to control browser actions and record relevant events on a test blockchain network:

- **Extension / Frontend:** A browser-based interface (or local web page) used for user interaction and event triggering.
- **Authentication Backend:** A Python service responsible for authentication, authorization, and permission management for sensitive operations.
- **`ViolationLogger` Smart Contract:** A Solidity smart contract used to record logs and violations on the blockchain through Hardhat.

## Repository Structure

```text
browser_control_extension/
├── auth-permissions/
│   ├── backend/
│   │   ├── app.py
│   │   ├── auth.py
│   │   ├── blockchain.py
│   │   ├── models.py
│   │   └── requirements.txt
│   └── frontend/
│       └── index.html
└── blockchain/
    ├── contracts/
    │   └── ViolationLogger.sol
    ├── scripts/
    │   └── deploy.ts
    ├── hardhat.config.ts
    └── package.json
```

## What the Application Does

- Allows the frontend/extension to submit events that, after validation by the backend, are recorded in the `ViolationLogger` smart contract.
- Provides authentication and authorization using JWT-based access control.
- Maintains immutable records of security-relevant events and policy violations on the blockchain.
- Separates responsibilities across system layers:
  - Frontend for user interaction.
  - Backend for authentication and authorization.
  - Blockchain for immutable logging and auditing.

## Architecture

The solution is composed of three layers:

### Frontend Layer

The frontend provides the user interface through which users authenticate and interact with the system. It can be executed as a standalone web page or packaged as a browser extension.

### Backend Layer

The backend is implemented in Python and is responsible for:

- User registration and authentication.
- JWT token generation and validation.
- Permission management.
- Violation detection.
- Communication with the blockchain network.

### Blockchain Layer

The blockchain layer uses Hardhat and Solidity to deploy the `ViolationLogger` smart contract.

When a violation is detected, the backend sends the event to the smart contract, which permanently stores the information on the blockchain.

## Features

- User registration.
- JWT authentication.
- Permission-based authorization.
- Violation detection.
- Immutable blockchain logging.
- Auditor access to violation records.
- Hardhat local blockchain support.

## Quick Start

### Backend Setup

```bash
cd auth-permissions
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1

pip install -r backend/requirements.txt
python backend/app.py
```

### Blockchain Setup

```bash
cd blockchain

npm install

npx hardhat compile

npx hardhat node
```

In another terminal:

```bash
cd blockchain

npx hardhat run scripts/deploy.ts --network localhost
```

Copy the deployed contract address and configure it in the backend environment variables.

### Frontend

Open:

```text
auth-permissions/frontend/index.html
```

in your browser.

## Environment Variables

Example `.env` configuration:

```env
JWT_SECRET=your_secret_key_here

BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545

WALLET_PRIVATE_KEY=your_private_key

WALLET_ADDRESS=your_wallet_address

CONTRACT_ADDRESS=your_contract_address
```

## API Endpoints

| Method | Endpoint | Authentication | Description |
|----------|----------|----------|----------|
| POST | `/api/auth/register` | No | Register a user |
| POST | `/api/auth/login` | No | Authenticate and obtain JWT |
| POST | `/api/violation` | JWT | Record a violation |
| GET | `/api/violations` | Auditor | List all violations |
| GET | `/api/violations/<user_id>` | Auditor | List violations by user |
| GET | `/api/violations/count` | JWT | Get total violations |
| GET | `/api/users` | Auditor | List registered users |
| GET | `/api/health` | No | Check API and blockchain status |

## Example JWT Payload

```json
{
  "sub": "1",
  "name": "John Doe",
  "email": "john@example.com",
  "permissions": ["read", "write"],
  "is_auditor": false,
  "iat": 1700000000,
  "exp": 1700028800
}
```

## Development Mode

The application can operate without blockchain integration.

If the blockchain environment variables are not configured:

- Violations are logged locally.
- The backend remains fully functional.
- Blockchain integration can be enabled later without changing the application logic.

## Future Work

Future developments may include:

- Browser extension packaging and distribution.
- Integration with external healthcare systems.
- Real-time monitoring of user actions.
- Cross-application security auditing.
- Deployment on public or consortium blockchain networks.
- Advanced compliance and forensic investigation capabilities.

## Contributing

Contributions are welcome.

Please open issues and pull requests describing:

- Proposed changes.
- Implementation details.
- Testing procedures.

## License

This project is intended for research and educational purposes.
