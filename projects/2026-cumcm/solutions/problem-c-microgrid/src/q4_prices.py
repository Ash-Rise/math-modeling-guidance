"""Causal price candidates. Every forecaster receives a history prefix only."""
import numpy as np

SLOTS = 144
MODELS = ('last', 'day', 'week', 'weekly_mean', 'week_level', 'ridge', 'xgb', 'xgb_residual')
XGB_PARAMS = dict(n_estimators=80, max_depth=3, learning_rate=.05,
                  min_child_weight=20, reg_lambda=10., subsample=1.,
                  colsample_bytree=1., tree_method='hist', n_jobs=1,
                  random_state=2026, objective='reg:squarederror')
LASSO_PARAMS = dict(alpha=.001, max_iter=1000000, tol=1e-5, selection='cyclic', precompute=True)
# Match Lasso's L1 coefficient (.001), adding .0005 * ||beta||_2^2.
ELASTIC_PARAMS = {**LASSO_PARAMS, 'alpha': .002, 'l1_ratio': .5}
LGB_PARAMS = dict(n_estimators=80, max_depth=3, num_leaves=8, learning_rate=.05,
                  min_child_samples=20, reg_lambda=10., n_jobs=1,
                  random_state=2026, deterministic=True, force_col_wise=True,
                  verbosity=-1)
QUANTILES = np.array([.1, .5, .9])
FEATURE_NAMES = ('week_same_slot', 'latest_same_slot', 'two_week_same_slot',
                 'daily7_same_slot_mean', 'weekly_mean', 'last24h_week_level',
                 'slot_fraction', 'slot_sin', 'slot_cos', 'weekday_fraction',
                 'lead_fraction', 'issue_fraction',
                 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')


def features(history, origin, targets):
    """Same features for all learned candidates; all lookup indices < origin.

    Targets may be beyond the observed year. No target-side unobserved lag is
    substituted with truth: same-slot lags roll back by full days/weeks.
    Calendar origin is Jan 1 2025, a Wednesday.
    """
    h = np.asarray(history)[:origin]
    targets = np.asarray(targets)
    assert len(h) == origin and origin >= SLOTS
    slots = targets % SLOTS
    latest = origin-1-((origin-1-slots) % SLOTS)
    week_idx = targets-1008
    week_idx -= np.maximum(0, (week_idx-origin+1008)//1008)*1008
    week_idx = np.where(week_idx >= 0, week_idx, latest)
    week = h[week_idx]
    two = np.where(week_idx-1008 >= 0, week_idx-1008, week_idx)
    profile = np.stack([h[np.maximum(latest-k*SLOTS, slots)] for k in range(min(7, origin//SLOTS))]).mean(0)
    sameweeks = np.stack([h[np.where(week_idx-k*1008 >= 0, week_idx-k*1008, week_idx)] for k in range(3)]).mean(0)
    # Last completed day's level shift relative to its week-ago counterpart.
    count = min(SLOTS, max(0, origin-1008))
    level = float(np.mean(h[origin-count:]-h[origin-count-1008:origin-1008])) if count else 0.
    dow = (targets//SLOTS+2) % 7
    return np.column_stack([week, h[latest], h[two], profile, sameweeks,
                            np.full(len(targets), level), slots/SLOTS,
                            np.sin(2*np.pi*slots/SLOTS), np.cos(2*np.pi*slots/SLOTS),
                            dow/6, (targets-origin)/288,
                            np.full(len(targets), (origin%SLOTS)/SLOTS),
                            *[(dow == k).astype(float) for k in range(7)]])


def basic(history, origin, targets, name):
    x = features(history, origin, targets)
    if name == 'last':
        return np.full(len(targets), history[-1])
    if name == 'day':
        return x[:, 1]
    if name == 'week':
        return x[:, 0]
    if name == 'weekly_mean':
        return x[:, 4]
    if name == 'week_level':
        return np.maximum(1e-6, x[:, 0]+x[:, 5])
    raise ValueError(name)


def price_forecast(history, origin, targets, name, training=None, *, diagnostics=None):
    assert len(history) == origin  # boundary enforced independently of caller
    if name in MODELS[:5]:
        return basic(history, origin, targets, name)
    if training is None:
        training = training_rows(history, origin)
    x, y, valid = training
    keep = valid < origin  # each individual training LABEL must have occurred
    x, y = x[keep], y[keep]
    future = features(history, origin, targets)
    base_column = 4 if name in ('lasso_weekly_mean', 'elastic_net_weekly_mean') else 0
    if not len(y):
        return future[:, base_column]
    if name in ('ridge', 'lasso', 'lasso_weekly_mean', 'elastic_net_weekly_mean'):
        from sklearn.linear_model import Ridge, Lasso, ElasticNet
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        if name == 'ridge':
            estimator = Ridge(alpha=100.)
        elif name == 'elastic_net_weekly_mean':
            estimator = ElasticNet(**ELASTIC_PARAMS)
        else:
            estimator = Lasso(**LASSO_PARAMS)
        fit = make_pipeline(StandardScaler(), estimator)
        # Strongly collinear columns can need >100k cheap Gram iterations.
        # Never silently score an unconverged linear candidate.
        import warnings
        from sklearn.exceptions import ConvergenceWarning
        with warnings.catch_warnings():
            warnings.simplefilter('error', ConvergenceWarning)
            # x's baseline was constructed at EACH historical issue, never
            # recomputed retrospectively using the current origin's history.
            fit.fit(x, y-x[:, base_column])
        pred = future[:, base_column]+fit.predict(future)
        if diagnostics is not None:
            estimator = fit[-1]
            diagnostics.update(coefficients=estimator.coef_.tolist(),
                               intercept=float(estimator.intercept_),
                               iterations=None if name == 'ridge' else int(estimator.n_iter_),
                               dual_gap=None if name == 'ridge' else float(estimator.dual_gap_))
    elif name == 'lgb':
        from lightgbm import LGBMRegressor
        fit = LGBMRegressor(**LGB_PARAMS, objective='regression')
        fit.fit(x, y)
        pred = fit.booster_.predict(future)
    elif name in ('xgb', 'xgb_residual'):
        from xgboost import XGBRegressor
        fit = XGBRegressor(**XGB_PARAMS)
        fit.fit(x, y-x[:, 0] if name == 'xgb_residual' else y)
        pred = fit.predict(future)
        if name == 'xgb_residual':
            pred += future[:, 0]
    else:
        raise ValueError(name)
    return np.maximum(1e-6, pred)


def quantile_forecast(history, origin, targets, name, training=None):
    """P10/P50/P90 fitted on the identical causal rows; return ordered and raw.

    Row-wise monotone rearrangement is fixed before evaluation. It uses no truth
    and leaves the middle quantile equal to the median of the three raw outputs.
    """
    assert len(history) == origin
    x, y, valid = training_rows(history, origin) if training is None else training
    keep = valid < origin
    x, y = x[keep], y[keep]
    future = features(history, origin, targets)
    if not len(y):
        raw = np.repeat(future[:, :1], 3, axis=1)
    elif name == 'xgb_quantile':
        from xgboost import XGBRegressor
        params = {**XGB_PARAMS, 'objective': 'reg:quantileerror', 'quantile_alpha': QUANTILES.tolist()}
        fit = XGBRegressor(**params).fit(x, y)
        raw = fit.predict(future)
    elif name == 'lgb_quantile':
        from lightgbm import LGBMRegressor
        fits = [LGBMRegressor(**LGB_PARAMS, objective='quantile', alpha=float(q)).fit(x, y) for q in QUANTILES]
        raw = np.column_stack([fit.booster_.predict(future) for fit in fits])
    else:
        raise ValueError(name)
    return np.maximum(1e-6, np.sort(raw, axis=1)), raw


def prepare_extension(price, models):
    """One shared training-row construction per release, no persistent caches."""
    forecasts = {m: np.zeros((len(price), 4, 288)) for m in models}
    intervals = {m: np.zeros((len(price), 4, 288, 3)) for m in models if m.endswith('_quantile')}
    crossings = {m: np.zeros((len(price), 4, 288), dtype=bool) for m in intervals}
    flat = price.ravel()
    for day in range(1, len(price)):
        for j in range(4):
            start, origin = 36*j, day*144+36*j
            target = np.arange(origin, (day+2)*144)
            history = flat[:origin]
            training = training_rows(history, origin)
            for m in models:
                if m in intervals:
                    ordered, raw = quantile_forecast(history, origin, target, m, training)
                    intervals[m][day, j, start:] = ordered
                    crossings[m][day, j, start:] = (np.diff(raw, axis=1) < 0).any(axis=1)
                    forecasts[m][day, j, start:] = ordered[:, 1]
                else:
                    forecasts[m][day, j, start:] = price_forecast(history, origin, target, m, training)
        if day % 7 == 0:
            print(f'extended price fits completed through day {day+1}', flush=True)
    return forecasts, intervals, crossings


def training_rows(history, origin):
    xs, ys, ts = [], [], []
    for old in range(144, origin, 36):
        target = np.arange(old, min((old//144+2)*144, origin))
        xs.append(features(history[:old], old, target))
        ys.append(history[target]); ts.append(target)
    if not xs:
        return np.empty((0, 19)), np.empty(0), np.empty(0, dtype=int)
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ts)


def prepare_prices(price, models=MODELS, *, diagnostics=None):
    """Re-fit at each procurement release; storage is only an offline cache.

    Residual corrections use completed historical target DAYS and the same
    release/target slot, with next-day targets maturing one day later.
    """
    days = len(price)
    forecasts = {m: np.zeros((days, 4, 288)) for m in models}
    flat = price.ravel()
    for day in range(1, days):
        for j in range(4):
            start, origin = 36*j, day*144+36*j
            target = np.arange(origin, (day+2)*144)
            history = flat[:origin]
            training = training_rows(history, origin) if any(m not in MODELS[:5] for m in models) else None
            for m in models:
                detail = {} if diagnostics is not None and m in diagnostics else None
                forecasts[m][day, j, start:] = price_forecast(history, origin, target, m, training, diagnostics=detail)
                if detail:
                    diagnostics[m].append(dict(day=day, hour=6*j, **detail))
        if day % 7 == 0:
            print(f'price fits completed through day {day+1}', flush=True)
    return forecasts


def error_adjustments(price, predictions):
    """Bias, signed Q.8 correction and symmetric 90%/80% marginal-error radii.

    These are empirical history summaries, not guaranteed future coverage or
    joint confidence sets. No Gaussian or independence assumption is made.
    """
    bias, quantile, radius, radius80 = [np.zeros_like(predictions) for _ in range(4)]
    for day in range(8, len(price)):
        for j in range(4):
            start = 36*j
            for a, b, old, truth in [(start, 144, predictions[7:day, j, start:144], price[7:day, start:]),
                                     (144, 288, predictions[7:day-1, j, 144:], price[8:day])]:
                if not len(old):
                    continue
                residual = truth-old
                bias[day, j, a:b] = residual.mean(0)
                quantile[day, j, a:b] = np.quantile(residual, .8, axis=0)
                radius[day, j, a:b] = np.quantile(abs(residual), .9, axis=0)
                radius80[day, j, a:b] = np.quantile(abs(residual), .8, axis=0)
    return dict(bias=bias, quantile=quantile, radius=radius, radius80=radius80)
