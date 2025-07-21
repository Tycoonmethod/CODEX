from constants import DELAY_IMPACT_FACTORS

def get_delay_impact_factor(phase):
    """Get the delay impact factor for a specific phase"""
    return DELAY_IMPACT_FACTORS.get(phase, 0.20)  # Default to 0.20 if phase not found 