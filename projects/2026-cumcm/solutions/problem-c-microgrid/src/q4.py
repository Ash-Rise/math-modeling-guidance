"""Q4 simulation: inherited Q2/Q3 control with forecast/settlement prices separated.

Point, box and budgeted price uncertainty share exactly the same physical LP.
Inherited net forecasts, price/control rules and the original warm-up are retained.
"""
from time import perf_counter
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix, hstack, vstack, diags, eye

from optimizer import Battery
from q2 import forecast, ar28_forecast, continuation_values, execute
from q3 import prepare_forecasts, risk_targets, revision_cost


def make_lp(target, price, initial, battery, baseline=None, accrued=None,
            radius=None, gamma=None):
    """Uncertainty is applied to nonnegative cumulative settlement exposure.

    For pending current-day slots exposure = accrued + 1.5u - .5v;
    for tomorrow's auxiliary slots exposure = q. The nominal accrued cost is
    a constant, but MUST remain inside the budgeted uncertainty support.
    gamma=None is a point/box LP; gamma in [0,n] uses Bertsimas-Sim support.
    """
    target, price = np.asarray(target), np.asarray(price)
    n = len(target); m = 0 if baseline is None else len(baseline)
    assert price.shape == target.shape and np.all(price > 0)
    width = 4*n+2*m
    ix = np.arange(n)
    au = coo_matrix((np.tile([-1., 1., -1.], (n, 1)).ravel(),
                    (np.repeat(ix, 3), np.column_stack([ix, n+ix, 2*n+ix]).ravel())),
                   shape=(n, width)).tocsr()
    rr, cc, vv = [], [], []
    for k in range(n):
        rr.extend([k]*3); cc.extend([n+k, 2*n+k, 3*n+k]); vv.extend([-battery.eta_c, 1/battery.eta_d, 1.])
        if k:
            rr.append(k); cc.append(3*n+k-1); vv.append(-1.)
    for k in range(m):
        rr.extend([n+k]*3); cc.extend([k, 4*n+k, 4*n+m+k]); vv.extend([1., -1., 1.])
    ae = coo_matrix((vv, (rr, cc)), shape=(n+m, width)).tocsr()
    be = np.r_[initial, np.zeros(n-1), np.asarray(baseline) if m else []]
    bounds = ([(0, None)]*n + [(0, battery.max_kwh)]*(2*n)
              + [(battery.minimum, battery.maximum)]*n)
    if m:
        bounds += [(0, None)]*m + [(0, max(0., float(b))) for b in baseline]
    er, ec, ev = list(range(m, n)), list(range(m, n)), [1.]*(n-m)
    for k in range(m):
        er.extend([k, k]); ec.extend([4*n+k, 4*n+m+k]); ev.extend([1.5, -.5])
    exposure_map = coo_matrix((ev, (er, ec)), shape=(n, width)).tocsr()
    constant = np.r_[accrued, np.zeros(n-m)] if m else np.zeros(n)
    if m:
        assert accrued is not None and np.all(np.asarray(accrued) >= np.asarray(baseline)-1e-6)
    objective = np.asarray(price @ exposure_map).ravel()
    bu = -target
    if gamma is not None:
        radius = np.asarray(radius)
        assert 0 <= gamma <= n and radius.shape == price.shape and np.all(radius >= 0)
        au = vstack([hstack([au, csr_matrix((n, n+1))]),
                     hstack([diags(radius) @ exposure_map, -np.ones((n, 1)), -eye(n)])]).tocsr()
        bu = np.r_[bu, -radius*constant]
        ae = hstack([ae, csr_matrix((n+m, n+1))]).tocsr()
        objective = np.r_[objective, gamma, np.ones(n)]
        bounds += [(0, None)]*(n+1)
    return dict(c=objective, A_ub=au, b_ub=bu, A_eq=ae, b_eq=be, bounds=bounds)


def solve_lp(lp, method='highs'):
    tic = perf_counter()
    result = linprog(**lp, method=method)
    seconds = perf_counter()-tic
    if not result.success:
        raise RuntimeError(result.message)
    dual = float(lp['b_ub']@result.ineqlin.marginals+lp['b_eq']@result.eqlin.marginals)
    for k, (lo, hi) in enumerate(lp['bounds']):
        if lo is not None:
            dual += lo*result.lower.marginals[k]
        if hi is not None:
            dual += hi*result.upper.marginals[k]
    equality = float(abs(lp['A_eq']@result.x-lp['b_eq']).max())
    inequality = float(np.maximum(lp['A_ub']@result.x-lp['b_ub'], 0).max())
    bound_error = max(max(0., (lo or 0)-result.x[k], result.x[k]-hi if hi is not None else 0.)
                      for k, (lo, hi) in enumerate(lp['bounds']))
    return result.x, dict(seconds=seconds, objective=float(result.fun),
                          dual_gap=abs(float(result.fun)-dual),
                          primal_error=max(equality, inequality, bound_error),
                          iterations=int(result.nit), crossover=int(result.crossover_nit))


def prepare_net(load, pv, releases, *, alpha_q42=.782, alpha_q43=.70):
    """Frozen defaults; keyword overrides are diagnostic only, never selected here."""
    q2mean = np.zeros((len(load), 4, 288))
    q2target = q2mean.copy(); residuals = []
    for day in range(1, len(load)):
        mean = ar28_forecast(load[:day], pv[:day], 2)
        margin = np.quantile(residuals, alpha_q42, axis=0) if residuals else np.zeros(144)
        q2mean[day, 0] = mean
        q2target[day, 0] = mean+np.tile(margin, 2)
        if day >= 7:
            residuals.append((load[day]-pv[day])/6-mean[:144])
    prepared = prepare_forecasts(load, pv, releases)
    return {2: (q2mean, q2target), 3: (prepared['mean'], risk_targets(load, pv, prepared, alpha_q43))}


def simulate(load, pv, actual_price, means, targets, predictions, corrections,
             branch, treatment='point', method='highs', *, activate_day=8,
             warmup=None, start_day=0, initial=6000., capture=None):
    """Jan pilot starts Jan 9 after common causal Q4 point/greedy warm-up.

    Formal validation (activate_day=31) uses that same predeclared weekly
    price, point-load/greedy January, NOT retrospectively selected control.
    Current realized price is read only by the single-slot execution and by
    ex-post accounting. Continuation curves use forecast prices only.
    """
    battery = Battery(.9, .9); days = len(load)
    out = {k: np.zeros((days, 144)) for k in
           ('plan', 'effective', 'charge', 'discharge', 'emergency', 'unused', 'exposure')}
    out['soc'] = np.zeros((days, 145))
    out['versions'] = np.zeros((days, 4, 144))
    out['lp_stats'] = []
    begin = start_day
    if warmup is not None:
        begin = min(activate_day, days)
        for key in ('plan', 'effective', 'charge', 'discharge', 'emergency', 'unused', 'soc', 'exposure', 'versions'):
            out[key][:begin] = warmup[key][:begin]
        initial = float(warmup['soc'][begin-1, -1])
    soc = initial
    for day in range(begin, days):
        active = day >= activate_day
        orders = np.zeros(288); accrued = np.zeros(144)
        for j in range(4 if active and branch == 3 else 1):
            start = j*36
            end = start+36 if active and branch == 3 else 144
            values = None
            if day:
                p = predictions[day, j, start:].copy()
                rad = corrections['radius'][day, j, start:]
                if active and treatment == 'bias':
                    p = np.maximum(1e-6, p+corrections['bias'][day, j, start:])
                if active and treatment == 'q80':
                    p = np.maximum(1e-6, p+corrections['quantile'][day, j, start:])
                nominal = p.copy()
                if active and treatment == 'box':
                    p += rad
                if active and treatment == 'interval_half':
                    p += .5*rad
                # Same forecast continuation for every uncertainty treatment:
                # robustification is only of procurement, not a claim of robust DP.
                gamma = float(treatment.split('_')[1])*len(p) if active and treatment.startswith('budget_') else None
                target = targets[day, j, start:] if active else forecast(load[:day],pv[:day],2)
                lp = make_lp(target, p, soc, battery,
                             baseline=orders[start:144] if j else None,
                             accrued=accrued[start:] if j else None,
                             radius=rad, gamma=gamma)
                solution, stats = solve_lp(lp, method)
                out['lp_stats'].append(stats)
                if capture is not None:
                    capture(day, j, lp)
                new = np.maximum(solution[:len(p)], 0.)
                if j:
                    accrued[start:] += revision_cost(orders[start:144], new[:144-start], 1.)
                else:
                    accrued[:] = new[:144]
                    out['plan'][day] = new[:144]
                orders[start:] = new
                if active:
                    values = continuation_values(means[day, j, start:], orders[start:], nominal, battery)
            out['versions'][day, j] = orders[:144]
            if not (active and branch == 3):
                out['versions'][day] = orders[:144]
            for slot in range(start, end):
                # This sample belongs to the current supply interval; it has
                # occurred at execution, never at the earlier procurement solve.
                actual = execute((load[day, slot:slot+1]-pv[day, slot:slot+1])/6,
                                 orders[slot:slot+1], soc, battery,
                                 values=None if values is None else values[slot-start:],
                                 price=actual_price[day, slot:slot+1])
                for key in ('charge', 'discharge', 'emergency', 'unused'):
                    out[key][day, slot] = actual[key][0]
                out['soc'][day, slot:slot+2] = actual['soc']
                soc = float(actual['soc'][-1])
        out['effective'][day] = orders[:144]
        out['exposure'][day] = accrued
    out['planned_cost'] = (actual_price*out['plan']).sum(1)
    out['adjustment_cost'] = (actual_price*(out['exposure']-out['plan'])).sum(1)
    out['emergency_cost'] = 5*(actual_price*out['emergency']).sum(1)
    out['cost'] = out['planned_cost']+out['adjustment_cost']+out['emergency_cost']
    return out


def summary(x, start, stop):
    costs = x['cost'][start:stop]
    return dict(cost=float(costs.sum()), planned=float(x['planned_cost'][start:stop].sum()),
                adjustment=float(x['adjustment_cost'][start:stop].sum()),
                emergency=float(x['emergency_cost'][start:stop].sum()),
                emergency_kwh=float(x['emergency'][start:stop].sum()),
                initial_soc=float(x['soc'][start, 0]), final_soc=float(x['soc'][stop-1, -1]),
                max_day_cost=float(costs.max()))
