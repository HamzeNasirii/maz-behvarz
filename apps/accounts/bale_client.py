import requests
from django.conf import settings


def _base_url():
    return f"https://tapi.bale.ai/bot{settings.BALE_BOT_TOKEN}"


def send_message(chat_id, text):
    response = requests.post(
        f"{_base_url()}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10,
    )
    response.raise_for_status()
    return response.json()

def send_invoice(chat_id, title, description, payload, prices, photo_url=None):
    from django.conf import settings

    body = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "provider_token": settings.BALE_PROVIDER_TOKEN,
        "prices": prices,
    }
    if photo_url:
        body["photo_url"] = photo_url

    response = requests.post(f"{_base_url()}/sendInvoice", json=body, timeout=10)
    response.raise_for_status()
    return response.json()


def answer_pre_checkout_query(pre_checkout_query_id, ok, error_message=None):
    body = {"pre_checkout_query_id": pre_checkout_query_id, "ok": ok}
    if not ok and error_message:
        body["error_message"] = error_message

    response = requests.post(f"{_base_url()}/answerPreCheckoutQuery", json=body, timeout=10)
    if not response.ok:
        raise RuntimeError(f"answerPreCheckoutQuery failed ({response.status_code}): {response.text}")
    return response.json()


def inquire_transaction(transaction_id):
    response = requests.get(
        f"{_base_url()}/inquireTransaction", params={"transaction_id": transaction_id}, timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_updates(offset=None, timeout=30):
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    response = requests.get(f"{_base_url()}/getUpdates", params=params, timeout=timeout + 10)
    response.raise_for_status()
    return response.json()