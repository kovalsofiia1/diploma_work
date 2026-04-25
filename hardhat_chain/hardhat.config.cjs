require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const { ALCHEMY_API_KEY = "", PRIVATE_KEY = "" } = process.env;

const accounts = PRIVATE_KEY ? [PRIVATE_KEY] : [];

module.exports = {
  solidity: "0.8.20",
  networks: {
    localhost: { url: "http://127.0.0.1:8545" },
    mumbai: {
      url: ALCHEMY_API_KEY ? `https://polygon-mumbai.g.alchemy.com/v2/${ALCHEMY_API_KEY}` : "",
      accounts,
    },
    polygon: {
      url: ALCHEMY_API_KEY ? `https://polygon-mainnet.g.alchemy.com/v2/${ALCHEMY_API_KEY}` : "",
      accounts,
    },
    amoy: {
      url: "https://rpc-amoy.polygon.technology",
      accounts,
    }
  },
};