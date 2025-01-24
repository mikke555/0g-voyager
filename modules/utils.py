import csv
import os
import random
import time
from datetime import datetime

from tqdm import tqdm

import settings
from modules.config import logger, mainnet_client


def random_sleep(min_time, max_time):
    duration = random.randint(min_time, max_time)
    time.sleep(duration)


def sleep(from_sleep, to_sleep):
    x = random.randint(from_sleep, to_sleep)
    desc = datetime.now().strftime("%H:%M:%S")

    for _ in tqdm(
        range(x), desc=desc, bar_format="{desc} | Sleeping {n_fmt}/{total_fmt}"
    ):
        time.sleep(1)
    print()


def get_gas():
    try:
        gas_price = mainnet_client.eth.gas_price
        gwei = mainnet_client.from_wei(gas_price, "gwei")
        return gwei
    except Exception as error:
        logger.error(error)


def wait_gas():
    while True:
        gas = get_gas()

        if gas > settings.MAX_GWEI:
            logger.info(f"Current gwei {gas} > {settings.MAX_GWEI}")
            random_sleep(60, 60)
        else:
            break


def check_gas(func):
    def wrapper(*args, **kwargs):
        wait_gas()
        return func(*args, **kwargs)

    return wrapper


def write_to_csv(path, headers, data):
    directory = os.path.dirname(path)

    if directory:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    with open(path, mode="a", newline="") as file:
        writer = csv.writer(file)

        if file.tell() == 0:
            writer.writerow(headers)

        writer.writerow(data)
