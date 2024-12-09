import random

import settings
from modules.config import logger
from modules.intract import Intract
from modules.utils import sleep


def main():
    with open("keys.txt", "r") as f:
        keys = [row.strip() for row in f]

    with open("proxies.txt") as file:
        proxies = [f"http://{row.strip()}" for row in file]

    if settings.SHUFFLE_WALLETS:
        random.shuffle(keys)

    total_keys = len(keys)
    logger.success(f"Loaded {total_keys} wallet(s) \n")

    for index, key in enumerate(keys, start=1):
        label = f"[{index}/{total_keys}]"
        proxy = random.choice(proxies)

        client = Intract(key, proxy, label)

        if not settings.ALLOW_MULTIPLE_MINTS:
            balance = client.get_balance()
            if balance > 1:
                logger.warning(f"{label} this wallet already minted {balance} nft(s)")
                continue

        if client.auth():
            claim_data = client.get_claim_data()
            status = client.mint(claim_data)

            if status and index < total_keys:
                sleep(*settings.SLEEP_BETWEEN_WALLETS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")
