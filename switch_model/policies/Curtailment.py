# Copyright 2017 The Switch Authors. All rights reserved.
# Licensed under the Apache License, Version 2, which is in the LICENSE file.

import os
from pyomo.environ import *
import pandas as pd
"""

This module defines a simple Renewable Portfolio Standard (RPS) policy scheme
for the Switch-Pyomo model. In this scheme, each fuel is categorized as RPS-
elegible or not. All non-fuel energy sources are assumed to be RPS-elegible.
Dispatched electricity that is generated by RPS-elegible sources in each
period is summed up and must meet an energy goal, set as a required percentage
of all energy that is generated in that period.

This module assumes that the generators.core.no_commit module is being used.
An error will be raised if this module is loaded along the
generators.core.commit package.

TODO:
Allow the usage of the commit module.

"""

def define_components(mod):
    """
    
    f_rps_eligible[f in FUELS] is a binary parameter that flags each fuel as
    elegible for RPS accounting or not.
    
    RPS_ENERGY_SOURCES is a set enumerating all energy sources that contribute
    to RPS accounting. It is built by union of all fuels that are RPS elegible
    and the NON_FUEL_ENERGY_SOURCES set.
    
    RPS_PERIODS is a subset of PERIODS for which RPS goals are defined.
    
    rps_target[p in RPS_PERIODS] is the fraction of total generated energy in
    a period that has to be provided by RPS-elegible sources.
    
    RPSProjFuelPower[g, t in _FUEL_BASED_GEN_TPS] is an
    expression summarizing the power generated by RPS-elegible fuels in every
    fuel-based project. This cannot be simply taken to be equal to the
    dispatch level of the project, since a mix of RPS-elegible and unelegible
    fuels may be being consumed to produce that power. This expression is only
    valid when unit commitment is being ignored.
    
    RPSFuelEnergy[p] is an expression that sums all the energy produced using
    RPS-elegible fuels in fuel-based projects in a given period.
    
    RPSNonFuelEnergy[p] is an expression that sums all the energy produced
    using non-fuel sources in a given period.
    
    TotalGenerationInPeriod[p] is an expression that sums all the energy
    produced in a given period by all projects. This has to be calculated and
    cannot be taken to be equal to the total load in the period, because
    transmission losses could exist.
    
    RPS_Enforce_Target[p] is the constraint that forces energy produced by
    renewable sources to meet a fraction of the total energy produced in the
    period.
    
    """

    mod.PERIOD_Curtailment_MAX = Set(
    	dimen=2,
    	validate=lambda m, p, e: (
    		p in m.PERIODS and
    		e in m.ENERGY_SOURCES))
    
    """
    mod.Gen_Curtailment_Timepoints = Set(
        dimen=2,
        validate=lambda m, g, t: (
    		g,t in m.GEN_TPS and m.gen_energy_source[g] in m.Curtail_ENERGY_SOURCES and t in TPS_IN_PERIOD[p]))
    
    
    mod.Gen_TPS_IN_PERIOD = Set(
        dimen=3,
    	validate=lambda m, g, p, t: (
    		g in m.GENERATION_PROJECTS and
    		pt in m.TPS_IN_PERIOD))
    )
    """
    mod.max_curtailment_Rate = Param(
    	mod.PERIOD_Curtailment_MAX,
    	within=NonNegativeReals,
    	default=1)
    
    mod.Curtailment = Var(mod.GEN_TPS, within=NonNegativeReals)
    
    mod.Curtailment_Cost = Expression(
        mod.PERIOD_Curtailment_MAX,
        rule=lambda m, p, e: (
            sum(m.Curtailment[g, t] for (g,t) in m.GENERATION_PROJECTS*m.TPS_IN_PERIOD[p] if m.gen_energy_source[g] == e)))
    
    mod.Dispatch_Curtailment = Constraint(
    	mod.GEN_TPS,
    	rule=lambda m, g, t: (
    		m.DispatchGen[g, t] + m.Curtailment[g, t] == m.DispatchUpperLimit[g, t] ))
    
    mod.Curtailment_Rate = Constraint(
    	mod.PERIOD_Curtailment_MAX,
    	rule=lambda m, p, e: (
    		sum(m.Curtailment[g, t] * m.tp_weight[t] for (g,t) in m.GENERATION_PROJECTS*m.TPS_IN_PERIOD[p] if m.gen_energy_source[g] == e) <= m.max_curtailment_Rate[p, e] * sum(m.DispatchUpperLimit[g, t] * m.tp_weight[t] for (g,t) in m.GENERATION_PROJECTS*m.TPS_IN_PERIOD[p] if m.gen_energy_source[g] == e)))
    """
    mod.Max_Curtailment_Rate = Constraint(
    	mod.PERIOD_Curtailment_MAX,
    	rule=lambda m, p, e: (
    		sum(m.GenCapacity[g, p] for g in m.GENERATION_PROJECTS if m.gen_energy_source[g] == e) >= m.minimum_capacity[p, e]))
    """

def load_inputs(mod, switch_data, inputs_dir):
    """
    The RPS target goals input file is mandatory, to discourage people from
    loading the module if it is not going to be used. It is not necessary to
    specify targets for all periods.
    
    Mandatory input files:
        rps_targets.tab
            PERIOD rps_target
    
    The optional parameter to define fuels as RPS eligible can be inputted
    in the following file:
        fuels.tab
            fuel  f_rps_eligible
    
    """

    switch_data.load_aug(
    	filename=os.path.join(inputs_dir, 'curtailment_rate_max.tab'),
    	select=('Period', 'Energy_Source', 'Max_Curtailment_Rate'),
    	index=(mod.PERIOD_Curtailment_MAX),
    	param=[mod.max_curtailment_Rate])
def post_solve(instance, outdir):
    """
    Exported files:
    
    dispatch-wide.txt - Dispatch results timepoints in "wide" format with
    timepoints as rows, generation projects as columns, and dispatch level
    as values
    
    dispatch.csv - Dispatch results in normalized form where each row 
    describes the dispatch of a generation project in one timepoint.
    
    dispatch_annual_summary.csv - Similar to dispatch.csv, but summarized
    by generation technology and period.
    
    dispatch_zonal_annual_summary.csv - Similar to dispatch_annual_summary.csv
    but broken out by load zone. 
    
    dispatch_annual_summary.pdf - A figure of annual summary data. Only written
    if the ggplot python library is installed.
    """

    dispatch_normalized_dat = [{
        "generation_project": g,
        "gen_dbid": instance.gen_dbid[g],
        "gen_tech": instance.gen_tech[g],
        "gen_load_zone": instance.gen_load_zone[g],
        "gen_energy_source": instance.gen_energy_source[g],
        "timestamp": instance.tp_timestamp[t], 
        "tp_weight_in_year_hrs": instance.tp_weight_in_year[t],
        "period": instance.tp_period[t],
        "DispatchGen_MW_ideal": value(instance.DispatchUpperLimit[g, t]),
        "DispatchGen_MW_actual": value(instance.DispatchGen[g, t]),
        "Energy_GWh_typical_yr_ideal": value(
            instance.DispatchUpperLimit[g, t] * instance.tp_weight_in_year[t] / 1000),
        "Energy_GWh_typical_yr_actual": value(
            instance.DispatchGen[g, t] * instance.tp_weight_in_year[t] / 1000),    
        "VariableCost_per_yr": value(
            instance.DispatchUpperLimit[g, t] * instance.gen_variable_om[g] * 
            instance.tp_weight_in_year[t]),
        "DispatchEmissions_tCO2_per_typical_yr": value(sum(
            instance.DispatchEmissions[g, t, f] * instance.tp_weight_in_year[t]
              for f in instance.FUELS_FOR_GEN[g]
        )) if instance.gen_uses_fuel[g] else None
    } for g, t in instance.GEN_TPS ]
    dispatch_full_df = pd.DataFrame(dispatch_normalized_dat)
    dispatch_full_df.set_index(["generation_project", "timestamp"], inplace=True)
    dispatch_full_df.to_csv(os.path.join(outdir, "dispatch.csv"))
        

    annual_summary = dispatch_full_df.groupby(['gen_tech', "gen_energy_source", "period"]).sum()
    annual_summary.to_csv(
        os.path.join(outdir, "Curtailment_energy.csv"),
        columns=["Energy_GWh_typical_yr_ideal", "Energy_GWh_typical_yr_actual","VariableCost_per_yr", 
                 "DispatchEmissions_tCO2_per_typical_yr"])
    