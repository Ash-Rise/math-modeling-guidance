"""Q2 daily procurement with causal forecasts and real-time battery recourse.

The procurement LP is an approximate controller for the stated purchase-cost
objective. No perfect-information or global stochastic optimality is claimed.
"""
import numpy as np

from data import DT_H, SLOTS
from optimizer import plan


def forecast(history_load, history_pv, horizon_days=2):
    """Only completed days are passed in; no date-d truth is accessible here."""
    n = len(history_load)
    if not n:
        raise ValueError("Day one uses a declared zero-order cold start")
    loads = []
    for offset in range(horizon_days):
        idx = n + offset - 7
        loads.append(history_load[idx] if 0 <= idx < n else history_load[-1])
    # Frozen forecast: oldest-to-newest weights 1,...,7. Before Jan 8 only
    # available days are normalized; those warm-up errors never enter the pool.
    weights = np.arange(1, min(7, n)+1, dtype=float)
    pv = weights @ np.asarray(history_pv[-len(weights):]) / weights.sum()
    return (np.asarray(loads) - pv).reshape(-1) * DT_H


def procure(history_load, history_pv, residuals, price, initial, battery,
            quantile=None, horizon_days=2, forecast_model='base'):
    mean = (ar28_forecast if forecast_model=='ar28' else forecast)(history_load, history_pv, horizon_days)
    margin = np.zeros(SLOTS)
    if quantile is not None and len(residuals):
        margin = np.quantile(np.asarray(residuals), quantile, axis=0, method='linear')
    target = mean + np.tile(margin, horizon_days)
    result = plan(target, np.tile(price, horizon_days), initial, battery)
    result['full_prediction'] = mean
    result['prediction'] = mean[:SLOTS]
    result['target'] = target[:SLOTS]
    return result


def ar28_forecast(history_load, history_pv, horizon_days=2):
    """D9: fixed four-week half-life AR daily-level correction, history only.

    This corrects net load, not either physical load/PV component separately.
    Risk residuals must be rebuilt against this forecast at their issue dates.
    """
    mean = forecast(history_load, history_pv, horizon_days)
    levels = np.array([np.mean((history_load[h]-history_pv[h])*DT_H
        -forecast(history_load[:h],history_pv[:h],1)) for h in range(7,len(history_load))])
    if len(levels)<2:return mean
    a,b=levels[:-1],levels[1:]
    weights=2.**((np.arange(len(a))-(len(a)-1))/28.)
    denominator=np.sum(weights*a*a)
    beta=float(np.clip(np.sum(weights*a*b)/denominator,0,.95)) if denominator>1e-12 else 0.
    return mean+np.repeat(beta**np.arange(1,horizon_days+1)*levels[-1],SLOTS)


def execute(net, purchased, initial, battery, *, values=None, price=None):
    """Feedback within each slot: absorb surplus, discharge for actual deficit.

    Emergencies only fill the residual load shortage, never charge the battery.
    No future sample is accessed when choosing an executed action.
    """
    n = len(net)
    c, d, e, w = [np.zeros(n) for _ in range(4)]
    soc = np.empty(n + 1); soc[0] = initial
    for k in range(n):
        excess = purchased[k] - net[k]
        if excess >= 0:
            c[k] = min(excess, battery.max_kwh,
                           max(0., (battery.maximum-soc[k])/battery.eta_c))
            w[k] = max(0., excess-c[k])
        else:
            d[k] = min(-excess, battery.max_kwh,
                           max(0., (soc[k]-battery.minimum)*battery.eta_d))
            if values is not None:
                lower=soc[k]-d[k]/battery.eta_d
                points,continuation=values[k+1]
                next_states=np.r_[lower, points[(points>lower)&(points<soc[k])], soc[k]]
                discharge=(soc[k]-next_states)*battery.eta_d
                costs=5*price[k]*(-excess-discharge)+np.interp(next_states,points,continuation)
                d[k]=discharge[np.argmin(costs)]
            e[k] = max(0., -excess-d[k])
        soc[k+1] = soc[k] + battery.eta_c*c[k] - d[k]/battery.eta_d
    return dict(charge=c, discharge=d, emergency=e, unused=w, soc=soc)


def continuation_values(net, purchased, price, battery):
    """Exact convex piecewise-linear fixed-order recourse value.

    Future inputs are forecasts only. A discharge opportunity adds a segment
    of slope -5*p*eta_d and length discharge_limit/eta_d. Infimal convolution
    sorts marginal segments; free charging shifts and truncates the curve.
    No SOC grid, future truth, or extra terminal reward is used.
    """
    capacity=battery.maximum-battery.minimum
    slopes=np.array([0.]); lengths=np.array([capacity]); intercept=0.
    values=[None]*(len(net)+1)
    values[-1]=(np.array([battery.minimum,battery.maximum]),np.zeros(2))
    for k in range(len(net)-1,-1,-1):
        excess=purchased[k]-net[k]
        if excess>=0:
            shift=min(capacity,battery.eta_c*min(excess,battery.max_kwh))
            taken=np.minimum(lengths,np.maximum(0.,shift-np.r_[0.,np.cumsum(lengths)[:-1]]))
            intercept+=slopes@taken
            lengths=lengths-taken
            slopes=np.r_[slopes,0.];lengths=np.r_[lengths,shift]
        else:
            deficit=-excess
            slopes=np.r_[slopes,-5*price[k]*battery.eta_d]
            lengths=np.r_[lengths,min(deficit,battery.max_kwh)/battery.eta_d]
            order=np.argsort(slopes,kind='stable');slopes=slopes[order];lengths=lengths[order]
            lengths=np.minimum(lengths,np.maximum(0.,capacity-np.r_[0.,np.cumsum(lengths)[:-1]]))
            intercept+=5*price[k]*deficit
        keep=lengths>1e-9;slopes=slopes[keep];lengths=lengths[keep]
        points=battery.minimum+np.r_[0.,np.cumsum(lengths)]
        costs=intercept+np.r_[0.,np.cumsum(slopes*lengths)]
        values[k]=(points,costs)
    return values


def simulate(load, pv, price, battery, *, quantile=None, horizon_days=2,
             activate_day=31, control='value', forecast_model='base'):
    """D9: base point/greedy January warm-up; requested forecast/control from Feb 1.

    activate_day=8 is used only by the January reference regression test.
    Each day's order sees completed history only; real data enters execution.
    """
    days = len(load)
    arrays = {key: np.zeros((days, SLOTS)) for key in
              ['plan','charge','discharge','emergency','unused','prediction','target']}
    arrays['soc'] = np.zeros((days, SLOTS+1))
    residuals = []
    state = 6000.
    max_gap = 0.
    for day in range(days):
        net = (load[day]-pv[day])*DT_H
        values=None
        if day:
            alpha = quantile if day >= activate_day else None
            result=procure(load[:day],pv[:day],residuals,price,state,battery,alpha,horizon_days,
                           forecast_model if day>=activate_day else 'base')
            if day>=activate_day and control=='value':
                values=continuation_values(result['full_prediction'],result['plan'],
                                           np.tile(price,horizon_days),battery)
            arrays['plan'][day] = result['plan'][:SLOTS]
            arrays['prediction'][day] = result['prediction']
            arrays['target'][day] = result['target']
            max_gap = max(max_gap, abs(result['cost']-result['dual_cost']))
        actual = execute(net, arrays['plan'][day], state, battery,
                         values=values,price=price)
        for key in actual:
            arrays[key][day] = actual[key]
        state = actual['soc'][-1]
        if day >= 7:
            predictor=ar28_forecast if forecast_model=='ar28' else forecast
            residuals.append(net-predictor(load[:day],pv[:day],1))
    arrays['planned_cost'] = arrays['plan'] @ price
    arrays['emergency_cost'] = 5 * (arrays['emergency'] @ price)
    arrays['cost'] = arrays['planned_cost'] + arrays['emergency_cost']
    arrays['max_lp_dual_gap'] = max_gap
    return arrays
