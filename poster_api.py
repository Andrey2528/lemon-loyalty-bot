import requests
from config import POSTER_TOKEN, POSTER_URL

def get_clients():
    r = requests.get(POSTER_URL + "clients.getClients", params={"token": POSTER_TOKEN})
    return r.json().get("response", [])

def find_client_by_phone(phone):
    clients = get_clients()
    for c in clients:
        if phone in c.get("phone", ""):
            return c
    return None

def update_client(client_id, bonus):
    r = requests.post(POSTER_URL + "clients.updateClient", data={
        "token": POSTER_TOKEN,
        "client_id": client_id,
        "discount": bonus
    })
    return r.json()

def get_transactions(client_id):
    r = requests.get(POSTER_URL + "clients.getClientTransactions", params={
        "token": POSTER_TOKEN,
        "client_id": client_id
    })
    return r.json().get("response", [])
