
import os
import time
import base64
import json

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Max, Min
from django.views.decorators.cache import cache_page

from celery.result import AsyncResult

from imagedb.models import Request, Image, Cache, Collection
from imagedb.utils import ImageDict, SortKey, isMobile
from imagedb.settings import CACHE, REQUESTS

from casu.celery import app
from imagedb.tasks import computemd5
from PIL import Image as PILImage
from casu.settings import ALLOWED_HOSTS

# Create your views here.
def index(request):
    context={}
    return render(request, "imagedb/index.html", context)

@cache_page(60 * 60)
def collection(request):
    """
    Displays the list of image collections
    :param request:
    :return:
    """
    context={}

    try:
        context = json.load(open('/tmp/collections.pkl'))
    except:
        c = []
        result = Collection.objects.all()
        totalimages = 0
        for r in result:
            dd = ImageDict()
            for k in ['field', 'addinfo', 'survey', 'telescope', 'instrument', 'filter', 'status', 'pi']:
                dd[k] = getattr(r, k)
            dd['number'] = Image.objects.filter(collection = r.id).filter(ishidden=False).count()
            totalimages = totalimages + dd['number']
            dd.update(Image.objects.filter(collection = r.id).filter(ishidden=False).aggregate(Min('cenra')))
            dd.update(Image.objects.filter(collection = r.id).filter(ishidden=False).aggregate(Max('cenra')))
            dd.update(Image.objects.filter(collection = r.id).filter(ishidden=False).aggregate(Min('cendec')))
            dd.update(Image.objects.filter(collection = r.id).filter(ishidden=False).aggregate(Max('cendec')))
            c.append(dd)

        context['collection'] = c
        context['totalimages'] = totalimages

        json.dump(context,open('/tmp/collections.pkl','w'))

    return render(request, "imagedb/collection.html", context)

def getTar(request, md5hash):
    pass

def getImage(request):
    """

    :param request:
    :return:

    Example:

        http://apm14.ast.cam.ac.uk/imagedb/getImage?ra=242.0&dec=54.8&size=120.0&options=
    """
    ip = request.META['REMOTE_ADDR']
    if isMobile(request):
        template_name = 'imagedb/m_getimage.html'
    else:
        template_name = 'imagedb/getimage.html'

    # Get is a direct call
    if request.META['REQUEST_METHOD'] == 'POST':
        args = request.POST
    else:
        args = request.GET

    # Copy all arguments to own dictionary, because args is immutable
    context = {}
    for k in args.keys():
        context[k] = args[k]
        request.session[k] = args[k]

    # Check if we have all inputs, otherwise go back to the form
    try:
        ra, dec, size, options = args['ra'], args['dec'], args['size'], args['options']
        ra = float(ra)
        dec = float(dec)
        size = float(size)
    except:
        for k in ['ra', 'dec', 'size', 'options']:
            context[k] = request.session.get(k, None)
            if context[k] is None: context.pop(k)
            context['celeryID']=0
        return render(request, template_name, context)

    # Perform database query and get results
    result = Image.objects.all().filter(cendec__gt=dec - 1, cendec__lt=dec + 1, cenra__gt=ra - 1, cenra__lt=ra + 1).filter(ishidden=False)
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
        md5unique = computemd5((ra, dec, size, options.replace('U', ''), req.userGroup))
        req.md5hash = md5unique

    req.save()

    # Save the unique md5 of the request in the session
    request.session["md5unique"] = md5unique
    context["md5unique"] = md5unique

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

        #print [g.name for g in request.user.groups.all()], img.groupname
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
                       waveband = img.waveband, telescope = img.telescope, instrument = img.instrument,
                       md5hash=dd['md5hash'])
            ch.save()

    images.sort(key=SortKey)

    # Write unique md5
    fh = open(os.path.join(outputDir, 'md5unique'), 'w').write(md5unique)

    # Check if we can make colour VISTA image ---------------------------------
    context['vistaRGB'] = None

    bands = ['Ks', 'H', 'J', 'Y', 'Z']
    cbands = []
    for i in range(len(images)):
        if images[i].instrument.find('VIRCAM')<0: continue
        if not images[i]['avail']: continue
        if images[i].waveband in bands:
                if images[i].waveband in cbands:
                    pass
                else:
                    cbands.append(images[i].waveband)
        if len(cbands)==3: break

    if len(cbands) == 3:
        context['vistaRGB'] = 'rgbv%s' % md5unique
        context['vistaBands'] = ' '.join(cbands)
    # -------------------------------------------------------------------------

    # Check if we can make colour VST image ---------------------------------
    context['vstRGB'] = None

    bands = ['i_SDSS', 'r_SDSS', 'g_SDSS', 'u_SDSS']
    cbands = []
    for i in range(len(images)):
        if images[i].instrument.find('OMEGACAM')<0: continue
        if not images[i]['avail']: continue
        if images[i].waveband in bands:
                if images[i].waveband in cbands:
                    pass
                else:
                    cbands.append(images[i].waveband)
        if len(cbands)==3: break

    if len(cbands) == 3:
        context['vstRGB'] = 'rgbo%s' % md5unique
        context['vstBands'] = ' '.join(cbands)
    # -------------------------------------------------------------------------

    # Check if we can make colour WFC image ---------------------------------
    context['wfcRGB'] = None

    bands = ['i', 'r', 'g', 'u']
    cbands = []
    for i in range(len(images)):
        if images[i].instrument.find('WFC')<0: continue
        if not images[i]['avail']: continue
        if images[i].waveband in bands:
                if images[i].waveband in cbands:
                    pass
                else:
                    cbands.append(images[i].waveband)
        if len(cbands)==3: break

    if len(cbands) == 3:
        context['wfcRGB'] = 'rgbw%s' % md5unique
        context['wfcBands'] = ' '.join(cbands)
    # -------------------------------------------------------------------------

    # Check if we can make colour IRAC image ---------------------------------
    context['iracRGB'] = None

    bands = ['IRAC3', 'IRAC2', 'IRAC1']
    cbands = []
    for i in range(len(images)):
        if images[i].instrument.find('IRAC')<0: continue
        if not images[i]['avail']: continue
        if images[i].waveband in bands:
                if images[i].waveband in cbands:
                    pass
                else:
                    cbands.append(images[i].waveband)
        if len(cbands)==3: break

    if len(cbands) == 3:
        context['iracRGB'] = 'rgbirac%s' % md5unique
        context['iracBands'] = ' '.join(cbands)
    # -------------------------------------------------------------------------

    # Check if celery is accepting connections and submit job -----------------
    result = app.send_task('imagedb.tasks.status')
    time.sleep(0.1)
    status = result.ready()
    context['celeryStatus'] = status

    outCache = CACHE + '/' + request.session['md5unique'] + '/.complete'
    if os.access(outCache, os.R_OK):
        flag=False
        context['celeryStatus'] = True
        context['celeryID'] = result.task_id

    if flag:
        if status:
            result = app.send_task('imagedb.tasks.getImage', args=(req.id,))
            context["celeryID"] = result.task_id
            #print '****', result.task_id
            #res = AsyncResult(result.task_id)
            #print '****', res.ready()
    # -------------------------------------------------------------------------

    context['images'] = images

    if len(images) == 0:
        context['error_message'] = 'No images found.'

    req.success = True
    req.save()

    return render(request, 'imagedb/getimage.html', context)


def getStatus(request, id):
    if id=="0": return JsonResponse({'status': True})
    res = AsyncResult(id).ready()
    return JsonResponse({'status': res})

@cache_page(60 * 60)
def getImageCache(request, md5hash):
    imgFile = CACHE + '/' + request.session['md5unique'] + '/%s.png' % md5hash
    print imgFile
    #watch = time.time()
    #while not os.access(imgFile, os.R_OK):
    #    if time.time() - watch > 60:
    #        break
    #    time.sleep(1)
    #if md5hash.find('rgb') > -1: time.sleep(1)
    return redirect("http://apm14.ast.cam.ac.uk/cache/%s/%s.png" % (request.session['md5unique'], md5hash))
    #with open(imgFile, "rb") as image:
    #    return HttpResponse(image.read(), mimetype="image/png")

def getImageLocal(request):
    ip = request.META['REMOTE_ADDR']
    if isMobile(request):
        template_name = 'imagedb/m_getimage.html'
    else:
        template_name = 'imagedb/getimagelocal.html'

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

    # Check if we have all inputs, otherwise go to form
    try:
        ra, dec, size, image, hdu, options = args['ra'], args['dec'], args['size'], args['image'], args['hdu'], args[
            'options']
        ra, dec, size = float(ra), float(dec), float(size)
        if hdu == '': hdu = '1'
    except:
        return render(request, template_name, context)

    # Compute unique md5 from the argument list
    md5unique = computemd5((image, ra, dec, size, options.replace('U', '')))

    # Save request to database
    req = Request(ip=ip, ra=ra, dec=dec, size=size, options=options, success=False, userAnonymous=True,
                  md5hash=md5unique)
    if request.user.is_authenticated():
        req.userAnonymous = False
        req.userName = request.user.username
        req.userGroup = ' '.join([g.name for g in request.user.groups.all()])
        md5unique = computemd5((ra, dec, size, options.replace('U', ''), req.userGroup))
        req.md5hash = md5unique

    req.save()

    # Save the unique md5 of the request in the session
    request.session["md5unique"] = md5unique

    outputDir = os.path.join(REQUESTS, '%010d' % req.id)
    if not os.access(outputDir, os.X_OK):
        os.mkdir(outputDir)
        os.chmod(outputDir, 0777)


    ch = Cache(request=req, path=image, hdu=hdu, image=1,
                       md5hash=md5unique)
    ch.save()

    # Write unique md5
    fh = open(os.path.join(outputDir, 'md5unique'), 'w').write(md5unique)

    # Check if celery is accepting connections and submit job -----------------
    status = app.send_task('imagedb.tasks.status')
    time.sleep(0.1)
    status = status.ready()

    outCache = CACHE + '/' + request.session['md5unique']
    flag = True
    if os.access(outCache, os.R_OK):
        flag=False

    if flag:
        if status:
            result = app.send_task('imagedb.tasks.getImage', args=(req.id,))
            print '******', result, '****'
            result.get(timeout=600)
    # -------------------------------------------------------------------------

    if request.META['REQUEST_METHOD'] == 'POST':
        try:
            with open(CACHE + '/%s/%s.png' % (md5unique, md5unique), "rb") as image:
                req.success = True
                req.save()
                context['imagedata'] = "data:image/png;base64," + base64.encodestring(image.read())
                return render(request, 'imagedb/getimagelocal.html', context)
        except IOError:
            red = PILImage.new('RGBA', (1, 1), (255, 0, 0, 0))
            response = HttpResponse(mimetype="image/jpeg")
            red.save(response, "PNG")
            return response

    return render(request, 'imagedb/getimagelocal.html', context)


def getImageLocalOLD(request):
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
    

def showField(request):

    import json
    context={"data": []}

    for item in Collection.objects.filter(survey='INT/WFC', telescope='INT', field='EN1'):
        data=[]
        for img in Image.objects.filter(collection = item.id, ishidden=False):
            data.append([img.cenra, img.cendec])

        context["data"].append(r"{ name: '%s', data: %s }" % (item.filter, json.dumps(data)))

    context["data"] = ', '.join(context["data"])


    return render(request, 'imagedb/field.html', context)