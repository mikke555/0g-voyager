import random
import secrets
import time

import requests
from eth_account import Account
from requests.adapters import HTTPAdapter, Retry
from web3 import HTTPProvider, Web3
from web3.exceptions import TransactionNotFound
from web3.middleware import geth_poa_middleware

import settings as SETTINGS
from modules.config import CHAIN_DATA, ERC20_ABI, logger


class Wallet:
    def __init__(self, private_key, counter, chain="base"):
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.session = self.get_session()
        self.chain = chain
        self.web3 = Web3(
            HTTPProvider(
                CHAIN_DATA[chain]["rpc"],
                session=self.session,
                request_kwargs={"timeout": 180},
            )
        )
        self.explorer = CHAIN_DATA[chain]["explorer"]
        self.counter = counter
        self.label = f"{self.counter} {self.address} |"

        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def get_session(self):
        retries = Retry(
            total=5,
            backoff_factor=0.2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retries)
        session = requests.Session()
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

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

    def get_tx_data(self, value=0, eip1559=True, **kwargs):
        tx_data = {
            "chainId": self.web3.eth.chain_id,
            "from": self.address,
            "nonce": self.web3.eth.get_transaction_count(self.address),
            "value": value,
            **kwargs,
        }

        if eip1559 == False:
            tx_data["gasPrice"] = self.web3.eth.gas_price

        if self.chain == "0g":
            tx_data["gasPrice"] = tx_data["gasPrice"] * 2

        return tx_data

    def await_tx(self, tx_hash, timeout=180):
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

        total_time = 0
        poll_latency = 20

        while True:
            try:
                receipt = self.web3.eth.wait_for_transaction_receipt(
                    tx_hash, timeout=timeout
                )

                if receipt.status == 1:
                    logger.success(f"{self.label} Tx confirmed \n")
                    return True
                elif receipt.status is None:
                    logger.warning(f"{self.label} Waiting for tx confirmation...")
                    time.sleep(poll_latency)
                else:
                    logger.error(f"{self.label} Transaction failed")
                    return False

            except TransactionNotFound:
                if total_time > timeout:
                    logger.error(
                        f"{self.label} Transaction is not in the chain after {timeout} seconds"
                    )
                    return False

                logger.warning(f"{self.label} Waiting for tx confirmation...")
                total_time += poll_latency
                time.sleep(poll_latency)

    def send_tx(self, tx, tx_label="", retry=0, increment=1.1):
        try:
            if retry > 0:
                # Increment gas by 10% for each retry & recalculate nonce
                tx["gas"] = int(tx["gas"] * increment)
                tx["nonce"] = self.web3.eth.get_transaction_count(self.address)

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.info(f"{tx_label} | {self.explorer}/tx/{tx_hash.hex()}")

            return self.await_tx(tx_hash)

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

    def send_native_token_to_a_rand_wallet(self, amount_range):
        balance = self.get_balance()

        if balance == 0:
            logger.warning(f"{self.label} This wallet has no balance, skipping \n")
            return

        private_key = "0x" + secrets.token_hex(32)
        recipient = Account.from_key(private_key).address

        transfer_percentage = random.randint(*amount_range)
        transfer_amount = int(balance * (transfer_percentage / 100))

        tx = self.get_tx_data(
            eip1559=False, to=recipient, value=transfer_amount, gas=21000
        )

        return self.send_tx(tx, increment=2, tx_label=f"{self.label} Send A0GI")
