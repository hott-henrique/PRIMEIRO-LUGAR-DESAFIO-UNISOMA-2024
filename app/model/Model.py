import logging

import itertools as it

import pulp

import numpy as np

class Model(object):

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def optimze(self, params: dict) -> tuple[np.ndarray, str, float]:
        M = params['doctors']
        P = params['patientes']
        L = params['locals']
        H = params['hours']
        D = params['days']
        disp_m = params['disp_m']
        competencia_m_p = params['competence_m_p']
        local_m_l = params['local_m_l']
        local_p_l_d = params['local_p_l_d']
        dispon_m_d_h = params['dispon_m_d_h']
        dispon_p_d_h = params['dispon_p_d_h']

        comb = list(it.product(M, P, D, H, L))

        prob = pulp.LpProblem(name="Maximizar_Consultas", sense=pulp.LpMaximize)

        x1 = pulp.LpVariable.dicts(
            "x1",
            ((m, p, d, h, l) for m, p, d, h, l in comb),
            lowBound=0, upBound=1,
            cat='Binary'
        )

        # INFO: Objective Function
        prob += (pulp.lpSum(x1[m, p, d, h, l] for m, p, d, h, l in comb), "Total_Consultas")

        # INFO: Restrictions

        # DESCRIPTION: Doctor's max availability.
        for m in M:
            prob += pulp.lpSum(
                x1[m, p, d, h, l] for p in P for d in D for h in H for l in L
            ) <= disp_m[m], f"disp_medico_{m}"

        # INCLUDE
        # DESCRIPTION: Doctor's just one attends in each day-hour.
        for m in M:
            for d in D:
                for h in H:
                    prob += pulp.lpSum(
                        x1[m, p, d, h, l] for p in P for l in L
                    ) <= 1, f"max_consultas_medico_{m}_{d}_{h}"

        # DESCRIPTION: Each patient can consult a maximum of once per week.
        for p in P:
            prob += (
                pulp.lpSum( x1[m, p, d, h, l] for m in M for d in D for h in H for l in L ) <= 1,
                f"Max_consultas_paciente_{p}"
            )

        # DESCRIPTION: Doctor's competence.
        for m, p, d, h, l in comb:
            if competencia_m_p[m][p] == 0:
                prob += (x1[m, p, d, h, l] == 0, f"Competencia_{m}_{p}_{d}_{h}_{l}")

        # DESCRIPTION:  Doctor's available schedule.
        for m, p, d, h, l in comb:
            if dispon_m_d_h[m][d][h] == 0: #CHANGE
                prob += (x1[m, p, d, h, l] == 0, f"Horario_disponivel_medico_{m}_{p}_{d}_{h}_{l}")

        # DESCRIPTION: Doctor's available location.
        for m, p, d, h, l in comb:
            if local_m_l[m][l] == 0:
                prob += (x1[m, p, d, h, l] == 0, f"Local_disponivel_medico_{m}_{p}_{d}_{h}_{l}")

        # DESCRIPTION: Patient's available schedule.
        for m, p, d, h, l in comb:
            if dispon_p_d_h[p][d][h] == 0:
                prob += (x1[m, p, d, h, l] == 0, f"Horario_disponivel_paciente_{m}_{p}_{d}_{h}_{l}")

        # DESCRIPTION: Patient's available location.
        for m, p, d, h, l in comb:
            if local_p_l_d[p][l][d] == 0:
                prob += (x1[m, p, d, h, l] == 0, f"Local_disponivel_paciente_{m}_{p}_{d}_{h}_{l}")

        # DESCRIPTION: A doctor can only attend to one physical location per day.
        for m in M:
            for d in D:
                for l1, l2 in it.combinations(L, 2):
                    if (l1 == l2) or l1 == 0 or l2 == 0:
                        continue

                    prob += (
                        pulp.lpSum(x1[m, p, d, h, l1] + x1[m, p, d, h, l2] for p in P for h in H) <= 1,
                        f"Local_unico_medico_{m}_{p}_{d}_{h}_{l1}_{l2}"
                    )

        greedy_sol = list()
        patientes_attends = [ 0 ] * len(P)

        for m in M:
            med_consults = 0
            for d in D:
                local_define = 0

                if(med_consults >= disp_m[m]):
                    continue

                for l in L:
                    if(med_consults >= disp_m[m]):
                        continue

                    for p in P:
                        if(patientes_attends[p] or med_consults >= disp_m[m]):
                            continue

                        for h in H:
                            if(med_consults < disp_m[m] and
                               competencia_m_p[m][p] and
                               dispon_p_d_h[p][d][h] and
                               dispon_m_d_h[m][d][h] and
                               local_m_l[m][l] and
                               local_p_l_d[p][l][d]):
                                greedy_sol.append([m, p, d, h, l])
                                med_consults+=1
                                local_define = 1

                    if local_define:
                        break

        for m, p, d, h, l in greedy_sol:
            x1[m, p, d, h, l].setInitialValue(1)

        solver = pulp.PULP_CBC_CMD(msg=False, warmStart=True)

        prob.solve(solver)

        solution = list()

        for m, p, d, h, l in comb:
            if x1[m, p, d, h, l].varValue <= 0:
                continue

            solution.append([ m, p, d, h, l ])

            self.logger.debug(f"Doctor {m} attends Patient {p} on day {d} at {h} at location {l}.")

        return (np.array(solution), pulp.LpStatus[prob.status], prob.solutionTime)

if __name__ == "__main__":
    import json

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    m = Model(logger)

    with open(".ignored/example_2.json") as f:
        data = json.load(f)

        print(m.optimze(data))
