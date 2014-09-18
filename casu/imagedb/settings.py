

from socket import gethostname


HOSTNAME=gethostname()

if (HOSTNAME=='apm14.ast.cam.ac.uk'):
    CUTOUT='/Users/eglez/Development/Django/casu/bin/cutout'
    REQUESTS='/Users/eglez/data/ImageDB/Release/requests'
    CACHE='/Users/eglez/data/ImageDB/Release/cache'
elif (HOSTNAME=='apm38.ast.cam.ac.uk'):
    CUTOUT=''
    REQUESTS='/Users/eglez/data/ImageDB/Release/requests'
    CACHE='/Users/eglez/data/ImageDB/Release/cache'
