import os
import random
import time

from eth_account.messages import encode_defunct
from tls_client import Session

import settings as SETTINGS
from modules.config import VOYAGER_0G, VOYAGER_0G_ABI, logger
from modules.utils import check_gas
from modules.wallet import Wallet


class Intract(Wallet):
    def __init__(self, private_key, proxy, label):
        super().__init__(private_key, label)
        self.label += " Intract |"
        self.session = self.get_new_session(proxy)
        self.contract = self.get_contract(VOYAGER_0G, VOYAGER_0G_ABI)

    def get_new_session(self, proxy):
        session = Session(
            client_identifier="chrome_120", random_tls_extension_order=True
        )

        session.proxies = {
            "http": proxy,
            "https": proxy,
        }

        return session

    def get_nonce(self):
        url = "https://gcp-api.intract.io/api/qv1/auth/generate-nonce"
        payload = {
            "namespaceTag": "EVM::EVM",
            "walletAddress": self.address,
            "connector": "METAMASK::EOA",
        }

        resp = self.session.post(url, json=payload)
        return resp.json()["data"]["nonce"]

    def sign_message(self, nonce):
        message = f"Nonce: {nonce}"
        message_encoded = encode_defunct(text=message)
        signed_message = self.web3.eth.account.sign_message(
            message_encoded, private_key=self.private_key
        )
        return signed_message.signature.hex()

    def auth(self):
        nonce = self.get_nonce()
        signature = self.sign_message(nonce)

        url = "https://gcp-api.intract.io/api/qv1/auth/wallet"
        payload = {
            "namespaceTag": "EVM::EVM",
            "userAddress": self.address,
            "connector": "METAMASK::EOA",
            "isTaskLogin": False,
            "signature": signature,
            "fingerprintId": os.urandom(16).hex(),
        }

        response = self.session.post(url, json=payload)
        data = response.json()

        if not data.get("isEVMLoggedIn"):
            raise Exception(f"Authorization failed: {data}")

        logger.debug(f"{self.label} Authorization successful")
        time.sleep(random.randint(*SETTINGS.SLEEP_BETWEEN_ACTIONS))

        return True

    def get_claim_data(self):
        url = "https://gcp-api.intract.io/api/qv1/compass-nft/claim-signature"
        params = {
            "isGemsFreeClaim": False,
            "walletAddress": self.address,
            "nftId": "67161a819a40e4c9ec38fc7d",
            "chain": "base",
            "namespaceTag": "EVM::EVM",
        }

        response = self.session.get(url, params=params)
        return response.json()["claimData"]["functionParams"]

    def get_balance(self):
        balance = self.contract.functions.balanceOf(self.address).call()
        return balance

    @check_gas
    def mint(self, claim_data):
        """Function: mintWithSignature((address,address,uint256,address,string,uint256,address,uint128,uint128,bytes32), bytes)"""

        name = self.contract.functions.name().call()

        func_params = claim_data[0]
        signature = claim_data[1]

        royalty_addr = func_params["royaltyRecipient"]
        currency = func_params["currency"]

        uri = func_params["uri"]
        uid = func_params["uid"]
        validity_start = func_params["validityStartTimestamp"]
        validity_end = func_params["validityEndTimestamp"]

        # fmt: off
        req = (
            self.address,                   # to (address)
            royalty_addr,                   # royaltyRecipient (address)
            0,                              # royaltyBps (uint256)
            royalty_addr,                   # primarySaleRecipient (address)
            uri,                            # uri (string)
            0,                              # price (uint256)
            currency,                       # currency (address)
            validity_start,                 # validityStartTimestamp (uint128)
            validity_end,                   # validityEndTimestamp (uint128)
            self.web3.to_bytes(hexstr=uid)  # uid (bytes32)
        )
        # fmt: on

        contract_tx = self.contract.functions.mintWithSignature(
            req, signature
        ).build_transaction(self.get_tx_data())

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.label} mint {name}",
        )
