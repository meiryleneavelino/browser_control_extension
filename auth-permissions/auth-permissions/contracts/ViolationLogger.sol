// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ViolationLogger {

    address public owner;

    struct Violation {
        string  userId;
        string  userName;
        string  action;
        string  permissionsInToken;
        uint256 timestamp;
        address reportedBy;
    }

    Violation[] private violations;

    mapping(address => bool) public auditors;

    event ViolationRecorded(
        string  indexed userId,
        string  action,
        uint256 timestamp
    );

    event AuditorAdded(address indexed auditor);
    event AuditorRemoved(address indexed auditor);

    modifier onlyOwner() {
        require(msg.sender == owner, "Apenas o owner pode fazer isso");
        _;
    }

    modifier onlyAuditor() {
        require(
            auditors[msg.sender] || msg.sender == owner,
            "Acesso restrito a auditores"
        );
        _;
    }

    constructor() {
        owner = msg.sender;
        auditors[msg.sender] = true;
    }

    // ── Gravar violação ──────────────────────────────────────────────────────
    function recordViolation(
        string memory _userId,
        string memory _userName,
        string memory _action,
        string memory _permissionsInToken
    ) external {
        violations.push(Violation({
            userId:             _userId,
            userName:           _userName,
            action:             _action,
            permissionsInToken: _permissionsInToken,
            timestamp:          block.timestamp,
            reportedBy:         msg.sender
        }));

        emit ViolationRecorded(_userId, _action, block.timestamp);
    }

    // ── Consultar todas as violações (só auditores) ──────────────────────────
    function getAllViolations()
        external
        view
        onlyAuditor
        returns (Violation[] memory)
    {
        return violations;
    }

    // ── Consultar violações de um usuário específico (só auditores) ──────────
    function getViolationsByUser(string memory _userId)
        external
        view
        onlyAuditor
        returns (Violation[] memory)
    {
        uint256 count = 0;
        for (uint256 i = 0; i < violations.length; i++) {
            if (keccak256(bytes(violations[i].userId)) == keccak256(bytes(_userId))) {
                count++;
            }
        }
        Violation[] memory result = new Violation[](count);
        uint256 idx = 0;
        for (uint256 i = 0; i < violations.length; i++) {
            if (keccak256(bytes(violations[i].userId)) == keccak256(bytes(_userId))) {
                result[idx++] = violations[i];
            }
        }
        return result;
    }

    // ── Total de violações ───────────────────────────────────────────────────
    function getTotalViolations() external view returns (uint256) {
        return violations.length;
    }

    // ── Gerenciar auditores ──────────────────────────────────────────────────
    function addAuditor(address _auditor) external onlyOwner {
        auditors[_auditor] = true;
        emit AuditorAdded(_auditor);
    }

    function removeAuditor(address _auditor) external onlyOwner {
        require(_auditor != owner, "Nao pode remover o owner");
        auditors[_auditor] = false;
        emit AuditorRemoved(_auditor);
    }
}
