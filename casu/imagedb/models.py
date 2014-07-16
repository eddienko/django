from django.db import models

# Create your models here.
class Config(models.Model):
	pathRequest = models.CharField(max_length=200)
	pathCache = models.CharField(max_length=200)

class Request(models.Model):
    ip = models.CharField(max_length=60)
    ra = models.FloatField()
    dec = models.FloatField()
    size = models.FloatField()
#    path = models.CharField(max_length=200)
#    hdu = models.PositiveSmallIntegerField()
#    image = models.IntegerField()
    options = models.CharField(max_length=20)
    success = models.BooleanField()
    md5hash = models.CharField(max_length=80)
    
    userAnonymous = models.BooleanField()
    userName = models.CharField(max_length=16, null=True)
    userGroup = models.CharField(max_length=80, null=True)

class Cache(models.Model):
    request = models.IntegerField()
    path = models.CharField(max_length=200)
    hdu = models.PositiveSmallIntegerField()
    image = models.IntegerField()

    md5hash = models.CharField(max_length=80)

class Image(models.Model):
    filename = models.CharField(max_length=80)
    filepath = models.CharField(max_length=256)
    objname = models.CharField(max_length=40)
    extno = models.IntegerField()
    waveband = models.CharField(max_length=40)
    telescope =  models.CharField(max_length=40)
    instrument =  models.CharField(max_length=40)
    origin =  models.CharField(max_length=40)
    observatory =  models.CharField(max_length=40)
    mjd = models.FloatField()
    exptime = models.FloatField()
    seeing = models.FloatField(null=True)
    elliptic = models.FloatField(null=True)
    airmass = models.FloatField()
    maglim = models.FloatField(null=True)
    magzpt = models.FloatField(null=True)
    magzrr = models.FloatField(null=True)
    skynoise = models.FloatField(null=True)
    naxis1 = models.IntegerField()
    naxis2 = models.IntegerField()
    ctype1 = models.CharField(max_length=8)
    ctype2 = models.CharField(max_length=8)
    crpix1 = models.FloatField()
    crpix2 = models.FloatField()
    crval1 = models.FloatField()
    crval2 = models.FloatField()
    cd11 = models.FloatField()
    cd12 = models.FloatField()
    cd21 = models.FloatField()
    cd22 = models.FloatField()
    pv21 = models.FloatField(null=True)
    pv22 = models.FloatField(null=True)
    pv23 = models.FloatField(null=True)
    pv24 = models.FloatField(null=True)
    pv25 = models.FloatField(null=True)
    cenra = models.FloatField()
    cendec = models.FloatField()
    cencoords = models.CharField(max_length=30)
    pixscl = models.FloatField()
    addinfo = models.CharField(max_length=256)

    hascat = models.BooleanField()
    catname = models.CharField(max_length=80, null=True)
    
    groupname = models.CharField(max_length=256)
    seqn = models.IntegerField()
    
    
    
    