import os
import sys
import math
import glob
import json

from django.db import IntegrityError, transaction


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "casu.settings")
os.environ.setdefault("PYTHONPATH", "/Users/eglez/Development/Django/casu")

sys.path.append("/Users/eglez/Development/Django/casu")

from imagedb.models import Image, Collection

cnum = 1

for item in open('collections.json'):
    if len(item)<1:
        continue
        
    if item[0]=='#':
        print item.strip()
        continue
    
    dd = json.loads(item)
    dd['cnum'] = cnum
    
    res = Collection.objects.filter(field = dd['field'], survey = dd['survey'], telescope = dd['telescope'], instrument = dd['instrument'], filter = dd['filter'])
    if res.count() == 0:
        Collection(**dd).save()
    else:
        dd['cnum'] = res[0].cnum
        res.update(**dd)
        
    print dd
    cnum = cnum + 1
    
    #if Collection.objects.filter(cnum = dd['cnum']).count()==0:
    #    Collection(**dd).save()
    #else:
    #    Collection.objects.filter(cnum = dd['cnum']).update(**dd)
    #print dd