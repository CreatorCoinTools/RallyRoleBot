import requests

from constants import *


def return_req_error(url, result):
    print("Request error!")
    print(f"Url: {url}")
    print(f"Status Code: {result.status_code}")
    print(f"JSON result type: {type(result.json())}")
    print(result.json())


def get_coins_list():
    url = COINGECKO_API_URL + "/coins/list"
    result = requests.get(url)
    if result.status_code != 200:
        return_req_error(url, result)
        return False

    return result.json()


def valid_coin(symbol):
    symbol = symbol.lower()

    coins = get_coins_list()
    if coins is False:
        return False

    for keyval in coins:
        if symbol == keyval["symbol"].lower():
            return True
    return False


def get_id_from_symbol(symbol):
    symbol = symbol.lower()

    coins = get_coins_list()
    if coins is False:
        return False

    for keyval in coins:
        if symbol == keyval["symbol"].lower():
            return keyval["id"]
    return False


def get_price_data(symbol):
    coin_id = get_id_from_symbol(symbol)
    if coin_id is False:
        return False

    url = COINGECKO_API_URL + "/coins/" + coin_id
    result = requests.get(url)
    if result.status_code != 200:
        return_req_error(url, result)
        return False

    result = result.json()["market_data"]
    return {
        "current_price": result["current_price"]["usd"],
        "price_change_percentage_24h": result["price_change_percentage_24h"],
        "price_change_percentage_30d": result["price_change_percentage_30d"],
    }
