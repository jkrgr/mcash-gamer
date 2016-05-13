import requests
import secret


mcash_url = "https://api.mca.sh/merchant/v1/"
gamer_url = "https://krgr.pythonanywhere.com/"
headers = {
    "X-Mcash-Merchant":secret.merchant_id,
    "X-Mcash-User": secret.merchant_user,
    "Authorization": "SECRET %s" % secret.secret,
    "Content-Type": "application/json",
    "Accept": "application/vnd.mcash.api.merchant.v1+json"
    }



def create_shortlink(callback_uri):
    data = {
        "callback_uri": gamer_url + "scan_callback"
        }
    url = mcash_url + "shortlink/"
    return requests.post(url, headers=headers, json=data)


def get_shortlink(shortlink_id):
    url = mcash_url + "shortlink/%s" % shortlink_id
    return requests.get(url)


def create_payment_request(token, amount, text, game_id, pos_tid):
    data = {
      "customer": token,
      "amount": amount,
      "currency": "NOK",
      "required_scope": "openid profile",
      "text": text,
      "action": "sale",
      "expires_in": 260000,
      "callback_uri": gamer_url + "pay_callback",
      "allow_credit": True,
      "pos_id": game_id,
      "pos_tid": pos_tid
    }
    url = mcash_url + "payment_request/"

    return requests.post(url, headers=headers, json=data)


def capture_payment_request(tid):
    pass