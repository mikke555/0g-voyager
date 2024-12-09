import random
import time

from eth_account import Account
from web3 import Web3
from web3.middleware import geth_poa_middleware

import settings as SETTINGS
from modules.config import CHAIN_DATA, ERC20_ABI, logger


class Wallet:
    def __init__(self, private_key, counter, chain="base"):
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.address = self.account.address

        self.chain = chain
        self.web3 = Web3(Web3.HTTPProvider(CHAIN_DATA[chain]["rpc"]))
        self.explorer = CHAIN_DATA[chain]["explorer"]

        self.counter = counter
        self.label = f"{self.counter} {self.address} | "

        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def __str__(self):
        return f"Wallet(address={self.address})"

    def to_checksum(self, address):
        return self.web3.to_checksum_address(address)

    def get_contract(self, address, abi=None):
        contract_address = Web3.to_checksum_address(address)
        if not abi:
            abi = ERC20_ABI

        return self.web3.eth.contract(address=contract_address, abi=abi)

    def get_balance(self, token_addr=None):
        if token_addr == None:
            balance = self.web3.eth.get_balance(self.address)
        else:
            token = self.get_contract(token_addr)
            balance = token.functions.balanceOf(self.address).call()

        return balance

    def get_token_info(self, token_addr):
        token = self.get_contract(token_addr)

        balance = token.functions.balanceOf(self.address).call()
        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()

        return balance, decimals, symbol

    def get_tx_data(self, value=0, **kwargs):
        return {
            "chainId": self.web3.eth.chain_id,
            "from": self.address,
            "nonce": self.web3.eth.get_transaction_count(self.address),
            "value": value,
            # "gasPrice": self.web3.eth.gas_price,
            **kwargs,
        }

    def send_tx(self, tx, tx_label="", retry=0, increment=1.1):
        try:
            if retry > 0:
                # Increment gas by 10% for each retry & recalculate nonce
                tx["gas"] = int(tx["gas"] * increment)
                tx["nonce"] = self.web3.eth.get_transaction_count(self.address)

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.info(f"{tx_label} | {self.explorer}/tx/{tx_hash.hex()}")

            tx_receipt = self.web3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=400
            )

            attempts = f"after {retry + 1} attempts" if retry > 0 else ""

            if tx_receipt.status == 1:
                logger.success(f"{tx_label} | Tx confirmed {attempts} \n")
                return tx_receipt.status
            else:
                raise Exception(f"{tx_label} | Tx Failed \n")

        except Exception as error:
            logger.error(error)
            if retry < SETTINGS.RETRY_COUNT:
                time.sleep(random.randint(15, 20))
                return self.send_tx(tx, tx_label, retry=retry + 1)

    def check_allowance(self, token_addr, spender):
        token = self.get_contract(token_addr)

        return token.functions.allowance(self.address, spender).call()

    def approve(self, token_address, spender, amount, tx_label):
        token = self.get_contract(token_address)

        balance, decimals, symbol = self.get_balance(token_address)
        allowance = self.check_allowance(token_address, spender)

        if balance == 0:
            logger.info(f"{tx_label} | Your {symbol} is 0")
            return

        if allowance >= balance:
            logger.info(
                f"{tx_label} | {balance / 10 ** decimals} {symbol} already approved"
            )
            return

        tx_data = self.get_tx_data()
        tx = token.functions.approve(spender, amount).build_transaction(tx_data)

        status = self.send_tx(tx, tx_label)
        time.sleep(random.uniform(7, 20))
        return status
