import collections
import copy
import json
from collections import Counter
from pprint import pprint

from ua_parser import user_agent_parser


def read_lines(dataset):
    """Yields instances from a file like object by knowing the file structure"""
    for line in dataset:
        obs = json.loads(line)
        converted = int(obs['converted'])
        winning_bid = float(obs['winning_prices'][0])
        req = obs['req']
        yield converted, winning_bid, req


requests = []
with open('dataset.dsv', 'r') as f:
    for _, _, req in read_lines(f):
        requests.append(req)


def split_imp_requests(request):
    """Yields requests with a single imp object at the 'imp' key"""
    request = copy.deepcopy(request)
    imps = request['imp']
    if len(imps) == 1:
        request['imp'] = imps[0]
        yield request
    elif len(imps) > 1:
        for imp in imps:
            req_copy = copy.deepcopy(request)
            req_copy['imp'] = imp
            yield req_copy


def flatten(nested_dict, parent_key='', sep='.'):
    """Turns a nested dict with dict values into a 'flat' dict where path to values in nested dicts is
    contained in the top level dict and keys reflect the path to the value delimited by sep."""
    key_value_pairs = []
    for key, val in nested_dict.items():
        new_key = parent_key + sep + key
        if isinstance(val, collections.MutableMapping):
            # Add key_value pairs generated from the map at value
            key_value_pairs.extend(flatten(val, new_key, sep=sep).items())
        else:
            key_value_pairs.append((new_key, val))
    key_value_pairs = map(lambda t: (t[0][len(sep):] if t[0].startswith(sep) else t[0], t[1]), key_value_pairs)
    return dict(key_value_pairs)


def flatten_lists(flat_dict, sep="."):
    """Counts members of an iterable and adds each member to the dict at distict key"""
    d = copy.deepcopy(flat_dict)
    d2 = {}
    for key, val in d.items():
        if isinstance(val, list):
            iterable_counter = Counter(val)
            for elem_name, count in iterable_counter.items():
                d2[key + sep + str(elem_name)] = count
        else:
            d2[key] = val
    return d2


def onehot_categorical_feats(request):
    """Turns request string values into 1s and appends the string to the key."""
    request = copy.deepcopy(request)
    for k, v in request.items():
        if isinstance(v, str):
            del request[k]
            request[k + '_' + v] = 1
    return request


def add_ua_features(request):
    request = copy.deepcopy(request)
    device = request['device'] = request.get('device', {})
    ua = device['ua'] = device.get('ua')
    if ua is not None:
        parsed_ua = user_agent_parser.Parse(ua)
        flat_ua = flatten(parsed_ua)
        flat_ua.pop('string', None)
        flat_ua.pop('user_agent_minor', None)
        flat_ua.pop('user_agent_patch', None)
        flat_ua.pop('os_patch', None)
        flat_ua.pop('os_patch_minor', None)
        device['ua'] = flat_ua
        return request
    else:
        return request


def usefull_feats(request):
    """Filters the dict for useful keys"""
    result_dict = {}
    for key, val in request.items():
        if any([key.startswith(prefix) for prefix in ['device', 'imp', 'site', 'user', 'ua']]):
            result_dict[key] = val
    return result_dict


def flat_and_map(request_dict):
    for request in split_imp_requests(request_dict):
        # add/remove feats:
        flat_dict = add_ua_features(request)
        flat_dict = usefull_feats(flat_dict)
        # flatten:
        flat_dict = flatten(flat_dict)
        flat_dict = flatten_lists(flat_dict)
        flat_dict = onehot_categorical_feats(flat_dict)
        yield flat_dict


if __name__ == '__main__':
    pprint(requests[0])
    for x in flat_and_map(requests[0]):
        pprint(x)
