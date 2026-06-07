import { ethers } from "hardhat";

async function main() {
  const ViolationLogger = await ethers.getContractFactory("ViolationLogger");
  const violationLogger = await ViolationLogger.deploy();

  await violationLogger.waitForDeployment();
  console.log(`ViolationLogger deployed to ${await violationLogger.getAddress()}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
