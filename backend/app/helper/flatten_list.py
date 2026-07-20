from itertools import chain


def flatten_list(nested_list) -> list:
    return list(chain.from_iterable(nested_list))
