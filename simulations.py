import numpy as np
import pandas as pd
import datetime as dt
from datetime import timedelta
from phase_model import calculate_project_timeline

def pert_random(min_val, most_likely, max_val, size=1):
    """
    Generate random numbers using a PERT distribution
    PERT is better than triangular for project management as it gives more weight to the most likely value
    """
    alpha = 4
    # Calculate PERT beta distribution parameters
    a = 1 + alpha * (most_likely - min_val) / (max_val - min_val)
    b = 1 + alpha * (max_val - most_likely) / (max_val - min_val)
    
    # Generate random numbers from beta distribution
    beta_samples = np.random.beta(a, b, size=size)
    
    # Scale to our desired range
    return min_val + beta_samples * (max_val - min_val)

def run_holistic_monte_carlo(scenario_windows, risk_values, n_simulations=5000, base_monthly_cost=100000):
    """
    Run holistic Monte Carlo simulation considering quality, duration, and cost
    
    Parameters:
    -----------
    scenario_windows : dict
        Dictionary containing phase windows with start and end dates
    risk_values : dict
        Dictionary containing risk values for each phase
    n_simulations : int
        Number of Monte Carlo simulations to run
    base_monthly_cost : float
        Base monthly cost of the project team
        
    Returns:
    --------
    pd.DataFrame
        DataFrame containing simulation results with columns:
        sim_quality, sim_duration_days, sim_cost
    """
    results = []
    
    for sim in range(n_simulations):
        # Create a copy of scenario windows for this simulation
        sim_windows = {}
        
        # Apply variability to each phase duration
        for phase, window in scenario_windows.items():
            original_duration = (window['end'] - window['start']).days
            
            # Define variation ranges (-15% to +30%)
            min_duration = original_duration * 0.85  # -15%
            max_duration = original_duration * 1.30  # +30%
            
            # Generate random duration using PERT distribution
            new_duration = pert_random(min_duration, original_duration, max_duration)[0]
            
            # Create new window with varied duration
            sim_windows[phase] = {
                'start': window['start'],
                'end': window['start'] + timedelta(days=new_duration)
            }
        
        try:
            # Calculate project timeline with varied durations
            timeline_result = calculate_project_timeline(sim_windows, sim_windows, risk_values)
            
            # Extract quality and duration (get the last total_quality value)
            quality = timeline_result['total_quality'].iloc[-1]
            
            # Calculate total duration in days
            project_start = min(window['start'] for window in sim_windows.values())
            project_end = max(window['end'] for window in sim_windows.values())
            duration_days = (project_end - project_start).days
            
            # Calculate duration in months (rounded up to nearest month)
            duration_months = np.ceil(duration_days / 30)
            
            # Apply variability to monthly cost (-5% to +5%)
            cost_variation = np.random.uniform(0.95, 1.05)
            monthly_cost = base_monthly_cost * cost_variation
            
            # Calculate total cost
            total_cost = monthly_cost * duration_months
            
            # Store results
            results.append({
                'sim_quality': quality,
                'sim_duration_days': duration_days,
                'sim_cost': total_cost
            })
            
        except Exception as e:
            print(f"Simulation {sim} failed: {str(e)}")
            continue
    
    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    
    return results_df

def calculate_confidence_intervals(results_df):
    """
    Calculate confidence intervals and statistics for simulation results
    """
    metrics = {}
    
    for column in ['sim_quality', 'sim_duration_days', 'sim_cost']:
        values = results_df[column]
        metrics[column] = {
            'mean': values.mean(),
            'median': values.median(),
            'std': values.std(),
            'p10': values.quantile(0.10),
            'p90': values.quantile(0.90)
        }
    
    return metrics 