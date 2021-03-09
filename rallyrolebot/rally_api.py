import requests

from constants import *

# TODO: Discuss specific details with Calvin before making changes


def return_req_error(url, result):
    print("Request error!")
    print(f"Url: {url}")
    print(f"Status Code: {result.status_code}")
    print(f"JSON result type: {type(result.json())}")
    print(result.json())


def get_balances(rally_id):
    url = BASE_URL + "/users/rally/" + rally_id + "/balance"
    result = requests.get(url)
    if result.status_code != 200:
        return_req_error(url, result)
        return None
    return result.json()


def get_balance_of_coin(rally_id, coin_name):
    balances = get_balances(rally_id)
    if balances is None:
        return 0.0
    find_balance_of_coin(coin_name, balances)


def find_balance_of_coin(coin_name, balances):
    if not balances:
        return 0.0
    for coin_balance in balances:
        if coin_balance[COIN_KIND_KEY] == coin_name:
            return float(coin_balance[COIN_BALANCE_KEY])


def valid_coin_symbol(coin_name):
    url = BASE_URL + "/creator_coins/" + coin_name + "/price"
    result = requests.get(url)
    if result.status_code != 200:
        return False
    return result.json()["symbol"] is not None


def get_current_price(coin_name):
    url = BASE_URL + "/creator_coins/" + coin_name + "/price"
    result = requests.get(url)
    if result.status_code != 200:
        return_req_error(url, result)
        return False
    return result.json()


def get_coin_image_url(coin):
    url = BASE_URL + "/creator_coins/"
    result = requests.get(url)
    for data in result.json():
        if data['coinSymbol'] == coin:
            return data['coinImagePath']

    return ''


def get_coin_summary(coin):
    url = BASE_URL + "/creator_coins/" + coin + '/summary'
    result = requests.get(url)
    if result.status_code != 200:
        return_req_error(url, result)
        return False

    return result.json()


def get_creator_coins():
    url = BASE_URL + "/creator_coins"
    result = requests.get(url)
    if result.status_code != 200:
        return_req_error(url, result)
        return False

    return result.json()


def get_coin_rewards(coin):
    url = BASE_URL + "/creator_coins/" + coin + '/rewards'
    result = requests.get(url)
    if result.status_code != 200:
        return_req_error(url, result)
        return False

    return result.json()


"""
    TODO: Add 24h and 30d price data
"""


def get_price_data(coin_name):
    data = get_current_price(coin_name)
    return {
        "current_price": data["priceInUSD"],
        "price_change_percentage_24h": -17,
        "price_change_percentage_30d": 43,
    }
