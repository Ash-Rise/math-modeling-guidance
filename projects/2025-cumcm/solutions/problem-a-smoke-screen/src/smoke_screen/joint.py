"""DP-04: max over target rays AFTER min over eligible clouds.

Records passed to this module must already be filtered by assigned missile.
Search uses linearly interpolated crossings; reported intervals use Brent roots
and split at cloud availability events so no root crosses a discontinuity.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from .model import merge_intervals


def expiry(record: dict, missile: np.ndarray) -> float:
    b = record['explosion_time_s']
    return min(b + 20., np.linalg.norm(missile) / 300.,
               b + record['explosion_point_m'][2] / 3.)


def joint_radii(times, missile, records, points):
    times = np.asarray(times, dtype=float)
    missile = np.asarray(missile, dtype=float)
    result = np.full(len(times), np.inf)
    observers = missile * (1. - 300. * times[:, None] / np.linalg.norm(missile))
    # Safe necessary condition: any ray hit implies center-ray distance <=
    # R + enclosing-target radius, by the endpoint Hausdorff-distance bound.
    axis = np.array([0., 200., 5.]) - observers
    denom = np.sum(axis * axis, axis=1)
    eligible = []
    for r in records:
        b = r['explosion_time_s']
        c = np.tile(r['explosion_point_m'], (len(times), 1))
        c[:, 2] -= 3. * (times - b)
        w = c - observers
        lam = np.clip(np.sum(w * axis, axis=1) / denom, 0., 1.)
        near = np.linalg.norm(w - lam[:, None] * axis, axis=1) <= 10. + np.sqrt(74.) + 1e-9
        alive = (times >= b) & (times <= expiry(r, missile)) & near
        eligible.append((c, alive))
    use = np.flatnonzero(np.any([a for _, a in eligible], axis=0)) if eligible else []
    for start in range(0, len(use), 64):
        ids = use[start:start + 64]
        seg = points[None, :, :] - observers[ids, None, :]
        den = np.einsum('tpc,tpc->tp',seg,seg)
        best = np.full(den.shape, np.inf)
        for c, alive in eligible:
            if not alive[ids].any():
                continue
            w = c[ids] - observers[ids]
            dot = np.einsum('tpc,tc->tp',seg,w)
            lam = np.clip(dot / den, 0., 1.)
            # Expanded squared distance avoids two large (time,point,xyz)
            # temporaries. Roundoff is checked against the scalar formulation.
            d = np.einsum('tc,tc->t',w,w)[:,None] - 2*lam*dot + lam*lam*den
            d = np.maximum(d,0.)
            d[~alive[ids]] = np.inf
            best = np.minimum(best, d)
        result[ids] = np.sqrt(best.max(axis=1))
    return result


def intervals(missile, records, points, step=.01, refine=True):
    # An irrelevant cloud must not move the time-grid events and thereby
    # manufacture a numerical marginal contribution. Exclude only with a
    # conservative all-ray/all-time distance lower bound.
    records = [r for r in records if ray_distance_lower_bound(r,missile) <= 10.]
    events = sorted({x for r in records for x in
                     (r['explosion_time_s'], expiry(r, missile))
                     if 0 <= x <= np.linalg.norm(missile) / 300.})
    output = []
    for left, right in zip(events, events[1:]):
        active = [r for r in records
                  if r['explosion_time_s'] <= (left + right) / 2 <= expiry(r, missile)]
        if not active or right <= left:
            continue
        ts = np.linspace(left, right, max(2, int(np.ceil((right-left)/step))+1))
        vals = joint_radii(ts, missile, active, points) - 10.
        inside = vals <= 0.
        transitions = np.flatnonzero(inside[1:] != inside[:-1])
        roots = []
        for k in transitions:
            a, b = ts[k:k+2]
            if refine:
                root = brentq(lambda t: joint_radii([t], missile, active, points)[0]-10.,
                              a, b, xtol=1e-10)
            else:
                va, vb = np.minimum(vals[k:k+2], 1e3)
                root = a - va * (b-a) / (vb-va)
            roots.append(float(root))
        bounds = [left, *roots, right]
        state = bool(inside[0])
        for a, b in zip(bounds, bounds[1:]):
            if state:
                output.append((float(a), float(b)))
            state = not state
    return merge_intervals(output)


def ray_distance_lower_bound(record, missile, step=.25):
    missile=np.asarray(missile,dtype=float)
    b=record['explosion_time_s'];end=expiry(record,missile)
    if end<=b:
        return float('inf')
    ts=np.linspace(b,end,max(2,int(np.ceil((end-b)/step))+1))
    obs=missile*(1-300*ts[:,None]/np.linalg.norm(missile))
    c=np.tile(record['explosion_point_m'],(len(ts),1));c[:,2]-=3*(ts-b)
    axis=np.array([0.,200.,5.])-obs;w=c-obs
    lam=np.clip(np.sum(w*axis,axis=1)/np.sum(axis*axis,axis=1),0,1)
    return float(np.linalg.norm(w-lam[:,None]*axis,axis=1).min()
                 -303*(ts[1]-ts[0])/2-np.sqrt(74.))


def difference(intervals_a, intervals_b):
    out = []
    for left, right in intervals_a:
        cursor = left
        for a, b in intervals_b:
            if b <= cursor or a >= right:
                continue
            if a > cursor:
                out.append((cursor, min(a, right)))
            cursor = max(cursor, b)
        if cursor < right:
            out.append((cursor, right))
    return [(a,b) for a,b in out if b-a > 1e-8]
