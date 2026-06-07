// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ViolationLogger {
    address public owner;

    struct Violation {
        string userId;
        string userName;
        string action;
        string permissionsInToken;
        uint256 timestamp;
        address reportedBy;
    }

    Violation[] private violations;
    mapping(address => bool) public auditors;

    event ViolationRecorded(string indexed userId, string action, uint256 timestamp);
    event AuditorAdded(address indexed auditor);
    event AuditorRemoved(address indexed auditor);

    modifier onlyOwner() {
        require(msg.sender == owner, "Apenas o owner pode fazer isso");
        _;
    }

    modifier onlyAuditor() {
        require(auditors[msg.sender] || msg.sender == owner, "Acesso restrito a auditores");
        _;
    }

    constructor() {
        owner = msg.sender;
        auditors[msg.sender] = true;
    }

    function recordViolation(
        string memory _userId,
        string memory _userName,
        string memory _action,
        string memory _permissionsInToken
    ) external {
        violations.push(
            Violation({
                userId: _userId,
                userName: _userName,
                action: _action,
                permissionsInToken: _permissionsInToken,
                timestamp: block.timestamp,
                reportedBy: msg.sender
            })
        );

        emit ViolationRecorded(_userId, _action, block.timestamp);
    }

    function getAllViolations() external view onlyAuditor returns (Violation[] memory) {
        return violations;
    }

    function getViolationsByUser(string memory _userId) external view onlyAuditor returns (Violation[] memory) {
        uint256 count = 0;
        for (uint256 i = 0; i < violations.length; i++) {
            if (keccak256(abi.encodePacked(violations[i].userId)) == keccak256(abi.encodePacked(_userId))) {
                count++;
            }
        }

        Violation[] memory filtered = new Violation[](count);
        uint256 idx = 0;
        for (uint256 i = 0; i < violations.length; i++) {
            if (keccak256(abi.encodePacked(violations[i].userId)) == keccak256(abi.encodePacked(_userId))) {
                filtered[idx] = violations[i];
                idx++;
            }
        }

        return filtered;
    }

    function getTotalViolations() external view returns (uint256) {
        return violations.length;
    }

    function addAuditor(address _auditor) external onlyOwner {
        auditors[_auditor] = true;
        emit AuditorAdded(_auditor);
    }

    function removeAuditor(address _auditor) external onlyOwner {
        auditors[_auditor] = false;
        emit AuditorRemoved(_auditor);
    }
}
