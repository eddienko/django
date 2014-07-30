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

# VISTA

query="""
select filename, filepath, obj as objname, chipno as extno,
filtname as waveband, telescop as telescope, instrume as instrument,
'ESO'::text as origin, 'Paranal'::text as observatory,
image.mjd as mjd, image.exptime as exptime,
seeing*pixsize as seeing, ellipticity as elliptic,
amend as airmass, maglim, magzpt, magzerr as magzrr,
skynoise, naxis1, naxis2, ctype1, ctype2, crval1, crval2, crpix1, crpix2,
cd1_1 as cd11, cd1_2 as cd12, cd2_1 as cd21, cd2_2 as cd22,
cenra, cendec, coords as cencoords, pixsize as pixscl, ''::text as addinfo, groupname, 22::int as seqn,
true as hascat, image.dateobs as dateobs, obsname, prog
 from image 
join extension on (image.id=extension.image_id)
join filter on (image.insfilter_id=filter.id)
JOIN qc ON extension.id = qc.extension_id
JOIN programme ON image.programme_id = programme.id
where 
is_tile=true limit 1000 offset %d;
"""

src = "host=%(host)s dbname=vista user=%(user)s port=%(port)s password=%(password)s" % config['apm45']
dst = "host=%(host)s dbname=imagedb user=%(user)s port=%(port)s password=%(password)s" % config['apm14']

sconn = psycopg2.connect(src)
scursor = sconn.cursor()

#dconn = psycopg2.connect(dst)
#dcursor = dconn.cursor()

programmes={'179.A-2010': 'VHS', '179.A-2004': 'VIKING', '179.B-2003': 'VMC', '179.A-2006': 'VIDEO', '179.A-2005': 'UltraVISTA', '179.B-2002': 'VVV'}

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
            
        if survey=='VHS':
            if obsname.find('DES')>0: field='DES'
            elif obsname.find("ATL")>0: field="ATLAS"
            elif obsname.find("GPS")>0: field="GPS"
        elif survey=='VIKING':
            if obsname.find('ngp')>0: field='NGP'
            elif obsname.find('sgp')>0: field='SGP'
            elif obsname.find('gama')>0: field='GAMA'
        elif survey=='VMC':
            if obsname.find('smc')>0: field='SMC'
            elif obsname.find('lmc')>0: field='LMC'
            elif obsname.find('bridge')>0: field='BRIDGE'
            elif obsname.find('stream')>0: field='STREAM'
        elif  survey=='VIDEO':
            if obsname.find('xmm')>0: field='XMM'
            elif obsname.find('cdfs')>0: field='CDFS'
            elif obsname.find('ES1')>0: field='ES'
        elif  survey=='VVV':
            if obsname[0]=='b': field='BULGE'
            elif obsname[0]=='d': field='DISK'
            else: field='BULGE'
        else:
            survey="PPI"
            field = "PPI"
            
        try:
            req = Collection.objects.get(field=field, survey=survey, filter=data['waveband'], instrument='VIRCAM', telescope='VISTA')
        except:
            print "***", obsname, prog, data
            continue
        
        data['collection_id'] = req.id
        data['dateobs'] = data['dateobs'].replace(tzinfo=utc)
        
        img = Image(**data)
        img.save()
            
