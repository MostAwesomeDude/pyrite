def remap_keys(m, d):
    """
    Copy values in d to a new dictionary, using m as the mapping of old keys
    to new keys.
    """

    return dict((v, d[k]) for k, v in m.items())
