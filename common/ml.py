import pickle


def pickle_save(key, data):
    pickle.dump(data, open('cache/' + key + '.p', 'wb'))


def pickle_load(key):
    return pickle.load(open('cache/' + key + '.p', 'rb'))


def one_hot(idx: int, size: int):
    ret = [0]*size
    ret[idx] = 1
    return ret


