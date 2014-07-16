import os
import math
import glob
import pyfits

import ephem
from kapteyn import wcs

from django.db import IntegrityError, transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "casu.settings")

from imagedb.models import Image

procpath='/Users/eglez/Data/INTWFC/EN1/'

translate = {
    'objname': 'OBJECT', 'waveband': 'WFFBAND', 
    'telescope': 'TELESCOP', 'instrument': 'INSTRUME', 'origin': 'ORIGIN',
    'mjd': 'MJD-OBS',
    'exptime': 'EXPTIME', 'airmass': 'AIRMASS',
    'naxis1': 'NAXIS1', 'naxis2': 'NAXIS2',
    'ctype1': 'CTYPE1', 'ctype2': 'CTYPE2',
    'crpix1': 'CRPIX1', 'crpix2': 'CRPIX2',
    'crval1': 'CRVAL1', 'crval2': 'CRVAL2',
    'cd11': 'CD1_1', 'cd21': 'CD2_1', 'cd12': 'CD1_2', 'cd22': 'CD2_2', 
    'pv21': 'PV2_1', 'pv23': 'PV2_3',
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
    
@transaction.atomic
def ingestFile(fitsFile):
    fileHandler = pyfits.open(fitsFile)
    imageHdu = fileHandler[1]
    
    d0 = ingestImageHeader(fileHandler[0].header)
    
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
              'groupname': 'intwfc', 'origin': 'INT',
              'seqn': 0,
              'hascat': True,
              'observatory': 'La Palma'
        #    'nightobs': int(os.path.dirname(fitsFile).split('/')[-1])
        }
    
        data.update(dd)
                
        print data
                
        img = Image(**data)
    
        img.save()
    
    fileHandler.close()
    
    
 
fitsFiles = runFileFilter(glob.glob(os.path.join(procpath, 'r*.fit')))
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
    
