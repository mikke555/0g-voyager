import random

import questionary

import settings
from modules.config import logger
from modules.intract import Intract
from modules.utils import sleep
from modules.wallet import Wallet


def main():
    with open("keys.txt", "r") as f:
        keys = [row.strip() for row in f]

    with open("proxies.txt") as file:
        proxies = [f"http://{row.strip()}" for row in file]

    if not proxies and settings.USE_PROXY:
        logger.warning("No proxies found. Please add proxies to proxies.txt")
        return

    if settings.SHUFFLE_WALLETS:
        random.shuffle(keys)

    action = questionary.select(
        "Select action",
        choices=["Ming 0g Voyager NFT", "Send token to a random wallet"],
    ).ask()

    for index, key in enumerate(keys, start=1):
        total_keys = len(keys)
        label = f"[{index}/{total_keys}]"
        status = None

        try:
            if action == "Ming 0g Voyager NFT":
                proxy = random.choice(proxies) if settings.USE_PROXY else None
                client = Intract(key, proxy, label)

                if not settings.ALLOW_MULTIPLE_MINTS:
                    balance = client.get_balance()
                    if balance > 1:
                        logger.warning(
                            f"{label} This wallet already minted {balance} nft(s), skipping \n"
                        )
                        continue

                if client.auth():
                    claim_data = client.get_claim_data()
                    status = client.mint(claim_data)

            elif action == "Send token to a random wallet":
                wallet = Wallet(key, label, chain="0g")
                status = wallet.send_native_token_to_a_rand_wallet(
                    settings.SEND_VALUE_PERCENTAGE
                )

            if status and index < total_keys:
                sleep(*settings.SLEEP_BETWEEN_WALLETS)

        except KeyboardInterrupt:
            raise Exception
        except Exception as error:
            logger.error(f"{label} Error processing wallet: {error} \n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Cancelled by user")
