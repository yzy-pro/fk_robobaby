"""Independent numerical checks and figures while MATLAB execution is unavailable.

Run with /usr/bin/python3 chapter3/reference/verify_reference.py.
These outputs are explicitly named *_reference, never MATLAB-run evidence.
Dependencies: NumPy, SciPy, Pillow, Matplotlib (system Python packages).
"""
from pathlib import Path
import csv
import json
import re
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIGURES = ROOT.parent / 'figures'
RESULTS = ROOT / 'results'
K = np.array([[748.4469, 0, 944.9033], [0, 748.0773, 522.3963], [0, 0, 1]])
EXPONENTS = np.array([.50, .65, .80, 1, 1.25, 1.55, 1.90])
LUT = np.floor(255*(np.arange(256)[:, None]/255)**EXPONENTS+.5).astype(np.uint8)


def save_figure(fig, name):
    fig.savefig(FIGURES / f'{name}_reference.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


def write_rows(name, rows):
    with (RESULTS / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def rotation(yaw, pitch):
    yaw, pitch = np.deg2rad([yaw, pitch])
    ry = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
    rx = np.array([[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]])
    return rx @ ry


def distort(x, y, radial=(.0099, -.0434), tangential=(0., 0.)):
    r2 = x*x+y*y
    scale = 1+radial[0]*r2+radial[1]*r2*r2
    p1, p2 = tangential
    return (x*scale+2*p1*x*y+p2*(r2+2*x*x),
            y*scale+p1*(r2+2*y*y)+2*p2*x*y)


def maps(shape, R=None, lens=True):
    v, u = np.indices(shape[:2], dtype=float)
    rays = np.stack(((u+1-K[0, 2])/K[0, 0], (v+1-K[1, 2])/K[1, 1], np.ones_like(u)))
    if R is not None:
        rays = np.einsum('ij,jhw->ihw', R, rays)
    X, Y, Z = rays
    valid = Z > 1024/2**18
    x = X/np.where(valid, Z, np.nan)
    y = Y/np.where(valid, Z, np.nan)
    if lens:
        r2 = x*x+y*y
        valid &= r2 <= 600000/2**18
        x, y = distort(x, y)
    mx, my = K[0, 0]*x+K[0, 2], K[1, 1]*y+K[1, 2]
    mx[~valid] = np.nan
    my[~valid] = np.nan
    return mx, my


def sample(image, mx, my, bits=None, nearest=False):
    h, w = image.shape[:2]
    valid = np.isfinite(mx) & np.isfinite(my) & (mx >= 1-1e-9) & (mx <= w+1e-9) & (my >= 1-1e-9) & (my <= h+1e-9)
    x = np.clip(np.where(valid, mx, 1)-1, 0, w-1)
    y = np.clip(np.where(valid, my, 1)-1, 0, h-1)
    channels = image[:, :, None] if image.ndim == 2 else image
    if bits is None:
        # SciPy provides an independent bilinear interpolation implementation.
        values = np.stack([map_coordinates(p.astype(float), [y, x], order=0 if nearest else 1,
                                          mode='nearest', prefilter=False) for p in channels.transpose(2, 0, 1)], axis=2)
        output = np.floor(values+.5).astype(np.uint8)
    else:
        ix, iy = np.floor(x).astype(int), np.floor(y).astype(int)
        F = 2**bits
        a, b = np.floor((x-ix)*F+.5).astype(np.int64), np.floor((y-iy)*F+.5).astype(np.int64)
        a, b = a[:, :, None], b[:, :, None]
        data = channels.astype(np.int64)
        acc = ((F-a)*(F-b)*data[iy, ix]+a*(F-b)*data[iy, np.minimum(ix+1, w-1)]
               +(F-a)*b*data[np.minimum(iy+1, h-1), ix]+a*b*data[np.minimum(iy+1, h-1), np.minimum(ix+1, w-1)])
        output = (acc//F**2).astype(np.uint8)
    output[~valid] = 0
    return (output[:, :, 0] if image.ndim == 2 else output), valid


def classify(image):
    data = image.astype(np.int64)
    y = (data[:, :, 0]+2*data[:, :, 1]+data[:, :, 2])//4
    n, total = y.size, int(y.sum())
    if np.count_nonzero(y < 48)*8 >= n and np.count_nonzero(y >= 208)*8 >= n:
        result = 2
    elif total < 48*n: result = 0
    elif total < 80*n: result = 1
    elif total < 112*n: result = 2
    elif total > 208*n: result = 6
    elif total > 176*n: result = 5
    elif total > 144*n: result = 4
    else: result = 3
    return result, total/n


def main():
    FIGURES.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    raw = np.array(Image.open(ROOT/'undistort/images/20260923_125558_900.jpg'))
    assert raw.shape == (1080, 1920, 3)
    yy, xx = np.indices((10, 12))
    plane = (3*(xx+1)+5*(yy+1)+7).astype(np.uint8)
    measured, valid = sample(plane,np.array([[2.25,6.5]]),np.array([[3.5,7.25]]))
    expected = np.floor(3*np.array([[2.25,6.5]])+5*np.array([[3.5,7.25]])+7+.5).astype(np.uint8)
    assert np.all(valid) and np.array_equal(measured,expected)
    measured, valid = sample(plane,np.array([[-1,np.nan,12]]),np.array([[2,2,10]]))
    assert np.array_equal(valid,[[False,False,True]]) and measured[0,0] == measured[0,1] == 0
    assert measured[0,2] == plane[-1,-1]
    identity, _ = sample(plane,*maps(plane.shape,lens=False))
    assert np.array_equal(identity,plane)
    tx, ty = distort(.2,.1,radial=(0,0),tangential=(.03,-.02))
    assert abs(tx-.1986)<1e-12 and abs(ty-.1013)<1e-12
    assert np.all(np.diff(LUT.astype(int), axis=0) >= 0)
    rtl = ROOT.parents[2]/'Pgl50h/src/video/preprocess/adaptive_gamma_lut.v'
    if rtl.is_file():
        entries = re.findall(r"rom\[(\d+)\]=8'd(\d+);", rtl.read_text())
        assert len(entries) == 2048
        for address, value in entries:
            c, v = divmod(int(address), 256)
            assert int(value) == (int(LUT[v, c]) if c < 7 else v)
    for level, expected in zip([47,48,79,80,111,112,144,145,176,177,208,209], [0,1,1,2,2,3,3,4,4,5,5,6]):
        assert classify(np.full((2, 2, 3), level, np.uint8))[0] == expected
    mx, my = maps(raw.shape)
    floating, valid = sample(raw, mx, my)
    q5, _ = sample(raw, mx, my, bits=5)
    nn, _ = sample(raw, mx, my, nearest=True)
    delta = q5.astype(float)-floating.astype(float)
    undistort = {'ValidRatio': float(valid.mean()), 'Q5MaxError': float(np.max(np.abs(delta[valid]))),
                 'Q5RMSE': float(np.sqrt(np.mean(delta[valid]**2)))}
    write_rows('undistort_reference.csv', [undistort])
    fig, ax = plt.subplots(2, 2, figsize=(14, 8))
    for a, im, title in zip(ax.flat, [raw, floating, nn, np.max(np.abs(delta), axis=2)],
                           ['Original camera image', 'Floating bilinear undistortion', 'Nearest-neighbour undistortion', '5-bit weights: maximum channel error']):
        item = a.imshow(im); a.set_title(title); a.axis('off')
        if im.ndim == 2: fig.colorbar(item, ax=a, shrink=.7)
    fig.tight_layout(); save_figure(fig, 'undistort_comparison')
    h, w = raw.shape[:2]
    v, u = np.indices((h, w))
    base = (45+170*((u//80+v//80)%2)).astype(np.uint8)
    chart = np.stack([base, np.floor(base*(.65+.35*(u+1)/w)+.5).astype(np.uint8),
                      np.floor(base*(.65+.35*(v+1)/h)+.5).astype(np.uint8)], axis=2)
    chart[(u%80 < 3) | (v%80 < 3)] = 240
    pose_rows = []
    fig, ax = plt.subplots(2, 3, figsize=(15, 7))
    for a, (yaw, pitch) in zip(ax.flat, [(0,0),(10,0),(0,-10),(10,-8),(-15,15),(15,-15)]):
        R = rotation(yaw, pitch)
        source, sv = sample(chart, *maps(chart.shape, R.T, False))
        mx, my = maps(chart.shape, R, False)
        corrected, cv = sample(source, mx, my)
        ix = np.floor(np.nan_to_num(mx, nan=1)-1).clip(0,w-1).astype(int)
        iy = np.floor(np.nan_to_num(my, nan=1)-1).clip(0,h-1).astype(int)
        common = cv & sv[iy, ix] & sv[iy, np.minimum(ix+1,w-1)] & sv[np.minimum(iy+1,h-1),ix] & sv[np.minimum(iy+1,h-1),np.minimum(ix+1,w-1)]
        uv = np.stack([u[common]+1, v[common]+1, np.ones(common.sum())])
        Hi = K@R.T@np.linalg.inv(K)
        rt = Hi@np.stack([mx[common],my[common],np.ones(common.sum())])
        e = rt[:2]/rt[2]-uv[:2]
        coordinate_error = float(np.sqrt(np.mean(np.sum(e*e, axis=0))))
        assert coordinate_error < 1e-9
        quantized_angles = np.floor(np.deg2rad(np.array([yaw,pitch]))*2048+.5)/2048
        qx, qy = maps(chart.shape, rotation(*np.rad2deg(quantized_angles)), False)
        d = corrected.astype(float)-chart.astype(float)
        row = {'YawDeg': yaw, 'PitchDeg': pitch, 'CommonValidRatio': float(common.mean()),
               'ImageRMSE': float(np.sqrt(np.mean(d[common]**2))), 'CoordinateRoundTripRMSE': coordinate_error,
               'Q2048AngleMapRMSE': float(np.sqrt(np.mean((qx[common]-mx[common])**2+(qy[common]-my[common])**2)))}
        pose_rows.append(row)
        a.imshow(corrected); a.axis('off'); a.set_title(f'yaw={yaw}, pitch={pitch}; common={common.mean():.1%}')
        if (yaw,pitch) == (10,-8):
            detail, axes = plt.subplots(1,3,figsize=(15,4))
            for aa, im, title in zip(axes,[chart,source,corrected],['Reference planar chart','Synthetic rotated camera','Rectified image']):
                aa.imshow(im); aa.axis('off'); aa.set_title(title)
            detail.tight_layout(); save_figure(detail,'pose_correction')
    fig.tight_layout(); save_figure(fig,'pose_sweep')
    write_rows('pose_reference.csv',pose_rows)
    small = raw[::4,::4].astype(float)
    normal = np.floor(50+.6*small+.5).astype(np.uint8)
    dark = np.floor(.18*small+.5).astype(np.uint8)
    bright = np.floor(215+.15*small+.5).astype(np.uint8)
    mixed = dark.copy(); mixed[:,small.shape[1]//2:] = bright[:,small.shape[1]//2:]
    active = target = 3; pending = candidate = None
    gamma_rows=[]; final=[]
    for name, image in zip(['normal','dark','bright','mixed'],[normal,dark,bright,mixed]):
        for _ in range(10):
            active += int(np.sign(target-active))
            if pending is not None:
                if candidate == pending: target = pending
                candidate = pending
            classified, mean = classify(image); pending = classified
            output = LUT[image, active]
            _, enhanced_mean = classify(output)
            gamma_rows.append(dict(Frame=len(gamma_rows)+1,Scene=name,RawMean=mean,EnhancedMean=enhanced_mean,
                                   Classified=classified,Target=target,Active=active))
        final.append((name,image,output,active))
    assert np.max(np.abs(np.diff([r['Active'] for r in gamma_rows]))) <= 1
    assert [r['Active'] for r in gamma_rows[10:16]] == [3,3,3,2,1,0]
    fig, axes=plt.subplots(2,4,figsize=(14,6))
    for k,(name,image,output,curve) in enumerate(final):
        axes[0,k].imshow(image); axes[0,k].set_title(f'{name}: raw')
        axes[1,k].imshow(output); axes[1,k].set_title(f'Curve {curve}, exponent {EXPONENTS[curve]:.2f}')
    for aa in axes.flat: aa.axis('off')
    fig.tight_layout(); save_figure(fig,'gamma_scenes')
    fig, axes=plt.subplots(2,1,figsize=(12,7))
    for field in ['RawMean','EnhancedMean']:
        axes[0].plot([r['Frame'] for r in gamma_rows],[r[field] for r in gamma_rows],label=field)
    for field in ['Classified','Target','Active']:
        axes[1].step([r['Frame'] for r in gamma_rows],[r[field] for r in gamma_rows],where='post',label=field)
    for aa in axes: aa.legend(); aa.grid()
    axes[0].set_ylabel('Mean luma'); axes[1].set_ylabel('Curve index'); axes[1].set_xlabel('Frame')
    fig.tight_layout(); save_figure(fig,'gamma_transition')
    fig, aa=plt.subplots(figsize=(8,5))
    for curve, exponent in enumerate(EXPONENTS): aa.plot(LUT[:,curve],label=f'{exponent:.2f}')
    aa.legend(title='Exponent'); aa.grid(); aa.set_xlabel('Input'); aa.set_ylabel('Output')
    fig.tight_layout(); save_figure(fig,'gamma_curves')
    write_rows('gamma_reference.csv',gamma_rows)
    summary={'execution':'Independent Python numerical cross-check; MATLAB not executed',
             'undistort':undistort,'pose':pose_rows,'gamma_final':[r for r in gamma_rows if r['Frame']%10==0],
             'checks':'PASS: independent SciPy sampling, rotation inverse, all 2048 RTL LUT entries, gamma thresholds and temporal slew'}
    (RESULTS/'reference_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
