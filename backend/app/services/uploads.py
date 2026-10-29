import io
import warnings
from PIL import Image, ImageOps, ImageCms, UnidentifiedImageError
import numpy as np

Image.MAX_IMAGE_PIXELS = 20_000_000

class UploadError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status

def decode(raw):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            im = Image.open(io.BytesIO(raw))
            if im.format not in ('JPEG','PNG'):
                raise UploadError('Only JPEG and PNG images are supported.',415)
            if getattr(im,'n_frames',1) != 1:
                raise UploadError('Animated images are not supported.',415)
            if im.width*im.height > 20_000_000:
                raise UploadError('Image exceeds the 20 megapixel limit.')
            im.load()
            return im
    except UploadError:
        raise
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise UploadError('The image could not be safely decoded.')

def normalize(raw):
    source = ImageOps.exif_transpose(decode(raw))
    original = source.size
    alpha = source.mode in ('RGBA','LA') or 'transparency' in source.info
    if alpha:
        rgba = source.convert('RGBA')
        base = Image.new('RGBA',rgba.size,(244,244,245,255))
        source = Image.alpha_composite(base,rgba).convert('RGB')
    else:
        source = source.convert('RGB')
    profile = source.info.get('icc_profile')
    if profile:
        try:
            source = ImageCms.profileToProfile(source,ImageCms.ImageCmsProfile(io.BytesIO(profile)),ImageCms.createProfile('sRGB'),outputMode='RGB')
        except (OSError,ValueError,ImageCms.PyCMSError):
            raise UploadError('Invalid embedded color profile.')
    ratio = min(512/original[0],512/original[1])
    width,height = max(1,round(original[0]*ratio)),max(1,round(original[1]*ratio))
    left,top = (512-width)//2,(512-height)//2
    canvas = Image.new('RGB',(512,512),(244,244,245))
    canvas.paste(source.resize((width,height),Image.Resampling.LANCZOS),(left,top))
    geometry = dict(width=512,height=512,original_width=original[0],original_height=original[1],scaled_width=width,scaled_height=height,padding=[left,top,512-width-left,512-height-top],scale=ratio,alpha_composited=alpha,background='#f4f4f5')
    return canvas,geometry

def validate_mask(raw, geometry):
    mask = decode(raw)
    if mask.format != 'PNG' or mask.size != (512,512):
        raise UploadError('Mask must be a 512 × 512 PNG.')
    array = np.asarray(mask.convert('L'))
    if not np.isin(array,[0,255]).all():
        raise UploadError('Mask must contain only 0 (retain) and 255 (edit).')
    left,top,right,bottom = geometry['padding']
    valid = np.zeros((512,512),bool)
    valid[top:512-bottom if bottom else 512,left:512-right if right else 512] = True
    if np.any((array>0)&~valid):
        raise UploadError('Letterbox padding must remain uneditable.')
    fraction = float(np.count_nonzero(array)/np.count_nonzero(valid))
    if not .05 <= fraction <= .95:
        raise UploadError('Select between 5% and 95% of the real image.')
    return Image.fromarray(array),fraction
