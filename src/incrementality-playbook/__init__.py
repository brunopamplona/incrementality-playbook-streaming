from .config import ChannelSpec, SimConfig, default_config
from .simulator import Intervention, run_simulation, channel_response
from .truth import true_channel_summary
from .plans import plan_economics
from .calibration import calibrated_config, monthly_budget, scale_config, with_monthly_budget
from .optimize import optimal_split
from .economics import true_channel_plan_summary, channel_value_roi, plan_ltv_cac
from .attribution import last_click_attribution, naive_panel_regression, compare_to_truth, platform_summary

__all__ = [
    "ChannelSpec", "SimConfig", "default_config", "Intervention",
    "run_simulation", "channel_response", "true_channel_summary", "plan_economics", "optimal_split", "calibrated_config", "scale_config", "monthly_budget", "with_monthly_budget", "true_channel_plan_summary", "channel_value_roi", "plan_ltv_cac",
    "last_click_attribution", "naive_panel_regression", "compare_to_truth", "platform_summary",
]
