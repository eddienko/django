from __future__ import absolute_import

from celery import shared_task

import os
import json
import md5
import subprocess
from imagedb.settings import REQUESTS, CACHE

def computemd5(args):
    return md5.new(json.dumps(args)).hexdigest()
    
@shared_task
def getImageLocal(ra, dec, size, image, hdu, options='', req = 1):
    
    
    outputDir = os.path.join(REQUESTS, '%010d' % req)
    if (not os.access(outputDir, os.X_OK)):
        os.mkdir(outputDir)
        
    inFile = os.path.basename(image)
    outFile = os.path.join(outputDir, inFile)
    if (not os.access(outFile, os.R_OK)):
        os.symlink(image, outFile)
    
    md5hash = computemd5((ra, dec, image, size, hdu, options.replace('U','')))
    
    fh = open(os.path.join(outputDir, 'list'), 'w')
    fh.write('%s %s %s %s %s %s %s\n' % (inFile, hdu, ra, dec, size, options+'_', md5hash))
    fh.close()
    
    p = subprocess.Popen(['./mapmaker.sh', '%010d' % req], cwd=REQUESTS)
    p.wait()
          
    return
    
@shared_task
def getImage(reqID = 1):
    
    p = subprocess.Popen(['./mapmaker.sh', '%010d' % reqID], cwd=REQUESTS)
    p.wait()
          
    return

@shared_task
def status():
    return True

@shared_task
def add(x, y):
    return x + y


@shared_task
def mul(x, y):
    return x * y


@shared_task
def xsum(numbers):
    return sum(numbers)
    