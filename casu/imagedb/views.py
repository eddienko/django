
import os
import time
import base64

from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render

from imagedb.models import Request, Image, Cache
from imagedb.utils import ImageDict, SortKey, celeryStatus
from imagedb.settings import CACHE, REQUESTS

from casu.celery import app
from imagedb.tasks import computemd5
from PIL import Image as PILImage
from casu.settings import ALLOWED_HOSTS

# Create your views here.
def index(request):
    return HttpResponse("Hello, world. You're at the imagedb index.")


def getImage(request):
    ip = request.META['REMOTE_ADDR']
    cachePath = '/Users/eglez/Django/casu/imagedb/data/cache'

    # Get is a direct call
    if request.META['REQUEST_METHOD'] == 'POST':
        args = request.POST
    else:
        args = request.GET

    # Copy all arguments to own dictionary, because args is immutable
    context = {}
    for k in args.keys():
        context[k] = args[k]

    # Check if we have all inputs, otherwise go back to the form
    try:
        ra, dec, size, options = args['ra'], args['dec'], args['size'], args['options']
        ra = float(ra)
        dec = float(dec)
        size = float(size)
    except:
        return render(request, 'imagedb/getimage.html', context)

    # Perform database query and get results
    result = Image.objects.all().filter(cendec__gt=dec - 1, cendec__lt=dec + 1, cenra__gt=ra - 1, cenra__lt=ra + 1)
    onchip = "onchip(%s,%s,naxis1, naxis2, ctype1, ctype2, crval1, crval2, crpix1, crpix2, cd11, cd12, cd21, cd22, pv21, pv23, pv25)=true" % (
    ra, dec)
    result = result.extra(where=[onchip])

    # Compute unique md5 from the argument list
    md5unique = computemd5((ra, dec, size, options.replace('U', '')))

    # Save request to database
    req = Request(ip=ip, ra=ra, dec=dec, size=size, options=options, success=False, userAnonymous=True,
                  md5hash=md5unique)
    if request.user.is_authenticated():
        req.userAnonymous = False
        req.userName = request.user.username
        req.userGroup = ' '.join([g.name for g in request.user.groups.all()])
        req.md5hash = computemd5((ra, dec, size, options.replace('U', ''), req.userGroup))

    req.save()

    request.session["md5unique"] = req.md5hash

    outputDir = os.path.join(REQUESTS, '%010d' % req.id)
    if not os.access(outputDir, os.X_OK):
        os.mkdir(outputDir)
        os.chmod(outputDir, 0777)

    # Get full list of images
    flag = False
    keys = [f.name for f in Image._meta.fields]
    images = []
    for img in result:
        dd = ImageDict()
        for k in keys:
            dd[k] = getattr(img, k)
        md5hash = computemd5(
            (ra, dec, os.path.join(img.filepath, img.filename), size, img.extno, options.replace('U', '')))
        dd['md5hash'] = md5hash
        # Work out if the user has access rights
        dd['avail'] = False

        if ip in ALLOWED_HOSTS:
            dd['avail'] = True
        elif (img.groupname == 'public'):
            dd['avail'] = True
        else:
            if request.user.is_authenticated():
                groups = [g.name for g in request.user.groups.all()]
                if 'casuadmin' in groups:
                    dd['avail'] = True
                elif img.groupname in groups:
                    dd['avail'] = True
        images.append(dd)
        if dd['avail']:
            flag = True
            ch = Cache(request=req, path=os.path.join(img.filepath, img.filename), hdu=img.extno, image=img.id,
                       md5hash=dd['md5hash'])
            ch.save()

    images.sort(key=SortKey)

    # Write unique md5
    fh = open(os.path.join(outputDir, 'md5unique'), 'w').write(md5unique)

    # Check if we can make colour VISTA image ---------------------------------
    context['vistaRGB'] = None
    cacheFile = CACHE + '/rgbv%s.png' % md5unique
    if ('U' not in options) and os.access(cacheFile, os.R_OK):
        context['vistaRGB'] = 'rgbv%s' % md5unique
        for i in range(len(images)):
            if images[i].instrument.find('VIRCAM')<0: continue
            if not images[i]['avail']:
                context['vistaRGB'] = None
    else:
        dd = {}
        bands = ['Ks', 'H', 'J', 'Y', 'Z']
        for i in range(len(images)):
            if images[i].instrument.find('VIRCAM')<0: continue
            if not images[i]['avail']: continue
            if images[i].waveband in bands:
                if images[i].waveband in dd:
                    #if images[i].seeing < images[dd[images[i].waveband]].seeing:
                    dd[images[i].waveband].append(i)
                else:
                    dd[images[i].waveband] = [i]

        count = 0
        cimages = []
        cbands = []
        for f in bands:
            if f in dd:
                cimages.append([images[i].md5hash for i in dd[f]])
                cbands.append(f)
                count += 1
                if count == 3:
                    break

        if count == 3:
            fh = open(os.path.join(outputDir, 'vistaColour'), 'w')
            fh.write("%s\n" % (' '.join(cbands)))
            for c in cimages:
                fh.write("%s\n" % (' '.join(c)))
            fh.close()
            context['vistaRGB'] = 'rgbv%s' % md5unique
            context['vistaBands'] = ' '.join(cbands)
            if os.access(cacheFile, os.R_OK):
                os.unlink(cacheFile)
    # -------------------------------------------------------------------------

    # Check if we can make colour VST image ---------------------------------
    context['vstRGB'] = None
    cacheFile = CACHE + '/rgbo%s.png' % md5unique
    if ('U' not in options) and os.access(cacheFile, os.R_OK):
        context['vstRGB'] = 'rgbo%s' % md5unique
        for i in range(len(images)):
            if images[i].instrument.find('OMEGACAM')<0: continue
            if not images[i]['avail']:
                context['vstRGB'] = None
    else:
        dd = {}
        bands = ['i_SDSS', 'r_SDSS', 'g_SDSS', 'u_SDSS']
        for i in range(len(images)):
            if images[i].instrument.find('OMEGACAM')<0: continue
            if not images[i]['avail']: continue
            if images[i].waveband in bands:
                if images[i].waveband in dd:
                    #if images[i].seeing < images[dd[images[i].waveband]].seeing:
                    dd[images[i].waveband].append(i)
                else:
                    dd[images[i].waveband] = [i]

        count = 0
        cimages = []
        cbands = []
        for f in bands:
            if f in dd:
                cimages.append([images[i].md5hash for i in dd[f]])
                cbands.append(f)
                count = count + 1
                if count == 3:
                    break

        if count == 3:
            fh = open(os.path.join(outputDir, 'vstColour'), 'w')
            fh.write("%s\n" % (' '.join(cbands)))
            for c in cimages:
                fh.write("%s\n" % (' '.join(c)))
            fh.close()
            context['vstRGB'] = 'rgbo%s' % md5unique
            context['vstBands'] = ' '.join(cbands)
            if os.access(cacheFile, os.R_OK):
                os.unlink(cacheFile)
    # -------------------------------------------------------------------------

    # Check if we can make colour WFC image ---------------------------------
    context['wfcRGB'] = None
    cacheFile = CACHE + '/rgbw%s.png' % md5unique
    if ('U' not in options) and os.access(cacheFile, os.R_OK):
        context['wfcRGB'] = 'rgbw%s' % md5unique
        for i in range(len(images)):
            if images[i].instrument.find('WFC')<0: continue
            if not images[i]['avail']:
                context['wfcRGB'] = None
    else:
        dd = {}
        bands = ['i', 'r', 'g', 'u']
        for i in range(len(images)):
            if images[i].instrument.find('WFC')<0: continue
            if not images[i]['avail']: continue
            if images[i].waveband in bands:
                if images[i].waveband in dd:
                    #if images[i].seeing < images[dd[images[i].waveband]].seeing:
                    dd[images[i].waveband].append(i)
                else:
                    dd[images[i].waveband] = [i]

        count = 0
        cimages = []
        cbands = []
        for f in bands:
            if f in dd:
                cimages.append([images[i].md5hash for i in dd[f]])
                cbands.append(f)
                count = count + 1
                if count == 3:
                    break

        if count == 3:
            fh = open(os.path.join(outputDir, 'wfcColour'), 'w')
            fh.write("%s\n" % (' '.join(cbands)))
            for c in cimages:
                fh.write("%s\n" % (' '.join(c)))
            fh.close()
            context['wfcRGB'] = 'rgbw%s' % md5unique
            context['wfcBands'] = ' '.join(cbands)
            if os.access(cacheFile, os.R_OK):
                os.unlink(cacheFile)
    # -------------------------------------------------------------------------

    # Check if celery is accepting connections and submit job -----------------
    status = app.send_task('imagedb.tasks.status')
    time.sleep(0.1)
    status = status.ready()

    outCache = CACHE + '/' + request.session['md5unique']
    if os.access(outCache, os.R_OK):
        flag=False

    if flag:
        if status:
            result = app.send_task('imagedb.tasks.getImage', args=(req.id,))
    # -------------------------------------------------------------------------

    context['images'] = images

    if len(images) == 0:
        context['error_message'] = 'No images found.'

    req.success = True
    req.save()

    return render(request, 'imagedb/getimage.html', context)


def getImageCache(request, md5hash):
    imgFile = CACHE + '/' + request.session['md5unique'] + '/%s.png' % md5hash
    watch = time.time()
    while not os.access(imgFile, os.R_OK):
        if time.time() - watch > 60:
            break
        time.sleep(1)
    if md5hash.find('rgb') > -1: time.sleep(1)
    with open(imgFile, "rb") as image:
        return HttpResponse(image.read(), mimetype="image/png")


def getImageLocal(request):
    ip = request.META['REMOTE_ADDR']

    cachePath = '/Users/eglez/Django/casu/imagedb/data/cache'

    # Get is a direct call
    if request.META['REQUEST_METHOD'] == 'POST':
        args = request.POST
    else:
        args = request.GET

    context = {}
    for k in args.keys():
        context[k] = args[k]


    # Check if we have all inputs, otherwise go to form
    try:
        ra, dec, size, image, hdu, options = args['ra'], args['dec'], args['size'], args['image'], args['hdu'], args[
            'options']
        if hdu == '': hdu = '1'
    except:
        return render(request, 'imagedb/getimagelocal.html', context)

    # Do something with the input

    req = Request(ip=ip, ra=ra, dec=dec, size=size, options=options, success=False, userAnonymous=True)
    req.save()

    ch = Cache(request=req.id, path=image, hdu=hdu, image=-1)
    ch.save()

    md5hash = computemd5((ra, dec, image, size, hdu, options.replace('U', '')))

    if not os.access(cachePath + '/%s.png' % md5hash, os.R_OK):
        if celeryStatus():
            result = app.send_task('imagedb.tasks.getImageLocal', args=(ra, dec, size, image, hdu, options, req.id))
            result.get(timeout=600)

    if request.META['REQUEST_METHOD'] == 'POST':
        try:
            with open(cachePath + '/%s.png' % md5hash, "rb") as image:
                req.success = True
                req.save()
                context['imagedata'] = "data:image/png;base64," + base64.encodestring(image.read())
                return render(request, 'imagedb/getimagelocal.html', context)
        except IOError:
            red = PILImage.new('RGBA', (1, 1), (255, 0, 0, 0))
            response = HttpResponse(mimetype="image/jpeg")
            red.save(response, "PNG")
            return response

    else:
        try:
            with open(cachePath + '/%s.png' % md5hash, "rb") as image:
                req.success = True
                req.save()
                return HttpResponse(image.read(), mimetype="image/png")
        except IOError:
            red = PILImage.new('RGBA', (1, 1), (255, 0, 0, 0))
            response = HttpResponse(mimetype="image/jpeg")
            red.save(response, "PNG")
            return response
    
