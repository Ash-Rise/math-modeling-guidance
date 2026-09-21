"""Q3: two-layer rolling scheduling based on Economic MPC.

Upper layer: procurement Economic MPC at 0/6/12/18h using actual SOC,
effective orders and forecasts available at that release.
Lower layer: fixed-order battery inventory-value feedback every ten minutes,
using actual net demand and SOC; it is not a second procurement MPC.
The horizon shrinks from 48 to 30 hours within a day, then rolls at midnight.
Only today's orders are committed; tomorrow's purchases are a planning proxy.
This is a cost-based, risk-adjusted approximation, not stochastic optimal MPC.
See paper/paper.md, section 5, for the accepted model explanation.
"""
from datetime import datetime, timedelta

import numpy as np
from openpyxl import load_workbook
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from data import INPUT, SLOTS, DT_H
from optimizer import plan
from q2 import ar28_forecast, continuation_values, execute


def read_releases():
    book = load_workbook(INPUT / '附件3.xlsx', read_only=True, data_only=True)
    rows = list(book.active.values)
    book.close()
    assert rows[0][2:] == tuple(f'预报{h}小时' for h in range(1, 25))
    assert len(rows) == 1461
    values = []
    day = None
    for i, row in enumerate(rows[1:]):
        if row[0] not in (None, ''):
            day = datetime.strptime(row[0], '%Y-%m-%d')
        issue = day + timedelta(hours=int(row[1].split(':')[0]))
        assert issue == datetime(2025, 1, 1) + timedelta(hours=6*i)
        values.append(row[2:])
    cube = np.asarray(values, float).reshape(365, 4, 24)
    assert np.isfinite(cube).all() and (cube >= 0).all()
    return cube


def disaggregate(hourly, anchor, method='linear'):
    """Right endpoints 10,...,1440 minutes after issue; anchor is already known."""
    if method == 'hold':
        return np.repeat(hourly, 6)
    if method != 'linear':
        raise ValueError(method)
    return np.interp(np.arange(1, 145), np.arange(0, 145, 6), np.r_[anchor, hourly])


def prepare_forecasts(load, pv, releases, mode='blend', interpolation='linear'):
    """Each row uses completed history and its own release, never later versions.

    Convex fusion minimizes past squared PV error in four six-hour lead blocks.
    Only fully observed 24h windows (and complete dates) enter that regression.
    Net-residual margins are computed separately for each release and target slot.
    The auxiliary horizon always ends at next midnight (the Q2 48h boundary).
    """
    days = len(load)
    means = np.zeros((days, 4, 288))
    weights = np.ones((days, 4, 4))
    base_pv = np.zeros((days, 288))
    official = np.zeros((days, 4, 144))
    for day in range(1, days):
        w = np.arange(1, min(7, day)+1, dtype=float)
        base_pv[day] = np.tile(w @ pv[day-len(w):day] / w.sum(), 2)
        base_net = ar28_forecast(load[:day], pv[:day], 2)
        for j in range(4):
            start = j*36
            anchor = pv[day-1, -1] if j == 0 else pv[day, start-1]
            official[day, j] = disaggregate(releases[day, j], anchor, interpolation)
            # j=0's prior day window is complete; j>0's is not until next midnight.
            mature = range(7, day if j == 0 else day-1)
            numerator = np.zeros(4); denominator = np.zeros(4)
            for old in mature:
                base = base_pv[old, start:start+144]
                delta = official[old, j] - base
                truth = pv.reshape(-1)[old*144+start:old*144+start+144]
                numerator += (delta*(truth-base)).reshape(4, 36).sum(axis=1)
                denominator += (delta*delta).reshape(4, 36).sum(axis=1)
            beta = np.clip(np.divide(numerator, denominator, out=np.ones(4),
                                     where=denominator > 1e-12), 0., 1.)
            if mode == 'raw':
                beta[:] = 1.
            elif mode == 'history':
                beta[:] = 0.
            elif mode != 'blend':
                raise ValueError(mode)
            weights[day, j] = beta
            means[day, j] = base_net
            means[day, j, start:start+144] -= np.repeat(beta, 36) * (official[day, j]-base_pv[day, start:start+144])*DT_H
    return dict(mean=means, weights=weights)


def risk_targets(load, pv, prepared, alpha):
    """Alpha=.70 is a uniform economic-risk quantile level, not an MPC parameter.

    Deterministic Economic MPC absorbs new information by replanning; this
    quantile corrects the forecast uncertainty remaining at each solve.
    Separate causal residual pools yield release-specific kWh corrections.
    Targets constrain the order LP; battery continuation uses unshifted means.
    Alpha is neither a reliability constraint nor an objective penalty weight.
    A future stochastic/robust MPC could replace this correction with a fuller
    uncertainty model; the current implementation does not introduce one.
    """
    means = prepared['mean']
    targets = means.copy()
    truth = (load-pv)*DT_H
    for day in range(8, len(load)):
        for j in range(4):
            start = j*36
            if alpha is not None:
                residual = truth[7:day, start:] - means[7:day, j, start:144]
                targets[day, j, start:144] += np.quantile(residual, alpha, axis=0, method='linear')
                # Next-day targets mature one day later; no current-day residuals.
                if day > 8:
                    residual = truth[8:day] - means[7:day-1, j, 144:]
                    targets[day, j, 144:] += np.quantile(residual, alpha, axis=0, method='linear')
    return targets


def revision_cost(before, after, price):
    change = np.asarray(after)-np.asarray(before)
    return np.asarray(price)*(1.5*np.maximum(change, 0)-.5*np.maximum(-change, 0))


def revise(target, price, initial, battery, baseline):
    """Convex LP for today's remaining order and tomorrow's uncommitted proxy.

    Variables q,c,d,E,u,v. q-u+v=b on today's slots, 0<=v<=b.
    Past fees are sunk. Objective = 1.5*p*u-.5*p*v + tomorrow's p*q.
    Initial is the actual SOC at release; baseline is the latest effective
    order restricted to unexecuted slots, not the original midnight order.
    No binary variables: simultaneous increase/decrease is strictly dominated.
    """
    target, price, baseline = map(lambda x: np.asarray(x, float), (target, price, baseline))
    n, m = len(target), len(baseline)
    assert len(price) == n and 0 < m <= n and (baseline >= -1e-7).all()
    rr, cc, vv = [], [], []
    for k in range(n):
        rr.extend([k]*3); cc.extend([n+k, 2*n+k, 3*n+k]); vv.extend([-battery.eta_c, 1/battery.eta_d, 1.])
        if k:
            rr.append(k); cc.append(3*n+k-1); vv.append(-1.)
    for k in range(m):
        rr.extend([n+k]*3); cc.extend([k, 4*n+k, 5*n+k]); vv.extend([1., -1., 1.])
    ae = coo_matrix((vv, (rr, cc)), shape=(n+m, 6*n)).tocsr()
    rhs = np.r_[initial, np.zeros(n-1), baseline]
    ix = np.arange(n)
    au = coo_matrix((np.tile([-1., 1., -1.], (n, 1)).ravel(),
                    (np.repeat(ix, 3), np.column_stack([ix, n+ix, 2*n+ix]).ravel())),
                   shape=(n, 6*n)).tocsr()
    objective = np.r_[np.r_[np.zeros(m), price[m:]], np.zeros(3*n),
                      np.r_[1.5*price[:m], np.zeros(n-m)],
                      np.r_[-.5*price[:m], np.zeros(n-m)]]
    bounds = ([(0, None)]*n + [(0, battery.max_kwh)]*(2*n)
              + [(battery.minimum, battery.maximum)]*n
              + [(0, None)]*m + [(0, 0)]*(n-m)
              + [(0, max(0., b)) for b in baseline] + [(0, 0)]*(n-m))
    result = linprog(objective, A_ub=au, b_ub=-target, A_eq=ae, b_eq=rhs,
                     bounds=bounds, method='highs')
    if not result.success:
        raise RuntimeError(result.message)
    dual = float((-target) @ result.ineqlin.marginals + rhs @ result.eqlin.marginals)
    for k, (lo, hi) in enumerate(bounds):
        dual += lo*result.lower.marginals[k]
        if hi is not None:
            dual += hi*result.upper.marginals[k]
    q = result.x[:n]
    cost = float(revision_cost(baseline, q[:m], price[:m]).sum()+price[m:]@q[m:])
    return dict(plan=q, cost=cost, dual_cost=dual)


def simulate(load, pv, price, battery, prepared, targets, warmup, *,
             activate_day=31, adjust=(6, 12, 18), observe=(6, 12, 18)):
    """Two-layer loop: procurement Economic MPC and fixed-order battery feedback.

    Default Q3 updates at 0/6/12/18h, executes only the next six-hour block,
    and reinitializes each LP with the measured/simulated actual SOC. The
    lower inventory-value controller uses actual net demand and SOC every ten
    minutes; it does not re-solve the procurement MPC at that frequency.
    Today's future orders remain binding across releases; they are not discarded
    freely at the next solve. The horizon endpoint is next day's 24:00.

    Common frozen Q2 warm-up; release information and trading are distinct.
    Observe-only releases refresh continuation values and the auxiliary next-day
    plan. They cannot change any purchased electricity for today.
    """
    days = len(load)
    arrays = {key: np.zeros((days, 144)) for key in
              ['plan', 'effective', 'charge', 'discharge', 'emergency', 'unused']}
    arrays['soc'] = np.zeros((days, 145))
    arrays['versions'] = np.zeros((days, 4, 144))
    arrays['revision_fee'] = np.zeros((days, 3, 144))
    arrays['max_lp_dual_gap'] = 0.
    prefix = min(activate_day, days)
    for key in ['plan', 'charge', 'discharge', 'emergency', 'unused', 'soc']:
        arrays[key][:prefix] = warmup[key][:prefix]
    arrays['effective'][:prefix] = warmup['plan'][:prefix]
    arrays['versions'][:prefix] = warmup['plan'][:prefix, None, :]
    actual_soc = float(warmup['soc'][prefix-1, -1]) if prefix else 6000.
    horizon_price = np.tile(price, 2)
    for day in range(activate_day, days):
        r = plan(targets[day, 0], horizon_price, actual_soc, battery)
        arrays['max_lp_dual_gap'] = max(arrays['max_lp_dual_gap'], abs(r['cost']-r['dual_cost']))
        arrays['plan'][day] = r['plan'][:144]
        orders = r['plan'].copy()
        prediction = prepared['mean'][day, 0].copy()
        values = continuation_values(prediction, orders, horizon_price, battery)
        for j in range(4):
            start, end = j*36, (j+1)*36
            if j and j*6 in observe:
                prediction = prepared['mean'][day, j, start:]
                if j*6 in adjust:
                    r = revise(targets[day, j, start:], horizon_price[start:], actual_soc,
                               battery, orders[start:144])
                    arrays['max_lp_dual_gap'] = max(arrays['max_lp_dual_gap'], abs(r['cost']-r['dual_cost']))
                    arrays['revision_fee'][day, j-1, start:] = revision_cost(
                        orders[start:144], r['plan'][:144-start], price[start:])
                    orders[start:] = r['plan']  # Effective baseline for the next release.
                # An information-only update may use tomorrow's forecast to value
                # inventory. Optimize that auxiliary order conditional on today's
                # retained schedule using a fixed-order LP.
                else:
                    r = fixed_today(targets[day, j, start:], horizon_price[start:], actual_soc,
                                    battery, orders[start:144])
                    orders[144:] = r['plan'][144-start:]
                values = continuation_values(prediction, orders[start:], horizon_price[start:], battery)
                value_offset = start
            elif j == 0:
                value_offset = 0
            arrays['versions'][day, j] = orders[:144]
            actual = execute((load[day, start:end]-pv[day, start:end])*DT_H,
                             orders[start:end], actual_soc, battery,
                             values=values[start-value_offset:], price=price[start:end])
            for key in ['charge', 'discharge', 'emergency', 'unused']:
                arrays[key][day, start:end] = actual[key]
            arrays['soc'][day, start:end+1] = actual['soc']
            actual_soc = float(actual['soc'][-1])  # Never substitute the LP's SOC.
        arrays['effective'][day] = orders[:144]
    arrays['planned_cost'] = arrays['plan'] @ price
    arrays['adjustment_cost'] = arrays['revision_fee'].sum(axis=(1, 2))
    arrays['emergency_cost'] = 5*(arrays['emergency'] @ price)
    arrays['cost'] = arrays['planned_cost']+arrays['adjustment_cost']+arrays['emergency_cost']
    return arrays


def fixed_today(target, price, initial, battery, baseline):
    """Fixed current orders; feasible recourse shortage at 5p and free surplus.

    Used solely for information-only ablations, with tomorrow's purchases free
    to be optimized. Emergency proxy is not an executed or prepaid order.
    """
    n, m = len(target), len(baseline)
    rr, cc, vv = [], [], []
    for k in range(n):
        rr.extend([k]*3); cc.extend([n+k, 2*n+k, 3*n+k]); vv.extend([-battery.eta_c, 1/battery.eta_d, 1.])
        if k:
            rr.append(k); cc.append(3*n+k-1); vv.append(-1.)
    ae = coo_matrix((vv, (rr, cc)), shape=(n, 5*n)).tocsr()
    ix = np.arange(n)
    au = coo_matrix((np.tile([-1., 1., -1., -1.], (n, 1)).ravel(),
                    (np.repeat(ix, 4), np.column_stack([ix, n+ix, 2*n+ix, 4*n+ix]).ravel())),
                   shape=(n, 5*n)).tocsr()
    bounds = ([(b, b) for b in baseline]+[(0, None)]*(n-m)
              + [(0, min(battery.max_kwh, max(0., baseline[k]-target[k]))) for k in range(m)]
              + [(0, battery.max_kwh)]*(n-m)
              + [(0, min(battery.max_kwh, max(0., target[k]-baseline[k]))) for k in range(m)]
              + [(0, battery.max_kwh)]*(n-m)+[(battery.minimum, battery.maximum)]*n
              + [(0, None)]*m+[(0, 0)]*(n-m))
    result = linprog(np.r_[np.r_[np.zeros(m), price[m:]], np.zeros(3*n), 5*price],
                     A_ub=au, b_ub=-np.asarray(target), A_eq=ae,
                     b_eq=np.r_[initial, np.zeros(n-1)], bounds=bounds, method='highs')
    if not result.success:
        raise RuntimeError(result.message)
    return dict(plan=result.x[:n])
