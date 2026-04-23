"""
NOLHC training / output column order (nolhc_ml_engine_spec.md §5–6).

Feature columns use 0-based Excel indices (col 0 = run index, skipped).
The explicit list includes 35 parameters (including 4 Cherbourg shift-volume columns).
"""

from __future__ import annotations

import re
from typing import Dict, List

# 0-based column indices in ExpValues (row 4+ = data), excluding run index (0).
EXP_VALUES_FEATURE_COL_INDICES: List[int] = [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
]

TRAINING_COLUMN_ORDER: List[str] = [
    "NA_Im",
    "NA_Ex",
    "A_Im",
    "A_Ex",
    "Shift_NA_Im_LB_to_Cher",
    "NA_Im_LB",
    "NA_Im_DR",
    "Shift_NA_Ex_LB_to_Cher",
    "NA_Ex_LB",
    "NA_Ex_DR",
    "Shift_A_Im_LB_to_Cher",
    "A_Im_LB",
    "A_Im_DR",
    "Shift_A_Ex_LB_to_Cher",
    "A_Ex_LB",
    "A_Ex_DR",
    "VCap_Dub_Hey",
    "VCap_Dub_Holy",
    "VCap_Dub_Liv",
    "VCap_Ross_Fish",
    "VCap_Ross_Pem",
    "ChkTime_Doc",
    "ChkTime_Phy",
    "NumCusShed_D",
    "NumDAFM_D",
    "NumCusShed_R",
    "NumDAFM_R",
    "Pct_NA_OB_Green",
    "Pct_NA_OB_Red",
    "Pct_A_OB_Red",
    "Pct_NA_IB_Green",
    "Pct_NA_IB_Red",
    "Pct_A_IB_Red",
    "Pct_IB_PreBoard",
    "Pct_OB_PreBoard",
]

assert len(TRAINING_COLUMN_ORDER) == len(EXP_VALUES_FEATURE_COL_INDICES)

OUTPUT_COLUMN_ORDER: List[str] = [
    "TT_OB_Agri",
    "WT_OB_A_GB-Dub",
    "WT_OB_A_GB-Ross",
    "TT_IB_Agri",
    "WT_IB_A_Dub",
    "WT_IB_A_Ross",
    "WT_IB_NA_Dub",
    "WT_OB_NA_GB-Dub",
    "WT_IB_NA_Ross",
    "WT_OB_NA_GB-Ross",
    "TT_OB_LB",
    "WT_OB_LB",
    "TT_IB_LB",
    "WT_IB_LB",
    "TT_OB_DR",
    "TT_IB_DR",
    "Uti_Cus_D",
    "Uti_DAFM_D",
    "Uti_Cus_R",
    "Uti_DAFM_R",
]

assert len(OUTPUT_COLUMN_ORDER) == 20


def col_to_slug(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:80]


def output_unit(raw_key: str) -> str:
    if raw_key.startswith("Uti_"):
        return "fraction"
    return "hours"


INPUT_DESCRIPTIONS: Dict[str, str] = {
    "NA_Im": "Non-agri inbound volume (GB→IRE), tonnes",
    "NA_Ex": "Non-agri outbound volume (IRE→GB), tonnes",
    "A_Im": "Agri inbound volume (GB→IRE), tonnes",
    "A_Ex": "Agri outbound volume (IRE→GB), tonnes",
    "Shift_NA_Im_LB_to_Cher": "Shift volume non-agri inbound (LB→Cherbourg), tonnes",
    "NA_Im_LB": "Non-agri inbound via Landbridge, tonnes",
    "NA_Im_DR": "Non-agri inbound via Direct route, tonnes",
    "Shift_NA_Ex_LB_to_Cher": "Shift volume non-agri outbound (LB→Cherbourg), tonnes",
    "NA_Ex_LB": "Non-agri outbound via Landbridge, tonnes",
    "NA_Ex_DR": "Non-agri outbound via Direct route, tonnes",
    "Shift_A_Im_LB_to_Cher": "Shift volume agri inbound (LB→Cherbourg), tonnes",
    "A_Im_LB": "Agri inbound via Landbridge, tonnes",
    "A_Im_DR": "Agri inbound via Direct route, tonnes",
    "Shift_A_Ex_LB_to_Cher": "Shift volume agri outbound (LB→Cherbourg), tonnes",
    "A_Ex_LB": "Agri outbound via Landbridge, tonnes",
    "A_Ex_DR": "Agri outbound via Direct route, tonnes",
    "VCap_Dub_Hey": "Vessel capacity Dublin→Heysham (trailers)",
    "VCap_Dub_Holy": "Vessel capacity Dublin→Holyhead (trailers)",
    "VCap_Dub_Liv": "Vessel capacity Dublin→Liverpool (trailers)",
    "VCap_Ross_Fish": "Vessel capacity Rosslare→Fishguard (trailers)",
    "VCap_Ross_Pem": "Vessel capacity Rosslare→Pembroke (trailers)",
    "ChkTime_Doc": "Documentary check time (minutes)",
    "ChkTime_Phy": "Physical inspection time (minutes)",
    "NumCusShed_D": "Custom sheds at Dublin (count)",
    "NumDAFM_D": "DAFM bays at Dublin (count)",
    "NumCusShed_R": "Custom sheds at Rosslare (count)",
    "NumDAFM_R": "DAFM bays at Rosslare (count)",
    "Pct_NA_OB_Green": "Fraction non-agri outbound → green route",
    "Pct_NA_OB_Red": "Fraction non-agri outbound → red route",
    "Pct_A_OB_Red": "Fraction agri outbound → red route",
    "Pct_NA_IB_Green": "Fraction non-agri inbound → green route",
    "Pct_NA_IB_Red": "Fraction non-agri inbound → red route",
    "Pct_A_IB_Red": "Fraction agri inbound → red route",
    "Pct_IB_PreBoard": "Fraction inbound stopped (pre-boarding)",
    "Pct_OB_PreBoard": "Fraction outbound stopped (pre-boarding)",
}

OUTPUT_DESCRIPTIONS: Dict[str, str] = {
    "TT_OB_Agri": "Transport time, agri outbound (IRE→GB)",
    "WT_OB_A_GB-Dub": "Waiting time, agri outbound, Dublin GB-side",
    "WT_OB_A_GB-Ross": "Waiting time, agri outbound, Rosslare GB-side",
    "TT_IB_Agri": "Transport time, agri inbound (GB→IRE)",
    "WT_IB_A_Dub": "Waiting time, agri inbound, Dublin IRE-side",
    "WT_IB_A_Ross": "Waiting time, agri inbound, Rosslare IRE-side",
    "WT_IB_NA_Dub": "Waiting time, non-agri inbound, Dublin",
    "WT_OB_NA_GB-Dub": "Waiting time, non-agri outbound, Dublin GB-side",
    "WT_IB_NA_Ross": "Waiting time, non-agri inbound, Rosslare",
    "WT_OB_NA_GB-Ross": "Waiting time, non-agri outbound, Rosslare GB-side",
    "TT_OB_LB": "Transport time, Landbridge outbound",
    "WT_OB_LB": "Waiting time, Landbridge outbound",
    "TT_IB_LB": "Transport time, Landbridge inbound",
    "WT_IB_LB": "Waiting time, Landbridge inbound",
    "TT_OB_DR": "Transport time, Direct route outbound",
    "TT_IB_DR": "Transport time, Direct route inbound",
    "Uti_Cus_D": "Customs utilisation, Dublin",
    "Uti_DAFM_D": "DAFM utilisation, Dublin",
    "Uti_Cus_R": "Customs utilisation, Rosslare",
    "Uti_DAFM_R": "DAFM utilisation, Rosslare",
}


def input_unit(name: str) -> str:
    if name.startswith("Pct_"):
        return "fraction"
    if name.startswith("VCap_"):
        return "trailers"
    if name.startswith("ChkTime_"):
        return "minutes"
    if name.startswith("Num"):
        return "count"
    return "tonnes"
