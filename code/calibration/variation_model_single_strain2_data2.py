import numpy as np
from typing import List
from numba import jit
import pandas as pd
from datetime import datetime
from utils import get_beta
from datetime import datetime, timedelta
from numba import jit
from functions2wave_data2 import import_country, get_totR, update_contacts, get_contacts
import math
ncomp = 9
nage = 16

def SEIR_variation(start_date_org,
                  end_date,
                  start_week_delta,
                  vaxstart_date,
                  i0_q: float,
                  r0_q: float,
                  R0: float,
                  alpha: float,
                  gamma: float,
                  r: float,
                  eps: float,
                  mu: float,
                  ifr: List[float],
                  Delta: int,
                  VE: float,
                  VES: float,
                  # Delta_std: float,
                  Nk: List[float],
                  behaviour: str,
                  behaviour_bool: bool,
                  basin: str):
    """
    SEIR model with mobility data used to modulate the force of infection.
    Parameters
    ----------
        @param inf_t0 (int): initial number of infected
        @param rec_t0 (int): initial number of recovered
        @param Nk (List[float]): number of individuals in different age groups
        @param r (List[float]): contact reduction parameters
        @param T (int): simulation steps
        @param R0 (float): basic reproductive number
        @param eps (float): inverse of latent period
        @param mu (float): inverse of infectious period
        @param ifr (List[float]): infection fatality rate by age groups
        @param Delta (float): delay in deaths (mean)
        @param Delta_std (float): delay in deaths (std)
        @param C (List[List[float]]): contact matrix
        @param detection_rate (float): fraction of deaths that are reported
        @param dates (List[datetime]): list of simulation dates
        @param hemisphere (int): hemisphere (0: north, 1: tropical, 2: south)
        @param seasonality_min (float): seasonality parameter
        @param deaths_delay (str): method to calculate deaths delay. Defaults to "fixed" (alternative is "gamma")

    Return
    ------
        @return: dictionary of compartments and deaths

            S: 0, E: 1, I: 2, R: 3,
            SV: 4, EV: 5, IV: 6, RV: 7
            SV_NC: 8
    """
    if behaviour_bool == True:
        alpha = math.exp(alpha)
        gamma = math.exp(gamma)
    elif behaviour_bool == False:
        alpha = 0
        gamma = 0
    VEM = 1 - ((1 - VE) / (1 - VES))

    start_date = start_date_org + timedelta(weeks=int((start_week_delta)))
    T = (end_date - start_date).days
    T_nonvax = (vaxstart_date - start_date).days

    # number of age groups
    n_age = len(Nk)

    country_dict = import_country(basin, path_to_data='../data')

    deltadays = end_date - start_date
    dates = [start_date + timedelta(days=d) for d in range(deltadays.days)]

    # contact matrix
    Cs = {}
    for i in dates:
        Cs[i] = update_contacts(country_dict, i)

    # compute beta
    beta = get_beta(R0, mu, Nk, Cs[dates[0]])

    # get daily rate of vaccine for age group: rV_age
    file = pd.read_csv("../data2/regions/" + basin + "/epidemic/vac_1st_age_correct_ver(agegroup_adjust).csv",
                       index_col=0)
    date_uni = np.unique(file['date'])
    rV_age = []
    for d in date_uni:
        rV_age.append(list(file.loc[file['date'] == d, 'rV']))

    # initialize compartments and set initial conditions (S: 0, SB: 1, E: 2, I: 3, R: 4)
    compartments, deaths, infections = np.zeros((ncomp, nage, T)), np.zeros((nage, T)), np.zeros((nage, T))
    noncompliant, compliant = np.zeros((nage, T)), np.zeros((nage, T))

    # distribute intial infected and recovered among age groups
    for age in range(n_age):
        # I
        compartments[2, age, 0] = int(i0_q * Nk[age] * (1 / mu) / ((1 / mu) + (1 / eps)))
        # E
        compartments[1, age, 0] = int(i0_q * Nk[age]) - compartments[2, age, 0]
        # R
        compartments[3, age, 0] = int(r0_q * Nk[age])
        # S
        compartments[0, age, 0] = Nk[age] - (
                compartments[1, age, 0] + compartments[2, age, 0] + compartments[3, age, 0])

    V = 0
    Vt = []
    # simulate
    for t in np.arange(1, T, 1):

        if t >= 2:
            vt = V / sum(Nk)
        else:
            vt = 0
        if t >= 2:
            dt = 100000 * (sum(sum(deaths[:, 0: t - 1])) - sum(sum(deaths[:, 0: t - 2]))) / np.sum(Nk)
        else:
            dt = 0

        if behaviour == "constant_rate":
            if t >= T_nonvax + 1:
                nc_rate = [alpha for i in range(nage)]
                c_rate = [gamma for i in range(nage)]
            else:
                nc_rate = [0 for i in range(nage)]
                c_rate = [0 for i in range(nage)]
        elif behaviour == "vaccine_rate":
            nc_rate = [vt * alpha for i in range(nage)]
            c_rate = [dt * gamma for i in range(nage)]

        # compute force of infection
        force_inf = np.sum(beta * Cs[dates[t]] * (compartments[2, :, t - 1] + compartments[6, :, t - 1]) / Nk, axis=1)

        if t >= T_nonvax + 1:
            V_S = get_vaccinated(rV_age, compartments[:, :, t - 1].ravel('F'), t - 1 - T_nonvax,
                                 Nk)  # next time i.e. i step we have new vaccinated individuals VS VS_NC
            for age in range(nage):
                if compartments[0, age, t - 1] < V_S[age]:
                    compartments[4, age, t - 1] += compartments[0, age, t - 1]
                    compartments[0, age, t - 1] = 0
                else:
                    compartments[0, age, t - 1] -= V_S[age]  # S -
                    compartments[4, age, t - 1] += V_S[age]  # SV
        else:
            V_S = np.zeros(nage)
        # compute transitions

        # from S to E
        new_E = np.random.binomial(compartments[0, :, t - 1].astype(int), 1. - np.exp(-force_inf))

        # from SV to SV_NC, EV
        prob_SV_to_EV = (1 - VES) * force_inf
        prob_SV_to_NC = nc_rate

        total_leaving_from_SV = np.random.binomial(compartments[4, :, t - 1].astype(int),
                                                   1 - np.exp(-(prob_SV_to_EV + prob_SV_to_NC)))
        new_EV = np.random.binomial(total_leaving_from_SV, np.array(
            [a / b if b != 0 else 0 for a, b in zip(1 - np.exp(-prob_SV_to_EV),
                                                    1 - np.exp(
                                                        -(prob_SV_to_EV + prob_SV_to_NC)))]))
        new_SV_NC = total_leaving_from_SV - new_EV


        # from S_V_NC to SV, EV, EV_alpha
        prob_V_NC_to_EV = r * (1 - VES) * force_inf  # not probability but rate as force_int might be > 1

        prob_V_NC_to_SV = c_rate

        total_leaving_from_V_NC = np.random.binomial(compartments[8, :, t - 1].astype(int), 1 - np.exp(
            -(prob_V_NC_to_EV + prob_V_NC_to_SV)))

        new_EV_ = np.random.binomial(total_leaving_from_V_NC, np.array(
            [a / b if b != 0 else 0 for a, b in zip(1 - np.exp(-(prob_V_NC_to_EV)), 1 - np.exp(
                -(prob_V_NC_to_EV + prob_V_NC_to_SV)))]))
        new_V_NC_S = total_leaving_from_V_NC - new_EV_

        new_I = np.random.binomial(compartments[1, :, t - 1].astype(int), eps)
        new_R = np.random.binomial(compartments[2, :, t - 1].astype(int), mu)
        new_IV = np.random.binomial(compartments[5, :, t - 1].astype(int), eps)
        new_RV = np.random.binomial(compartments[6, :, t - 1].astype(int), mu)

        #  update next step solution
        # S
        compartments[0, :, t] = compartments[0, :, t - 1] - new_E
        # E
        compartments[1, :, t] = compartments[1, :, t - 1] + new_E - new_I
        # I
        compartments[2, :, t] = compartments[2, :, t - 1] + new_I - new_R
        # R
        compartments[3, :, t] = compartments[3, :, t - 1] + new_R

        # SV
        compartments[4, :, t] = compartments[4, :, t - 1] - new_EV - new_SV_NC + new_V_NC_S
        # EV
        compartments[5, :, t] = compartments[5, :, t - 1] + new_EV + new_EV_ - new_IV
        # IV
        compartments[6, :, t] = compartments[6, :, t - 1] + new_IV - new_RV
        # RV
        compartments[7, :, t] = compartments[7, :, t - 1] + new_RV

        # S_NC_V
        compartments[8, :, t] = compartments[8, :, t - 1] + new_SV_NC - new_V_NC_S - new_EV_

        # compute deaths
        if (t - 1) + Delta < deaths.shape[1]:
            deaths[:, (t - 1) + int(Delta)] += np.random.binomial( new_R, ifr)
            deaths[:, (t - 1) + int(Delta)] += np.random.binomial( new_RV, np.array(ifr)*(1 - VEM))
        infections[:, (t - 1)] = new_I + new_IV
        #infections[:, (t - 1)] = compartments[2, :, t] + compartments[6, :, t]

        # record noncompliant and compliant
        noncompliant[:, t] = compartments[8, :, t]
        compliant[:, t] = compartments[0, :, t] + compartments[4, :, t]

        Vt.append(np.sum(V_S))
        V += Vt[-1]

    deaths_sum = deaths.sum(axis=0)
    df_deaths = pd.DataFrame(data={"deaths": deaths_sum}, index=pd.to_datetime(dates))
    deaths_week = df_deaths.resample("W").sum()

    infections_sum = infections.sum(axis=0)
    df_infections = pd.DataFrame(data={"infections": infections_sum}, index=pd.to_datetime(dates))
    infections_week = df_infections.resample("W").sum()

    NCs_sum = noncompliant.sum(axis=0)
    # df_NCs = pd.DataFrame(data={"noncompliants": NCs_sum}, index=pd.to_datetime(dates))
    # NCs_week = df_NCs.resample("W").sum()

    Cs_sum = compliant.sum(axis=0)
    # df_Cs = pd.DataFrame(data={"compliants": Cs_sum}, index=pd.to_datetime(dates))
    # Cs_week = df_Cs.resample("W").sum()

    weekly_deaths = list(deaths_week.deaths.values)
    weekly_infections = list(infections_week.infections.values)
    # weekly_NCs = list(NCs_week.noncompliants.values)
    # weekly_Cs = list(Cs_week.compliants.values)
    daily_NCs = list(NCs_sum)
    daily_Cs = list(Cs_sum)

    for i in range(start_week_delta):
        weekly_deaths.insert(0, 0)
        weekly_infections.insert(0, 0)
    for i in range(start_week_delta*7):
        daily_NCs.insert(0, 0)
        daily_Cs.insert(0, 0)

    # print(weekly_NCs)

    return {'weekly_deaths': deaths_week.deaths.values[8 - start_week_delta:],
            'deaths_not_cut': weekly_deaths,
            'infections_not_cut': weekly_infections,
            'daily_noncompliant': daily_NCs,
            'daily_compliant': daily_Cs}

def get_vaccinated(rV_age, y, i, Nk):
    """
        This functions compute the n. of S individuals that will receive a vaccine in the next step
            :param rV (float): vaccination rate
            #:param Nk (array): number of individuals in different age groups
            :param y (array): compartment values at time t
            :param i (int): this time step from integrate_BV function
            :return: returns the two arrays of n. of vaccinated in different age groups for S and S_NC in the next step
    """

    t_rv = i

    V_S = np.zeros(nage)

    for age in range(nage):
        if y[(ncomp * age) + 0] <= 0:
            V_S[age] = 0
            continue
        if age == 0:
            V_S[age] = 0
        elif age == 1:
            rV = rV_age[t_rv][8]
            V_S[age] = round(rV * Nk[age])  # 5 - 9 years
        elif age <= 9:
            rV = rV_age[t_rv][age - 2]
            V_S[age] = round(rV * Nk[age])
        else:
            rV = rV_age[t_rv][age - 1]
            V_S[age] = rV * Nk[age]
    # print("V_S:",V_S)
    # print("V_S_NC:", V_S_NC)
    return V_S
