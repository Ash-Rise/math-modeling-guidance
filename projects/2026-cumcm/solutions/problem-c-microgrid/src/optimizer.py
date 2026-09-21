"""Sparse energy-flow LP. Efficiency is an explicit input, never a hidden default."""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix


@dataclass(frozen=True)
class Battery:
    eta_c: float
    eta_d: float
    minimum: float = 1200.0
    maximum: float = 10800.0
    max_kwh: float = 5000 / 6


def plan(net_kwh, price, initial, battery, *, terminal=None):
    """Known-trajectory conditional LP; no stochastic/online optimality claim.

    Variables q,c,d,E(1..n). Net supply may exceed demand without revenue.
    Terminal is None for a free end state or an explicit required SOC.
    """
    net = np.asarray(net_kwh, float)
    price = np.asarray(price, float)
    n = len(net)
    assert price.shape == net.shape and np.all(price > 0)
    assert battery.minimum <= initial <= battery.maximum
    assert 0 < battery.eta_c <= 1 and 0 < battery.eta_d <= 1
    ix = np.arange(n)
    # -q+c-d <= -net; surplus is reconstructed after the solve.
    au = coo_matrix((np.tile([-1.0, 1.0, -1.0], (n, 1)).ravel(),
                    (np.repeat(ix, 3), np.column_stack([ix, n+ix, 2*n+ix]).ravel())),
                   shape=(n, 4*n)).tocsr()
    er, ec, ev = [], [], []
    for k in range(n):
        er.extend([k, k, k])
        ec.extend([n+k, 2*n+k, 3*n+k])
        ev.extend([-battery.eta_c, 1/battery.eta_d, 1])
        if k:
            er.append(k); ec.append(3*n+k-1); ev.append(-1)
    ae = coo_matrix((ev, (er, ec)), shape=(n, 4*n)).tocsr()
    be = np.zeros(n); be[0] = initial
    objective = np.r_[price, np.zeros(3*n)]
    bounds = ([(0, None)]*n + [(0, battery.max_kwh)]*(2*n)
              + [(battery.minimum, battery.maximum)]*n)
    if terminal is not None:
        bounds[-1] = (terminal, terminal)
    result = linprog(objective, A_ub=au, b_ub=-net, A_eq=ae, b_eq=be,
                     bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(result.message)
    q, c, d, state = np.split(result.x, 4)
    # Eliminate simultaneous cycling while exactly preserving stored energy.
    # Positive surplus is permitted; therefore the transformation is feasible.
    eps = np.minimum(c, d/(battery.eta_c*battery.eta_d))
    c = c-eps
    d = d-eps*battery.eta_c*battery.eta_d
    surplus = q+d-c-net
    # Any newly available surplus with positive purchases can reduce purchases.
    reduction = np.minimum(q, np.maximum(surplus, 0))
    q = q-reduction
    dual = float((-net) @ result.ineqlin.marginals + be @ result.eqlin.marginals)
    for j, (lower, upper) in enumerate(bounds):
        if lower is not None:
            dual += lower * result.lower.marginals[j]
        if upper is not None:
            dual += upper * result.upper.marginals[j]
    return dict(plan=q, charge=c, discharge=d, soc=np.r_[initial, state],
                unused=q+d-c-net, cost=float(price@q),
                solver_cost=float(result.fun), dual_cost=dual,
                solver_status=int(result.status),
                dual_ineq=result.ineqlin.marginals, dual_eq=result.eqlin.marginals,
                dual_lower=result.lower.marginals, dual_upper=result.upper.marginals)
