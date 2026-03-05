const hre = require("hardhat");

async function main() {
  const Factory = await hre.ethers.getContractFactory("TicketRegistry");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();
  console.log("TICKET_CONTRACT_ADDRESS=", await contract.getAddress());
}

main().catch((e) => { console.error(e); process.exit(1); });