import json
import random
import re
import uuid
from collections import deque
from functools import reduce
from pprint import pprint

# Request generation

request_settings = {
        'imp_settings': {
            'imp_count': 1,
            'impression_type': 'native'
        }
    }


PORT = '8080'
LOCALHOST = "localhost"

class RequestProvider(object):
    def __init__(self, post_path):
        self.post_path = post_path
        self.request_post_url = self.build_url(self.post_path)
        self.request_list = deque([3])

    def get_sent_win_notice_url(self, bid):
        return None

    def pop_winner_notice(self):
        try:
            return self.request_list.pop()
        except IndexError:
            return None

    def determine_if_won(self, bid_price):
        # Figure out if won
        priceA = random.random() * 0.2  # range: (0, 0.2) to win bids often
        priceB = random.random() * 0.2
        market_first_price = max(priceA, priceB)
        market_second_price = min(priceA, priceB)
        won_auction = bid_price > market_first_price
        return won_auction, market_first_price, market_second_price

    @staticmethod
    def build_url(path, hostname=LOCALHOST, port=PORT):
        return "http://" + hostname + ":" + port + path


class Bidswitch(RequestProvider):
    def __init__(self):
        super(Bidswitch, self).__init__('/auctions/bidswitch/')

    def get_sent_win_notice_url(self, bid):
        adm = bid.get('adm', '')
        # banner:
        if 'iframe' in adm:
            regex = r'<*?src="(.*?)"'
            match = re.search(regex, adm)
            win_notice_url = match.group(1)
        # native
        elif 'native' in bid.get('ext', {}):  # or 'native' in adm
            win_notice_url = bid['nurl']
        # video
        elif 'VAST' in adm:
            regex = r'<VASTAdTagURI><!\[CDATA\[(.*)\]\]></VASTAdTagURI>'
            match = re.search(regex, adm)
            win_notice_url = match.group(1)
        else:
            print("Couldn't extract win notice url from adm field. Won't notify of the win!")
        return win_notice_url


bidswitch = Bidswitch()

with open('mobile-devices.json', 'r') as mobiles_file:
    mobiles = json.load(mobiles_file)

with open('desktop-devices.json', 'r') as desktops_file:
    desktops = json.load(desktops_file)

with open('native_imps.json', 'r') as native_requests_file:
    native_impressions = json.load(native_requests_file)

with open('sites.json', 'r') as sites_file:
    sites = json.load(sites_file)


def gen_request(provider, request_settings):
    request, likelihoods = gen_request_data(request_settings)
    past_winner_notice = provider.pop_winner_notice()
    if past_winner_notice is not None:
        request['ext'] = past_winner_notice
    total_likelihood = reduce(lambda x, y: x * y, likelihoods)
    return {
        'likelihood': total_likelihood,
        'request': request
    }


def gen_request_data(request_settings):
    likelihoods, impressions = [], []
    device = gen_device()
    user = gen_user()
    site = gen_site()
    imp_settings = request_settings['imp_settings']
    imp_count = imp_settings['imp_count']
    for i in range(imp_count):
        imp_struct = gen_impression(i, imp_settings)
        impressions.append(imp_struct['imp'])
        likelihoods.append(imp_struct['likelihood'])

    likelihoods.append(device['likelihood'])
    likelihoods.append(user['likelihood'])
    likelihoods.append(site['likelihood'])

    new_id = uuid.uuid4().hex
    request = {
        "id": new_id,
        "at": "2",
        "tmax": "120",
        "imp": impressions,
        "site": site['data'],
        "device": device['data'],
        "user": user['data']
    }
    return request, likelihoods


user_ids = [uuid.uuid4().hex for _ in range(5)]


def gen_user():
    age = int(random.random() * 50) + 15
    new_id = random.choice(user_ids)
    likelihood = random.random()
    user_struct = {
        "likelihood": likelihood,
        "data": {
            "id": new_id,
            "age": age,
            "ext": {
                "sessiondepth": 1
            }
        }
    }
    return user_struct


def gen_device():
    if random.randint(0, 1) == 1:
        device = random.choice(mobiles)
    else:
        device = random.choice(desktops)
    device['data']['ip'] = '149.18.58.219'
    return device


def gen_banner(n):
    format = gen_hw()
    banner_imp_struct = {
        'likelihood': format['likelihood'],
        'imp': {
            "id": n,
            "tagid": "61653",
            "banner": {
                "w": format['w'],
                "h": format['h'],
                "battr": [3, 9, 14018, 14014, 14, 13, 10, 14015, 8, 14019, 2, 5],
                "api": []
            },
            "iframebuster": []
        }
    }
    return banner_imp_struct


def gen_native(n):
    native = random.choice(native_impressions)
    native['id'] = n
    native['tagid'] = "61653"
    native['iframebuster'] = []
    native_imp_struct = {
        'likelihood': 1 / len(native_impressions),
        'description': native['description'],
        'imp': native
    }
    return native_imp_struct


def gen_impression(n, imp_settings):
    impression_type = imp_settings['impression_type']
    coin_toss = random.choice(['banner', 'native']) if impression_type is None else impression_type
    if coin_toss == 'banner':
        print("Banner impression was chosen")
        return gen_banner(n)
    else:
        native_imp_struct = gen_native(n)
        print("Native impression was chosen")
        print("Native Description: " + native_imp_struct['description'])
        return native_imp_struct


def gen_hw():
    formats = [
        {"h": 250, "w": 300, "likelihood": 1},
        # {"h" : 90, "w" : 720, "likelihood" : 0.0005},
        # {"h" : 600, "w" : 300, "likelihood" : 0.002},
        # {"h" : 1050, "w" : 300, "likelihood" : 0.003},
        # {"h" : 90, "w" : 970, "likelihood" : 0.002}
    ]
    return random.choice(formats)


def gen_site():
    return random.choice(sites)

pprint(gen_request(bidswitch, request_settings))