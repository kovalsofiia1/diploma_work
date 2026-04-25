const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const Factory = await hre.ethers.getContractFactory("TicketRegistry");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  const network = hre.network.name;
  const artifact = await hre.artifacts.readArtifact("TicketRegistry");

  const outputDir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(outputDir, { recursive: true });
  const outputPath = path.join(outputDir, `${network}.json`);

  const payload = {
    network,
    contractName: "TicketRegistry",
    contractAddress: address,
    abi: artifact.abi,
  };
  fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2), "utf-8");

  console.log("CONTRACT_ADDRESS=", address);
  console.log("ABI_OUTPUT=", outputPath);
}

main().catch((e) => { console.error(e); process.exit(1); });