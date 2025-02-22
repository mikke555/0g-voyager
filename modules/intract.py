import os
import random
import time

from eth_account.messages import encode_defunct
from tls_client import Session

import settings
from modules.config import VOYAGER_0G, VOYAGER_0G_ABI, logger
from modules.utils import check_gas
from modules.wallet import Wallet


class Intract(Wallet):
    def __init__(self, private_key, proxy, label):
        super().__init__(private_key, label)
        self.label += " Intract |"
        self.session = self.get_new_session(proxy)
        self.contract = self.get_contract(VOYAGER_0G, VOYAGER_0G_ABI)

        self.project_id = "66c904e84af02b13b2cdd831"
        self.campaign_id = "6715da4fc0c9e039a626fbe8"

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
        time.sleep(random.randint(*settings.SLEEP_BETWEEN_ACTIONS))

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
        data = response.json()

        if data.get("message") == "SuperUser not logged in":
            logger.error(f"{self.label} UNAUTHORIZED \n")
            return False

        return data["claimData"]["functionParams"]

    def get_nft_balance(self):
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
            tx_label=f"{self.label} Mint {name}",
        )

    def get_user_id(self) -> str:
        url = f"https://gcp-api.intract.io/api/qv1/auth/get-user?projectId={self.project_id}"
        response = self.session.get(url)
        quest_user_id = response.json()["_id"]

        self.session.headers.update({"Questuserid": quest_user_id})
        return quest_user_id

    def set_primary_identity(self):
        url = "https://gcp-api.intract.io/api/qv1/auth/set-primary-task-identity"

        payload = {"identity": self.address, "namespaceTag": "EVM::EVM"}

        response = self.session.post(url, json=payload)
        data = response.json()

        if data.get("isSuccess"):
            logger.debug(f"{self.label} Primary wallet set to {self.address}")

        return True if data.get("isSuccess") else False

    def verify_task(self, task):
        url = "https://gcp-api.intract.io/api/qv1/task/verify-v2"
        payload = {
            "campaignId": self.campaign_id,
            "taskId": task["id"],
            "userInputs": {},
            "userVerificationData": {},
        }

        response = self.session.post(url, json=payload)
        data = response.json()

        if data.get("verified"):
            logger.success(f"{self.label} Verified: {task['name']}")
        elif data.get("message"):
            logger.warning(f"{self.label} {data['message']}")

        return True if data.get("verified") else False

    def fetch_journey(self):
        url = "https://gcp-api.intract.io/api/qv1/journey/fetch"
        params = {
            "campaignId": self.campaign_id,
            "channelCode": "DEFAULT",
            "userRef": "null",
            "questUserId": self.session.headers.get("Questuserid"),
            "utm_source": "",
            "utm_medium": "",
            "utm_campaign": "",
            "referrer": "",
            "sessionId": random.randint(100000000, 999999999),
            "lastInternalUrl": "DIRECT",
            "isTelegramMiniApp": "false",
        }

        if settings.USE_REF:
            params.update(
                {
                    "referralCode": settings.REF_CODE,
                    "referralSource": "QUEST_PAGE",
                    "referralLink": "https://quest.intract.io/quest/6715da4fc0c9e039a626fbe8?campaign_initiator_type=explore&card_position=0",
                }
            )

        resp = self.session.get(url, params=params)
        data = resp.json()

        if data.get("isActive") != True:
            logger.error(f"Activate journey error: {resp.text}")

        logger.debug(f"{self.label} Collected XP: {data.get('xp')}")
        time.sleep(random.randint(5, 10))

        return data
