

from socket import gethostname


HOSTNAME=gethostname()

if (HOSTNAME=='apm14.ast.cam.ac.uk'):
    CUTOUT='/Users/eglez/Development/Django/casu/bin/cutout'
    REQUESTS='/Users/eglez/Development/Django/casu/imagedb/data/requests'
    CACHE='/Users/eglez/Development/Django/casu/imagedb/data/cache'
elif (HOSTNAME=='apm38.ast.cam.ac.uk'):
    CUTOUT=''
    REQUESTS='/Users/eglez/Django/casu/imagedb/data/requests'
    CACHE='/Users/eglez/Django/casu/imagedb/data/cache'
