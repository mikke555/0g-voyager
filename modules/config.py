import json
from sys import stderr

from loguru import logger
from web3 import Web3

logger.remove()
logger.add(
    stderr,
    format="<white>{time:HH:mm:ss}</white> | <level>{message}</level>",
)

CHAIN_DATA = {
    "ethereum": {
        "rpc": "https://rpc.ankr.com/eth",
        "explorer": "https://etherscan.io",
        "token": "ETH",
        "chain_id": 1,
    },
    "linea": {
        "rpc": "https://linea-mainnet.blastapi.io/5728a575-0886-4d28-b073-57d4cc303d3b",
        "explorer": "https://lineascan.build",
        "token": "ETH",
        "chain_id": 59144,
    },
    "base": {
        "rpc": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
        "token": "ETH",
        "chain_id": 8453,
    },
    "0g": {
        "rpc": "https://evmrpc-testnet.0g.ai",
        "explorer": "https://chainscan-newton.0g.ai",
        "token": "A0GI",
        "chain_id": 16600,
    },
}

mainnet_client = Web3(Web3.HTTPProvider(CHAIN_DATA["ethereum"]["rpc"]))

VOYAGER_0G = "0xF64B5E5D0aD587E2B8c796Cc07b108DD2f6C2288"

tasks = [
    {"name": "Follow 0G on Twitter", "id": "6715da4fc0c9e039a626fbea"},
    {"name": "Learn more about 0G dAIOS", "id": "6715db33c0c9e039a626fd12"},
    {
        "name": "Mint and verify that you hold 0G Voyager NFT",
        "id": "67162a6fc0c9e039a629d39d",
    },
    {"name": "Retweet the campaign announcement", "id": "6715db33c0c9e039a626fd13"},
    {"name": "Check out the TonTon miniapp", "id": "6715db33c0c9e039a626fd14"},
]

with open("data/abi/erc20.json") as f:
    ERC20_ABI = json.load(f)

with open("data/abi/voyager_0g.json") as f:
    VOYAGER_0G_ABI = json.load(f)
