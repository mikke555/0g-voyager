import random

import questionary

import settings
from modules.config import logger, tasks
from modules.intract import Intract
from modules.utils import random_sleep, sleep
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
        choices=[
            "Ming 0g Voyager NFT and claim tasks on Intract",
            "Send A0GI token to a random wallet",
        ],
    ).ask()

    for index, key in enumerate(keys, start=1):
        total_keys = len(keys)
        label = f"[{index}/{total_keys}]"
        status = None

        try:
            if action == "Ming 0g Voyager NFT and claim tasks on Intract":
                proxy = random.choice(proxies) if settings.USE_PROXY else None
                client = Intract(key, proxy, label)

                balance = client.get_nft_balance()

                if settings.ALLOW_MULTIPLE_MINTS or balance < 1:
                    claim_data = client.get_claim_data()
                    client.mint(claim_data)
                else:
                    logger.warning(
                        f"{label} This wallet already minted {balance} nft(s)"
                    )

                if not client.auth():
                    return

                if not client.get_user_id():
                    return

                if not client.fetch_journey():
                    return

                random.shuffle(tasks)

                for task in tasks:
                    if task["id"] == "67162a6fc0c9e039a629d39d":
                        client.set_primary_identity()
                        random_sleep(5, 10)

                    status = client.verify_task(task)
                    if status:
                        random_sleep(5, 20)

                client.fetch_journey()
                sleep(*settings.SLEEP_BETWEEN_WALLETS)

            elif action == "Send A0GI token to a random wallet":
                wallet = Wallet(key, label, chain="0g")
                status = wallet.send_native_token_to_a_rand_wallet(
                    settings.SEND_VALUE_PERCENTAGE
                )

            if status and index < total_keys:
                sleep(*settings.SLEEP_BETWEEN_WALLETS)

        except Exception as error:
            logger.error(f"{label} Error processing wallet: {error} \n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Cancelled by user")
