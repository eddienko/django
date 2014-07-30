import os, sys
import math
import glob
import pyfits
import datetime

import ephem
from kapteyn import wcs

from django.db import IntegrityError, transaction
from django.utils.timezone import utc

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "casu.settings")
os.environ.setdefault("PYTHONPATH", "/Users/eglez/Development/Django/casu")

sys.path.append("/Users/eglez/Development/Django/casu")

from imagedb.models import Image, Collection

translate = {
    'objname': 'OBJECT', 'waveband': 'CHNLNUM', 
    'telescope': 'TELESCOP', 'instrument': 'INSTRUME', 
    'naxis1': 'NAXIS1', 'naxis2': 'NAXIS2',
    'ctype1': 'CTYPE1', 'ctype2': 'CTYPE2',
    'crpix1': 'CRPIX1', 'crpix2': 'CRPIX2',
    'crval1': 'CRVAL1', 'crval2': 'CRVAL2',
    'cd11': 'CD1_1', 'cd21': 'CD2_1', 'cd12': 'CD1_2', 'cd22': 'CD2_2'
}

wcskeys=['CTYPE1','CTYPE2','CRVAL1','CRVAL2','CRPIX1','CRPIX2','CD1_1','CD2_2', 'CD2_1','CD1_2','PV2_1','PV2_2','PV2_3','PV2_4','PV2_5','NAXIS','NAXIS1','NAXIS2', 'CDELT1', 'CDELT2', 'CROTA1', 'CROTA2']

def runFileFilter(items):
    """Filters the list to return only valid files to ingest."""
    
    # Filter out catalogue and confidence maps
    return [e for e in items if e.find('.fit')>0]


def ingestImageHeader(hdr):
    
    data = {}
    
    for field in Image._meta.fields:
        if field.name in translate:
            if translate[field.name] in hdr:
                data[field.name] = hdr[translate[field.name]]
            
    return data

def fixHeader(hdr):
    if "CDELT1" in hdr:
        cdelt1 = hdr.pop('CDELT1')
        cdelt2 = hdr.pop('CDELT2')
        if "CROTA2" in hdr:
            crota = math.radians(float(hdr.pop("CROTA2")))
        elif "CROTA1" in hdr:
            crota = math.radians(float(hdr.pop("CROTA1")))
        else:
            crota = 0.0
            
        hdr["CD1_1"] = cdelt1 * math.cos(crota)
        hdr["CD1_2"] = -cdelt2 * math.sin(crota)
        hdr["CD2_1"] = cdelt1 * math.sin(crota)
        hdr["CD2_2"] = cdelt2 * math.cos(crota)
    
@transaction.atomic
def ingestFile(fitsFile):
    print fitsFile
    fileHandler = pyfits.open(fitsFile)
    imageHdu = fileHandler[1]
    
    d0 = ingestImageHeader(fileHandler[0].header)
    
    try:
        d0['dateobs'] = datetime.datetime.strptime(fileHandler[1].header['DATE_OBS'][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=utc)
    except:
        pass
    
    i=0
    for extHdr in fileHandler[1:]:
    
        data = ingestImageHeader(extHdr.header)
        i = i + 1
        data.update(d0)
    

        # Extract the relevant keywords from the header
        header = {}
        header['NAXIS'] = 2
        for k in wcskeys:
            if k in extHdr.header:
                header[k]=extHdr.header[k]
                
        fixHeader(header)
        
        # Construct WCS structure and create header of stamp
        w = wcs.Projection(header)
        a, d = w.crval
        x1, y1 = w.topixel((a,d))
        x2, y2 = w.topixel((a,d+1/60.))
        scl = 1./60./math.sqrt((x2-x1)**2+(y2-y1)**2)
        x = fileHandler[1].header['NAXIS1']
        y = fileHandler[1].header['NAXIS2']
        cenra, cendec = w.toworld((x,y))
        eq = ephem.Equatorial(math.radians(cenra), math.radians(cendec), epoch=ephem.J2000)
        sra = '%s' % eq.ra
        sra = '%02d:%02d:%05.2f' % tuple(map(float, sra.split(':')))
        sdec = '%s' % eq.dec
        sdec = '%+03d:%02d:%04.1f' % tuple(map(float, sdec.split(':')))
        if eq.dec<0:
            sdec='-'+sdec[1:]
        cencoords = '%s %s' % (sra, sdec)

        dd = {'filename': os.path.basename(fitsFile),
              'filepath': os.path.dirname(fitsFile),
              'extno': i,
              'cenra': cenra,
              'cendec': cendec, 
              'cencoords': cencoords,
              'pixscl': scl*3600.0, 
              'addinfo': '',
              'groupname': 'swire', 
              'seqn': 0,
              'hascat': True,
              'mjd': 0,
              'exptime': 0,
              'airmass': 0
        #    'nightobs': int(os.path.dirname(fitsFile).split('/')[-1])
        }
        
        data.update(dd)

        data.update({"cd11": header["CD1_1"], "cd21": header["CD2_1"], "cd12": header["CD1_2"], "cd22": header["CD2_2"]})
        
        # Work out collection ID
        field = fitsFile.split('_')[1]
        data['waveband'] = data['instrument']+str(data['waveband'])
        waveband = data['waveband']
        #print field, waveband
        req = Collection.objects.get(field=field, survey='SWIRE', filter=waveband, instrument=data['instrument'], telescope='Spitzer')
        data['collection_id'] = req.id                
        
        #print data
                
        img = Image(**data)
        img.save()
    
    fileHandler.close()

 
for procpath in ['/Users/eglez/Data/SWIRE/Spitzer']:
    print procpath
    fitsFiles = runFileFilter(glob.glob(os.path.join(procpath, '*.fits')))
    for f in fitsFiles:
        ingestFile(f)
    
#for month in glob.glob(os.path.join(procpath, '20*')):
#    for night in glob.glob(os.path.join(month, '20*')):
#        fitsFiles = runFileFilter(glob.glob(os.path.join(night, 'HAWK*')))
#        for fitsFile in fitsFiles:
#            try:
#                ingestFile(fitsFile)
#            except IntegrityError:
#                pass
    
