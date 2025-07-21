import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from constants import (
    PHASE_WEIGHTS,
    RISK_IMPACT_FACTORS,
    DELAY_IMPACT_FACTORS,
    HEALTH_WEIGHTS,
    HEALTH_THRESHOLDS,
    PHASE_SEQUENCE,
    PENALTY_FACTOR,
    QUALITY_SCALE
)

def get_delay_impact_factor(phase):
    """Get the delay impact factor for a specific phase"""
    return DELAY_IMPACT_FACTORS.get(phase, 0.20)  # Default to 0.20 if phase not found

def calculate_health_score(quality, delay_days, budget_pct_used, sum_risks):
    """
    Calculate a unified health score for the project combining quality, schedule, budget and risks.
    
    Args:
        quality: Current quality score (0-100)
        delay_days: Total delay in days from baseline
        budget_pct_used: Percentage of budget used (100 = all budget used)
        sum_risks: Sum of all risk percentages (0-300 for 3 risk categories)
    
    Returns:
        health_score: A score from 0-100 indicating overall project health
    """
    # Quality is already in percentage (0-100)
    q_norm = min(1.0, quality / 100)
    
    # Normalize time (more gradual degradation - takes 90 days to reach 0)
    t_norm = max(0.0, 1.0 - (delay_days / 90))
    
    # Normalize budget (more lenient - allows up to 100% over budget)
    b_norm = max(0.0, 1.0 - (budget_pct_used - 100) / 100) if budget_pct_used > 100 else 1.0
    
    # Normalize risks (more lenient - 300 is maximum sum of all risks)
    r_norm = max(0.0, 1.0 - (sum_risks / 300))
    
    # Calculate weighted score with quality as dominant factor
    score = (
        HEALTH_WEIGHTS['quality'] * q_norm +
        HEALTH_WEIGHTS['time'] * t_norm +
        HEALTH_WEIGHTS['budget'] * b_norm +
        HEALTH_WEIGHTS['risk'] * r_norm
    )
    
    # Convert to 0-100 scale
    return max(0.0, min(100.0, score * 100))

def calculate_phase_completion(current_date, start_date, end_date):
    """Calculate completion percentage for a phase on a given date."""
    if current_date < start_date:
        return 0.0
    if current_date >= end_date:
        return 1.0
    
    total_days = (end_date - start_date).days
    elapsed_days = (current_date - start_date).days
    return min(1.0, max(0.0, elapsed_days / total_days))

def calculate_phase_health(delay_days, predecessor_health, phase, execution_risk=0, accumulated_delays=None):
    """
    Calculate health factor based on delays, predecessor health, execution risk and accumulated delays.
    
    Args:
        delay_days: Number of days delayed from baseline
        predecessor_health: Health factor from predecessor phase (0-1)
        phase: Name of the phase being calculated
        execution_risk: Risk percentage for this phase (0-100)
        accumulated_delays: Dict with accumulated delays from previous phases
    """
    if accumulated_delays is None:
        accumulated_delays = {}
    
    # Calculate direct delay impact using phase-specific factor
    direct_delay_impact = delay_days * (get_delay_impact_factor(phase) / 100)
    
    # Calculate accumulated delay impact from previous phases
    accumulated_impact = 0
    for prev_phase, prev_delay in accumulated_delays.items():
        if prev_phase != phase:  # Don't count own delay twice
            impact_factor = get_delay_impact_factor(prev_phase)
            accumulated_impact += prev_delay * (impact_factor / 100)
    
    # Calculate risk impact using a progressive curve
    risk_factor = execution_risk / 100
    risk_impact = risk_factor * risk_factor  # Quadratic scaling for more sensitivity
    
    # Get the phase-specific risk impact factor
    phase_risk_factor = RISK_IMPACT_FACTORS.get(phase, 0.20)
    
    # Calculate total health degradation with all impacts
    total_impact = direct_delay_impact + accumulated_impact + (risk_impact * phase_risk_factor)
    health = predecessor_health * (1.0 - total_impact)
    
    return max(0.0, min(1.0, health))

def calculate_phase_quality(completion_pct, health_pct, phase_weight):
    """Calculate quality contribution for a phase considering completion and health."""
    effective_completion = (completion_pct / 100) * (health_pct / 100)
    return effective_completion * phase_weight * 100

def calculate_project_timeline(scenario_params, baseline_params, risk_params=None):
    """
    Calculate project timeline with cascading phase effects and accumulated delays.
    
    Args:
        scenario_params: Dict with actual start/end dates for each phase
        baseline_params: Dict with baseline start/end dates for each phase
        risk_params: Dict with execution risk percentage for each phase (0-100)
    
    Returns:
        DataFrame with daily quality metrics for each phase and overall project
    """
    # Initialize risk parameters if not provided
    if risk_params is None:
        risk_params = {phase: 0 for phase in PHASE_WEIGHTS.keys()}
        
    # Initialize accumulated delays tracking
    accumulated_delays = {}
    
    # Find project date range
    all_dates = []
    for params in [scenario_params, baseline_params]:
        for phase in PHASE_WEIGHTS.keys():
            all_dates.extend([params[phase]['start'], params[phase]['end']])
    
    start_date = min(all_dates)
    end_date = max(all_dates)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Initialize results DataFrame with proper dtypes
    columns = []
    for phase in PHASE_WEIGHTS.keys():
        columns.extend([
            f'{phase}_completion',
            f'{phase}_health',
            f'{phase}_effective',
            f'{phase}_quality_loss'
        ])
    columns.append('total_quality')
    
    # Initialize with zeros and proper float64 dtype
    results = pd.DataFrame(
        0.0,  # Initialize with float values directly
        index=date_range,
        columns=columns,
        dtype='float64'  # Explicitly set dtype
    )
    
    # Calculate metrics for each day
    previous_health = {'UAT': 1.0}
    
    for current_date in date_range:
        total_quality = 0.0
        
        # Process phases in sequence
        for phase_item in PHASE_SEQUENCE:
            if isinstance(phase_item, list):
                # Parallel phases (PRO & Training)
                phases = phase_item
            else:
                phases = [phase_item]
                
            for phase in phases:
                # Get actual and baseline dates
                actual_start = scenario_params[phase]['start']
                actual_end = scenario_params[phase]['end']
                baseline_end = baseline_params[phase]['end']
                
                # Calculate completion percentage
                completion = calculate_phase_completion(
                    current_date, actual_start, actual_end
                )
                
                # Calculate health based on delays, predecessor and risk
                delay_days = max(0, (actual_end - baseline_end).days)
                predecessor = 'UAT' if phase == 'UAT' else PHASE_SEQUENCE[
                    PHASE_SEQUENCE.index('UAT' if phase == 'Migration' else 
                    'Migration' if phase == 'E2E' else
                    'E2E' if phase in ['PRO', 'Training'] else
                    'E2E')  # For Hypercare, use E2E as main predecessor
                ]
                
                # Update accumulated delays for this phase
                if delay_days > 0:
                    accumulated_delays[phase] = delay_days
                
                health = calculate_phase_health(
                    delay_days,
                    previous_health.get(predecessor, 1.0),
                    phase,
                    risk_params[phase],
                    accumulated_delays
                )
                previous_health[phase] = health
                
                # Calculate effective completion and quality
                completion_pct = completion * 100
                health_pct = health * 100
                effective_pct = completion_pct * (health_pct / 100)
                
                # Store phase metrics
                results.loc[current_date, f'{phase}_completion'] = completion_pct
                results.loc[current_date, f'{phase}_health'] = health_pct
                results.loc[current_date, f'{phase}_effective'] = effective_pct
                
                # Calculate quality contribution
                phase_quality = calculate_phase_quality(completion_pct, health_pct, PHASE_WEIGHTS[phase])
                quality_loss = (completion_pct * PHASE_WEIGHTS[phase]) - phase_quality
                
                results.loc[current_date, f'{phase}_quality_loss'] = quality_loss
                
                if completion > 0:
                    total_quality += phase_quality
        
        # Apply quality scale to total quality
        results.loc[current_date, 'total_quality'] = total_quality * QUALITY_SCALE
    
    return results

def get_main_risk(timeline_df):
    """
    Analyze the timeline DataFrame and identify the main risk factor affecting project quality.
    
    Args:
        timeline_df: DataFrame with project timeline data including phase health and completion metrics
    
    Returns:
        str: Description of the main risk factor identified
    """
    # Get the latest data point
    latest_data = timeline_df.iloc[-1]
    
    # Analyze each phase's health
    phase_health = {}
    for phase in PHASE_WEIGHTS.keys():
        health_col = f'{phase}_health'
        if health_col in latest_data:
            health_score = latest_data[health_col] * 100
            phase_health[phase] = health_score
    
    # Find the phase with lowest health
    worst_phase = min(phase_health.items(), key=lambda x: x[1])
    phase_name, health_value = worst_phase
    
    # Determine severity level
    if health_value < HEALTH_THRESHOLDS['critical']:
        severity = "crítico"
    elif health_value < HEALTH_THRESHOLDS['warning']:
        severity = "moderado"
    else:
        severity = "leve"
    
    # Calculate delays
    completion_col = f'{phase_name}_completion'
    if completion_col in latest_data and latest_data[completion_col] < 1.0:
        return f"Riesgo {severity} en {phase_name} (salud {health_value:.1f}%) - Fase en progreso"
    else:
        return f"Riesgo {severity} en {phase_name} (salud {health_value:.1f}%)" 

def get_timeline_data():
    """
    Get the current timeline data for the project.
    This is a simplified version that returns sample data.
    In a real implementation, this would fetch data from a database or project management system.
    
    Returns:
        DataFrame: Timeline data with health scores, quality metrics, and completion status
    """
    # Create sample dates for each phase
    start_date = datetime.now()
    phase_data = {
        'UAT': {'start': start_date, 'end': start_date + timedelta(days=15)},
        'Migration': {'start': start_date + timedelta(days=15), 'end': start_date + timedelta(days=30)},
        'E2E': {'start': start_date + timedelta(days=30), 'end': start_date + timedelta(days=45)},
        'Training': {'start': start_date + timedelta(days=45), 'end': start_date + timedelta(days=60)},
        'PRO': {'start': start_date + timedelta(days=45), 'end': start_date + timedelta(days=60)},
        'Hypercare': {'start': start_date + timedelta(days=60), 'end': start_date + timedelta(days=75)}
    }
    
    # Create sample risk values
    risk_values = {phase: np.random.randint(10, 30) for phase in PHASE_WEIGHTS.keys()}
    
    # Calculate timeline using the existing function
    timeline_df = calculate_project_timeline(
        scenario_params=phase_data,
        baseline_params=phase_data,  # Using same dates for baseline
        risk_params=risk_values
    )
    
    return timeline_df 