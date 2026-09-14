"""Pair-aware guide assignment for dual-guide (scaffold A + scaffold C) libraries.

Selected with ``guides.assignment_mode: dual_guide_pair``. The single-guide
dominance rule (``assignment_mode: single_guide``) is untouched and remains the
default; this module adds a second matrix-based assignment path.

Rule
----
For each of the two scaffold classes (default ``A`` and ``C``) the strongest
guide in the cell is selected *within that class* and has to pass the same
gate the single-guide rule uses (``min_umi``, ``dominance_ratio`` against the
runner-up of the same class, optional ``max_second_umi``). Each class slot is
therefore ``resolved``, ``multiple`` (several strong guides in the class) or
``none`` (no guide of that class at ``min_umi``). The pair (A, C) is then
interpreted:

* both slots resolved and an explicit pair map is available: the pair is valid
  only if both guides share the designed ``pair_id`` (status
  ``designed_pair`` / ``designed_ntc_pair`` / ``designed_target_ntc``),
  otherwise ``invalid_pair``;
* both slots resolved without an explicit pair map (provisional same-target
  rule): same target -> ``same_target_pair``; both NTC -> ``ntc_pair``;
  targeting + NTC -> ``target_ntc_provisional`` (assigned to the target) or
  ``target_ntc_unconfirmed`` (ambiguous) depending on
  ``guides.ntc_partner_policy``; two different targets -> ``dual_target``
  (never collapsed onto one target; kept out of the targeting class);
* one slot resolved and the other empty -> ``incomplete_<class>_only``;
* any slot with several strong guides -> ``ambiguous_<class>_slot`` /
  ``ambiguous_both_slots``;
* no guide reaching ``min_umi`` -> ``below_min_umi`` (ambiguous) or
  ``no_guide`` (unassigned) when the cell has no guide UMIs at all.

The downstream contract of :mod:`perturbseq_pipeline.guides` is preserved:
``perturbation_class`` keeps its four values, ``target_gene`` carries the pair
target, ``guide_id`` carries ``"<A guide>|<C guide>"`` for assigned pairs. The
pair-level detail is written to additional ``obs`` columns (see ``OBS_*``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse

from .config import Config, GuideConfig
from .guides import (
    CLASS_AMBIGUOUS,
    CLASS_NTC,
    CLASS_TARGETING,
    CLASS_UNASSIGNED,
    OBS_CLASS,
    OBS_GUIDE,
    OBS_NDETECTED,
    OBS_SECOND,
    OBS_TARGET,
    OBS_TOP,
    OBS_TOTAL,
    _csr_top_two_numba,
    _csr_top_two_python,
    _log_assignment,
    is_non_targeting,
    resolve_guide_targets,
)

logger = logging.getLogger(__name__)

MODE_SINGLE = "single_guide"
MODE_DUAL = "dual_guide_pair"
ASSIGNMENT_MODES = (MODE_SINGLE, MODE_DUAL)

NTC_PARTNER_POLICIES = ("ambiguous", "provisional_target")

OBS_MODE = "guide_assignment_mode"
OBS_PAIR_ID = "pair_id"
OBS_PAIR = "pair_assignment"
OBS_PAIR_STATUS = "pair_assignment_status"
OBS_PAIR_PROVISIONAL = "pair_assignment_provisional"

# Per-class column templates ({c} = scaffold class name, e.g. A / C)
OBS_SLOT_ID = "guide_{c}_id"
OBS_SLOT_TARGET = "guide_{c}_target"
OBS_SLOT_COUNT = "guide_{c}_count"
OBS_SLOT_SECOND = "guide_{c}_second_count"
OBS_SLOT_NSTRONG = "n_strong_guides_{c}"
OBS_SLOT_STATUS = "guide_{c}_slot_status"

SLOT_RESOLVED = "resolved"
SLOT_MULTIPLE = "multiple"
SLOT_NONE = "none"

STATUS_NO_GUIDE = "no_guide"
STATUS_BELOW_MIN_UMI = "below_min_umi"
STATUS_INCOMPLETE = "incomplete_{c}_only"
STATUS_AMBIGUOUS_SLOT = "ambiguous_{c}_slot"
STATUS_AMBIGUOUS_BOTH = "ambiguous_both_slots"
STATUS_SAME_TARGET = "same_target_pair"
STATUS_NTC_PAIR = "ntc_pair"
STATUS_TARGET_NTC_PROVISIONAL = "target_ntc_provisional"
STATUS_TARGET_NTC_UNCONFIRMED = "target_ntc_unconfirmed"
STATUS_DUAL_TARGET = "dual_target"
STATUS_DESIGNED_PAIR = "designed_pair"
STATUS_DESIGNED_NTC_PAIR = "designed_ntc_pair"
STATUS_DESIGNED_TARGET_NTC = "designed_target_ntc"
STATUS_DESIGNED_DUAL_TARGET = "designed_dual_target"
STATUS_INVALID_PAIR = "invalid_pair"

PAIR_STATUS_ORDER = [
    STATUS_SAME_TARGET, STATUS_DESIGNED_PAIR, STATUS_NTC_PAIR, STATUS_DESIGNED_NTC_PAIR,
    STATUS_TARGET_NTC_PROVISIONAL, STATUS_DESIGNED_TARGET_NTC, STATUS_TARGET_NTC_UNCONFIRMED,
    STATUS_DUAL_TARGET, STATUS_DESIGNED_DUAL_TARGET, STATUS_INVALID_PAIR,
    "incomplete_A_only", "incomplete_C_only", "ambiguous_A_slot", "ambiguous_C_slot",
    STATUS_AMBIGUOUS_BOTH, STATUS_BELOW_MIN_UMI, STATUS_NO_GUIDE,
]

PAIR_SEP = "|"


# ---------------------------------------------------------------------------
# Pair map
# ---------------------------------------------------------------------------


def load_pair_map(path: str | Path, gcfg: GuideConfig) -> pd.DataFrame:
    """Read the guide pair map (CSV/TSV) indexed by ``guide_id``.

    Recognised columns: ``guide_id`` (required), ``gcfg.pair_id_column``
    (optional; empty/NaN = no designed pair), ``gcfg.scaffold_column``
    (optional), ``target_gene_name`` (optional), ``is_non_targeting`` (optional).
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"guides.pair_map_file not found: {path}")
    df = pd.read_csv(path, sep="\t" if path.suffix.lower() in (".tsv", ".txt") else ",", dtype=str, keep_default_na=False)
    if "guide_id" not in df.columns:
        raise ValueError(f"pair map {path} has no 'guide_id' column; columns: {list(df.columns)}")
    df["guide_id"] = df["guide_id"].astype(str).str.strip()
    if df["guide_id"].duplicated().any():
        raise ValueError(f"pair map {path} lists guide ids more than once")
    df = df.set_index("guide_id")
    pcol = gcfg.pair_id_column
    if pcol in df.columns:
        df[pcol] = df[pcol].astype(str).str.strip().replace({"nan": "", "NaN": "", "None": ""})
    else:
        df[pcol] = ""
    return df


def pair_map_is_explicit(pair_map: Optional[pd.DataFrame], gcfg: GuideConfig) -> bool:
    return pair_map is not None and bool((pair_map[gcfg.pair_id_column] != "").any())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _top_two(X: sparse.csr_matrix) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(top_idx, top_val, second_val, row_total) over a CSR matrix; zeros for empty rows."""
    X = sparse.csr_matrix(X)
    if X.shape[1] == 0:
        n = X.shape[0]
        return np.zeros(n, dtype=np.int64), np.zeros(n), np.zeros(n), np.zeros(n)
    res = _csr_top_two_numba(X)
    if res is None:
        res = _csr_top_two_python(X)
    top_idx, top_val, second_val, total = res
    return (np.asarray(top_idx, dtype=np.int64), np.asarray(top_val, dtype=float),
            np.asarray(second_val, dtype=float), np.asarray(total, dtype=float))


def resolve_guide_scaffolds(guides: ad.AnnData, gcfg: GuideConfig, pair_map: Optional[pd.DataFrame]) -> np.ndarray:
    """Scaffold class per guide from ``guides.var[gcfg.scaffold_column]`` or the pair map."""
    col = gcfg.scaffold_column
    scaf: Optional[pd.Series] = None
    if col in guides.var.columns:
        scaf = guides.var[col].astype(str).str.strip()
    elif pair_map is not None and col in pair_map.columns:
        scaf = pd.Series(guides.var_names.astype(str), index=guides.var_names).map(pair_map[col].astype(str)).fillna("unknown")
    if scaf is None:
        raise ValueError(
            f"dual_guide_pair assignment needs a scaffold class per guide: neither guides.var[{col!r}] "
            f"nor a {col!r} column in guides.pair_map_file is available (var columns: {list(guides.var.columns)})"
        )
    out = scaf.replace({"": "unknown", "nan": "unknown", "None": "unknown"}).to_numpy().astype(str)
    return out


def _slot_gate(top_val: np.ndarray, second_val: np.ndarray, gcfg: GuideConfig) -> Tuple[np.ndarray, np.ndarray]:
    """Return (resolved, multiple) boolean masks for one scaffold slot."""
    min_umi = max(int(gcfg.min_umi), 1)
    strong = top_val >= min_umi
    resolved = strong & (top_val > float(gcfg.dominance_ratio) * second_val)
    if gcfg.max_second_umi is not None and gcfg.max_second_umi >= 0:
        resolved &= second_val <= gcfg.max_second_umi
    multiple = strong & ~resolved
    return resolved, multiple


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def assign_guide_pairs(expr: ad.AnnData, guides: ad.AnnData, cfg: Config) -> ad.AnnData:
    """Dual-guide pair-aware assignment; writes into ``expr.obs`` and returns ``expr``."""
    gcfg = cfg.guides
    if gcfg.ntc_partner_policy not in NTC_PARTNER_POLICIES:
        raise ValueError(f"guides.ntc_partner_policy must be one of {NTC_PARTNER_POLICIES}")
    classes = [str(c) for c in gcfg.scaffold_classes]
    if len(classes) != 2:
        raise ValueError("guides.scaffold_classes must name exactly two scaffold classes for dual_guide_pair mode")
    cA, cC = classes

    if guides.n_obs == expr.n_obs and guides.obs_names.equals(expr.obs_names):
        aligned = guides
    else:
        aligned = guides[expr.obs_names].copy()
    X = aligned.layers["counts"] if "counts" in aligned.layers else aligned.X
    X = sparse.csr_matrix(X)
    n = X.shape[0]

    pair_map = load_pair_map(gcfg.pair_map_file, gcfg) if gcfg.pair_map_file else None
    explicit = pair_map_is_explicit(pair_map, gcfg)

    guide_ids = aligned.var_names.to_numpy().astype(str)
    guide_targets = resolve_guide_targets(aligned, gcfg)
    guide_ntc = is_non_targeting(guide_targets, gcfg)
    if "is_non_targeting" in aligned.var.columns:
        guide_ntc = guide_ntc | aligned.var["is_non_targeting"].astype(str).str.lower().isin(["true", "1"]).to_numpy()
    guide_scaf = resolve_guide_scaffolds(aligned, gcfg, pair_map)
    guide_pair_id = np.array([""] * len(guide_ids), dtype=object)
    if pair_map is not None:
        m = pd.Series(guide_ids).map(pair_map[gcfg.pair_id_column]).fillna("")
        guide_pair_id = m.to_numpy().astype(object)
    known = np.isin(guide_scaf, classes)
    if not known.any():
        raise ValueError(f"no guide carries a scaffold class in {classes}; scaffold values: {np.unique(guide_scaf).tolist()}")
    logger.info(
        "Dual-guide assignment: %d guides (%s), %d without a usable scaffold class; pair map: %s",
        len(guide_ids), ", ".join(f"{c}={int((guide_scaf == c).sum())}" for c in classes), int((~known).sum()),
        ("explicit (%s)" % gcfg.pair_map_file) if explicit else ("provisional same-target rule" + (f" (pair map {gcfg.pair_map_file} has no pair ids)" if pair_map is not None else "")),
    )

    # Global diagnostics (identical to single-guide mode)
    g_top_idx, g_top, g_second, total = _top_two(X)
    detected = np.asarray((X > gcfg.detection_threshold).sum(axis=1)).ravel().astype(np.int32)
    min_umi = max(int(gcfg.min_umi), 1)

    slot: Dict[str, Dict[str, np.ndarray]] = {}
    for c in classes:
        cols = np.flatnonzero(guide_scaf == c)
        sub = X[:, cols] if len(cols) else sparse.csr_matrix((n, 0))
        t_idx, t_val, s_val, _ = _top_two(sub)
        resolved, multiple = _slot_gate(t_val, s_val, gcfg)
        n_strong = np.asarray((sub >= min_umi).sum(axis=1)).ravel().astype(np.int32) if len(cols) else np.zeros(n, dtype=np.int32)
        gidx = cols[t_idx] if len(cols) else np.zeros(n, dtype=np.int64)
        slot[c] = dict(idx=gidx, val=t_val, second=s_val, resolved=resolved, multiple=multiple,
                       none=~(resolved | multiple), n_strong=n_strong)

    A, C = slot[cA], slot[cC]
    unl, amb = gcfg.unassigned_label, gcfg.ambiguous_label
    status = np.full(n, "", dtype=object)
    klass = np.full(n, CLASS_UNASSIGNED, dtype=object)
    target_call = np.full(n, unl, dtype=object)
    guide_call = np.full(n, unl, dtype=object)
    pair_call = np.full(n, unl, dtype=object)
    pair_id_call = np.full(n, "", dtype=object)
    provisional = np.zeros(n, dtype=bool)

    has_counts = total > 0
    no_strong = A["none"] & C["none"]
    status[no_strong & ~has_counts] = STATUS_NO_GUIDE
    status[no_strong & has_counts] = STATUS_BELOW_MIN_UMI
    klass[no_strong & has_counts] = CLASS_AMBIGUOUS
    target_call[no_strong & has_counts] = amb
    guide_call[no_strong & has_counts] = amb
    pair_call[no_strong & has_counts] = amb

    both_mul = A["multiple"] & C["multiple"]
    a_mul = A["multiple"] & ~C["multiple"]
    c_mul = C["multiple"] & ~A["multiple"]
    status[both_mul] = STATUS_AMBIGUOUS_BOTH
    status[a_mul] = STATUS_AMBIGUOUS_SLOT.format(c=cA)
    status[c_mul] = STATUS_AMBIGUOUS_SLOT.format(c=cC)
    a_only = A["resolved"] & C["none"]
    c_only = C["resolved"] & A["none"]
    status[a_only] = STATUS_INCOMPLETE.format(c=cA)
    status[c_only] = STATUS_INCOMPLETE.format(c=cC)
    amb_mask = both_mul | a_mul | c_mul | a_only | c_only
    klass[amb_mask] = CLASS_AMBIGUOUS
    target_call[amb_mask] = amb
    guide_call[amb_mask] = amb
    pair_call[amb_mask] = amb

    both = A["resolved"] & C["resolved"]
    idx = np.flatnonzero(both)
    if idx.size:
        ai, ci = A["idx"][idx], C["idx"][idx]
        tA, tC = guide_targets[ai], guide_targets[ci]
        nA, nC = guide_ntc[ai], guide_ntc[ci]
        gA, gC = guide_ids[ai], guide_ids[ci]
        pair_label = np.char.add(np.char.add(gA.astype(str), PAIR_SEP), gC.astype(str))
        pair_id_call[idx] = pair_label
        st = np.full(idx.size, "", dtype=object)
        kl = np.full(idx.size, CLASS_AMBIGUOUS, dtype=object)
        tg = np.full(idx.size, amb, dtype=object)
        pc = np.full(idx.size, amb, dtype=object)
        prov = np.zeros(idx.size, dtype=bool)
        same = tA == tC
        ntc_pair = nA & nC
        one_ntc = nA ^ nC
        two_targets = ~same & ~nA & ~nC
        if explicit:
            pA, pC = guide_pair_id[ai].astype(str), guide_pair_id[ci].astype(str)
            designed = (pA != "") & (pA == pC)
            invalid = ~designed
            st[invalid] = STATUS_INVALID_PAIR
            d_ntc = designed & ntc_pair
            d_one = designed & one_ntc
            d_same = designed & same & ~nA
            d_two = designed & two_targets
            st[d_ntc] = STATUS_DESIGNED_NTC_PAIR
            kl[d_ntc] = CLASS_NTC
            tg[d_ntc] = gcfg.ntc_label
            pc[d_ntc] = gcfg.ntc_label
            st[d_one] = STATUS_DESIGNED_TARGET_NTC
            kl[d_one] = CLASS_TARGETING
            tg[d_one] = np.where(nA, tC, tA)[d_one]
            pc[d_one] = tg[d_one]
            st[d_same] = STATUS_DESIGNED_PAIR
            kl[d_same] = CLASS_TARGETING
            tg[d_same] = tA[d_same]
            pc[d_same] = tA[d_same]
            st[d_two] = STATUS_DESIGNED_DUAL_TARGET
            pc[d_two] = np.char.add(np.char.add(tA.astype(str), PAIR_SEP), tC.astype(str))[d_two]
            pair_id_call[idx[designed]] = pA[designed]
        else:
            prov[:] = True
            st[ntc_pair] = STATUS_NTC_PAIR
            kl[ntc_pair] = CLASS_NTC
            tg[ntc_pair] = gcfg.ntc_label
            pc[ntc_pair] = gcfg.ntc_label
            s_t = same & ~nA
            st[s_t] = STATUS_SAME_TARGET
            kl[s_t] = CLASS_TARGETING
            tg[s_t] = tA[s_t]
            pc[s_t] = tA[s_t]
            if gcfg.ntc_partner_policy == "provisional_target":
                st[one_ntc] = STATUS_TARGET_NTC_PROVISIONAL
                kl[one_ntc] = CLASS_TARGETING
                tg[one_ntc] = np.where(nA, tC, tA)[one_ntc]
                pc[one_ntc] = tg[one_ntc]
            else:
                st[one_ntc] = STATUS_TARGET_NTC_UNCONFIRMED
                pc[one_ntc] = np.where(nA, tC, tA)[one_ntc]
            st[two_targets] = STATUS_DUAL_TARGET
            pc[two_targets] = np.char.add(np.char.add(tA.astype(str), PAIR_SEP), tC.astype(str))[two_targets]
        status[idx] = st
        klass[idx] = kl
        target_call[idx] = tg
        pair_call[idx] = pc
        provisional[idx] = prov
        assigned_pair = np.isin(kl, [CLASS_TARGETING, CLASS_NTC])
        guide_call[idx[assigned_pair]] = pair_label[assigned_pair]
        guide_call[idx[~assigned_pair]] = amb

    assert (status != "").all(), "every cell must receive a pair assignment status"

    # ---- write obs ---------------------------------------------------------------
    expr.obs[OBS_TOP] = g_top
    expr.obs[OBS_SECOND] = g_second
    expr.obs[OBS_TOTAL] = total
    expr.obs[OBS_NDETECTED] = detected
    expr.obs[OBS_GUIDE] = pd.Categorical(guide_call.astype(str))
    expr.obs[OBS_TARGET] = pd.Categorical(target_call.astype(str))
    expr.obs[OBS_CLASS] = pd.Categorical(
        klass.astype(str), categories=[CLASS_TARGETING, CLASS_NTC, CLASS_AMBIGUOUS, CLASS_UNASSIGNED]
    )
    expr.obs[OBS_MODE] = pd.Categorical([MODE_DUAL] * n)
    for c in classes:
        s = slot[c]
        sid = np.where(s["resolved"], guide_ids[s["idx"]], np.where(s["multiple"], amb, unl)).astype(str)
        stg = np.where(s["resolved"], guide_targets[s["idx"]], np.where(s["multiple"], amb, unl)).astype(str)
        stg = np.where(s["resolved"] & guide_ntc[s["idx"]], gcfg.ntc_label, stg)
        expr.obs[OBS_SLOT_ID.format(c=c)] = pd.Categorical(sid)
        expr.obs[OBS_SLOT_TARGET.format(c=c)] = pd.Categorical(stg)
        expr.obs[OBS_SLOT_COUNT.format(c=c)] = s["val"]
        expr.obs[OBS_SLOT_SECOND.format(c=c)] = s["second"]
        expr.obs[OBS_SLOT_NSTRONG.format(c=c)] = s["n_strong"]
        expr.obs[OBS_SLOT_STATUS.format(c=c)] = pd.Categorical(
            np.where(s["resolved"], SLOT_RESOLVED, np.where(s["multiple"], SLOT_MULTIPLE, SLOT_NONE)).astype(str),
            categories=[SLOT_RESOLVED, SLOT_MULTIPLE, SLOT_NONE],
        )
    expr.obs[OBS_PAIR_ID] = pd.Categorical(pair_id_call.astype(str))
    expr.obs[OBS_PAIR] = pd.Categorical(pair_call.astype(str))
    expr.obs[OBS_PAIR_STATUS] = pd.Categorical(status.astype(str))
    expr.obs[OBS_PAIR_PROVISIONAL] = provisional
    expr.uns["guide_assignment"] = {
        "mode": MODE_DUAL,
        "scaffold_classes": classes,
        "pair_map_file": str(gcfg.pair_map_file) if gcfg.pair_map_file else "",
        "pair_map_explicit": bool(explicit),
        "ntc_partner_policy": gcfg.ntc_partner_policy,
        "min_umi": int(gcfg.min_umi),
        "dominance_ratio": float(gcfg.dominance_ratio),
        "max_second_umi": int(gcfg.max_second_umi),
        "rule": (
            "strongest guide per scaffold class must reach min_umi and exceed dominance_ratio x the class runner-up; "
            "valid pair = same designed pair_id (explicit map) or same target (provisional rule)"
        ),
    }

    # ---- guide metadata written back ------------------------------------------------
    # var metadata is per guide, so write it to the caller's object as well when the
    # aligned view is a cell-subset copy (otherwise uns['guide_target_genes'] is lost on write)
    for obj in ({id(aligned): aligned, id(guides): guides}.values()):
        obj.var["target_gene"] = guide_targets
        obj.var["is_non_targeting"] = guide_ntc
        obj.var[gcfg.scaffold_column] = guide_scaf
        obj.var[gcfg.pair_id_column] = guide_pair_id.astype(str)
    aligned.obs[OBS_GUIDE] = expr.obs[OBS_GUIDE].to_numpy()
    aligned.obs[OBS_TARGET] = expr.obs[OBS_TARGET].to_numpy()

    counts = pd.Series(status).value_counts()
    logger.info("Pair assignment status: %s", ", ".join(f"{k}={int(v)}" for k, v in counts.items()))
    _log_assignment(expr, cfg)
    return expr


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def pair_assignment_summary(expr: ad.AnnData) -> Optional[pd.DataFrame]:
    """Cells per pair-assignment status (with class and provisional flag)."""
    if OBS_PAIR_STATUS not in expr.obs.columns:
        return None
    df = (expr.obs.groupby([OBS_PAIR_STATUS, OBS_CLASS, OBS_PAIR_PROVISIONAL], observed=True)
          .size().reset_index(name="n_cells"))
    df["pct_of_cells"] = 100.0 * df["n_cells"] / max(expr.n_obs, 1)
    order = {s: i for i, s in enumerate(PAIR_STATUS_ORDER)}
    df["_o"] = df[OBS_PAIR_STATUS].astype(str).map(lambda s: order.get(s, len(order)))
    return df.sort_values(["_o", OBS_CLASS]).drop(columns="_o").reset_index(drop=True)


def pair_assignment_per_lane(expr: ad.AnnData, lane_key: str = "lane_id") -> Optional[pd.DataFrame]:
    """Pair-assignment status counts per lane (wide) with a pooled row."""
    if OBS_PAIR_STATUS not in expr.obs.columns or lane_key not in expr.obs.columns:
        return None
    tab = pd.crosstab(expr.obs[lane_key].astype(str), expr.obs[OBS_PAIR_STATUS].astype(str))
    cols = [c for c in PAIR_STATUS_ORDER if c in tab.columns] + [c for c in tab.columns if c not in PAIR_STATUS_ORDER]
    tab = tab[cols]
    tab.loc["ALL"] = tab.sum(axis=0)
    tab.insert(0, "n_cells", tab.sum(axis=1))
    return tab.reset_index().rename(columns={lane_key: "lane_id"})
