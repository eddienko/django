import psycopg2


import os, sys
import math
import glob
import datetime

from django.db import IntegrityError, transaction
from django.utils.timezone import utc

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "casu.settings")
os.environ.setdefault("PYTHONPATH", "/Users/eglez/Development/Django/casu")

sys.path.append("/Users/eglez/Development/Django/casu")

from imagedb.models import Image, Collection


from configobj import ConfigObj
from os.path import expanduser

config = ConfigObj(expanduser("~/.configobj"))

# VST

query="""
select filename, filepath, obj as objname, chipno as extno,
filtname as waveband, telescop as telescope, instrume as instrument,
'ESO'::text as origin, 'Paranal'::text as observatory,
image.mjd as mjd, image.exptime as exptime,
seeing*pixsize as seeing, ellipticity as elliptic,
amend as airmass, maglim, magzpt, magzerr as magzrr,
skynoise, naxis1, naxis2, ctype1, ctype2, crval1, crval2, crpix1, crpix2,
cd1_1 as cd11, cd1_2 as cd12, cd2_1 as cd21, cd2_2 as cd22,
cenra, cendec, coords as cencoords, pixsize as pixscl, ''::text as addinfo, groupname, 21::int as seqn, 
true as hascat, image.dateobs as dateobs, obsname, prog
 from image 
join extension on (image.id=extension.image_id)
join filter on (image.insfilter_id=filter.id)
JOIN qc ON extension.id = qc.extension_id
JOIN programme ON image.programme_id = programme.id
limit 1000 offset %d;
"""

src = "host=%(host)s dbname=spvst user=%(user)s port=%(port)s password=%(password)s" % config['apm49']
dst = "host=%(host)s dbname=imagedb user=%(user)s port=%(port)s password=%(password)s" % config['apm14']

sconn = psycopg2.connect(src)
scursor = sconn.cursor()

programmes={'177.A-3011': 'ATLAS', '177.D-3023': 'VPHAS', '177.A-3018': 'KIDS', '179.A-2006': 'VIDEO', '179.A-2005': 'UltraVISTA', '179.B-2002': 'VVV'}

flag = True
i = -1
while flag:
    i = i + 1
    scursor.execute(query % (i*1000))
    res = scursor.fetchall()
    if res==[]:
        flag = False
        break
    print i, len(res)
    columns = [c.name for c in scursor.description]

    for item in res:
        data = {}
        for k,v in zip(columns, item):
            data[k] = v
            
        survey = ""
        field = ""
        obsname = data.pop('obsname')
        prog = data.pop('prog')
        if prog in programmes:
            survey = programmes[prog]
        else:
            survey='OTHER'
            
        field = survey
            
        try:
            req = Collection.objects.get(field=field, survey=survey, filter=data['waveband'], instrument='OMEGACAM', telescope='VST')
        except:
            print "***", obsname, prog, data
            continue
        
        data['collection_id'] = req.id
        data['dateobs'] = data['dateobs'].replace(tzinfo=utc)
        
        img = Image(**data)
        img.save()
            
