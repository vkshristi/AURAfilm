import cv2, numpy as np

def lut_from_tone(p):
    x = np.linspace(0,1,256, dtype=np.float32)
    y = 1.0/(1.0+np.exp(-(p.contrast*(x-0.5))))
    amin = 1.0/(1.0+np.exp(-(p.contrast*(p.toe-0.5))))
    amax = 1.0/(1.0+np.exp(-(p.contrast*(p.shoulder-0.5))))
    y = (y-amin)/max(1e-6,(amax-amin))
    y = np.clip(((y+p.lift)**(1.0/max(1e-6,p.gamma)))*p.gain, 0, 1)
    return (y*255).astype(np.uint8)

def apply_tone_lut(img_bgr, lut):
    return cv2.LUT(img_bgr, lut)

def vignette_mask(w,h, strength, roundness):
    yy,xx=np.mgrid[0:h,0:w]
    cx,cy=w/2,h/2
    rx,ry=(w/2)*roundness,(h/2)
    r = np.sqrt(((xx-cx)/max(1e-6,rx))**2 + ((yy-cy)/max(1e-6,ry))**2)
    return np.clip(1.0 - strength*(r**1.2), 0.0, 1.0).astype(np.float32)

def apply_vignette(img, mask):
    f = img.astype(np.float32)/255.0
    return (np.clip(f*mask[...,None],0,1)*255).astype(np.uint8)

def halation(img, p):
    x = img.astype(np.float32)/255.0
    luma = 0.2126*x[...,2] + 0.7152*x[...,1] + 0.0722*x[...,0]
    m = np.clip((luma-p.hal_thresh)/(1-p.hal_thresh+1e-6),0,1)
    def glow(ch, rad):
        return cv2.GaussianBlur(m*ch,(0,0), max(1e-6,rad))
    b = glow(x[...,0], p.hal_b); g = glow(x[...,1], p.hal_g); r = glow(x[...,2], p.hal_r)
    out = x.copy()
    out[...,0] = np.clip(out[...,0] + p.hal_str*b, 0, 1)
    out[...,1] = np.clip(out[...,1] + p.hal_str*g, 0, 1)
    out[...,2] = np.clip(out[...,2] + p.hal_str*r, 0, 1)
    return (out*255).astype(np.uint8)

def bloom(img, radius, strength, thresh=0.85):
    x = img.astype(np.float32)/255.0
    luma = 0.2126*x[...,2] + 0.7152*x[...,1] + 0.0722*x[...,0]
    mask = (luma>thresh).astype(np.float32)
    glow = cv2.GaussianBlur(x*mask[...,None], (0,0), max(1e-6,radius))
    return (np.clip(x + strength*glow, 0, 1)*255).astype(np.uint8)

def chrom_aberration(img, pixels):
    h,w=img.shape[:2]; shift=int(max(1, round(pixels)))
    b,g,r = cv2.split(img)
    r2 = cv2.warpAffine(r, np.float32([[1,0, shift],[0,1,0]]),(w,h), borderMode=cv2.BORDER_REFLECT)
    b2 = cv2.warpAffine(b, np.float32([[1,0,-shift],[0,1,0]]),(w,h), borderMode=cv2.BORDER_REFLECT)
    return cv2.merge([b2,g,r2])

def grain(img, strength, scale, rng):
    x = img.astype(np.float32)/255.0
    h,w=x.shape[:2]
    noise = rng.normal(0,1,(h,w)).astype(np.float32)
    if scale>1:
        small = cv2.resize(noise, (max(1, int(w/scale)), max(1,int(h/scale))), interpolation=cv2.INTER_AREA)
        noise = cv2.resize(small, (w,h), interpolation=cv2.INTER_LINEAR)
    noise = cv2.GaussianBlur(noise,(0,0),0.6)
    return (np.clip(x*(1.0 + strength*noise[...,None]),0,1)*255).astype(np.uint8)
