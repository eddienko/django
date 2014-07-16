
class ImageDict(dict):
    def __getattr__(self, name):
        return self[name]

def SortKey(item):
    k = {'J': 11, 'H': 12, 'K': 13, 'Ks': 13}
    w = item.waveband
    if w in k:
        j = k[w]
    else:
        j=99
    return j

def celeryStatus():
    try:
        from celery.task.control import inspect
        d = inspect().stats()
        if not d:
            return False
    except IOError as e:
        return False
    except ImportError as e:
        return False
    return True