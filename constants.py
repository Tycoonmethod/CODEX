# Constants for phase weights and penalties
PHASE_WEIGHTS = {
    'UAT': 0.10,
    'Migration': 0.30,
    'E2E': 0.20,
    'Training': 0.15,
    'PRO': 0.15,
    'Hypercare': 0.10
}

# Risk impact factors for each phase (higher = more sensitive to risk)
RISK_IMPACT_FACTORS = {
    'Migration': 0.40,  # Most sensitive
    'PRO': 0.35,       # Second most sensitive
    'UAT': 0.25,       # Medium-high sensitivity
    'E2E': 0.20,       # Medium sensitivity
    'Training': 0.20,  # Medium sensitivity
    'Hypercare': 0.15  # Least sensitive
}

# Delay impact factors for each phase
DELAY_IMPACT_FACTORS = {
    'Migration': 0.40,  # 0.40% per day (most critical)
    'E2E': 0.25,       # 0.25% per day
    'UAT': 0.20,       # 0.20% per day
    'PRO': 0.15,       # 0.15% per day
    'Training': 0.15,  # 0.15% per day
    'Hypercare': 0.10  # 0.10% per day (least critical for go-live)
}

# Health Score weights
HEALTH_WEIGHTS = {
    'quality': 0.70,    # Quality is the dominant factor
    'time': 0.15,       # Time/schedule less impactful
    'budget': 0.10,     # Budget and risks have minimal impact
    'risk': 0.05        # Total 100%
}

# Health Score thresholds
HEALTH_THRESHOLDS = {
    'critical': 70,     # Below this is critical (red)
    'warning': 85,      # Below this is warning (yellow)
                       # Above this is healthy (green)
}

PHASE_SEQUENCE = ['UAT', 'Migration', 'E2E', ['PRO', 'Training'], 'Hypercare']
PENALTY_FACTOR = 0.01  # 1% quality degradation per day of delay (reduced from 2%)
QUALITY_SCALE = 0.90  # Maximum achievable quality (90% is considered excellent) 