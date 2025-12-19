from pyscipopt import Model, quicksum
from functions import get_system, generate_graph_result, get_dict_result, save_sheet

# Importando o sistema
system = get_system()

total_points = len(system["DGer"]["Carga"])
n_uhe = len(system["UHE"])
n_ute = len(system["UTE"])

## Montando modelo de otimizacao
model = Model("Unit_Commitment")
model.setIntParam("display/verblevel", 0)

## Inicializa variaveis de decisão
vf, vt, vv, gt, ut, yt, wt, deficit = {}, {}, {}, {}, {}, {}, {}, {},

for t in range(total_points):
    for uhe in range(n_uhe):
        ## Variáveis de decisão das UHEs
        vf[(uhe, t)] = model.addVar(name=f"VF_UHE{uhe}_POINT{t}", vtype="C", lb=system["UHE"][uhe]["Vmin"], ub=system["UHE"][uhe]["Vmax"])
        vt[(uhe, t)] = model.addVar(name=f"VT_UHE{uhe}_POINT{t}", vtype="C", lb=0, ub=system["UHE"][uhe]["Engol"])
        vv[(uhe, t)] = model.addVar(name=f"VV_UHE{uhe}_POINT{t}", vtype="C", lb=0)

        ## Restrições: Balanço hídrico
        model.addCons(vf[(uhe, t)] + vt[(uhe, t)] + vv[(uhe, t)] == (vf[(uhe, t - 1)] if t > 0 else system["UHE"][uhe]["VI"]) + system["UHE"][uhe]["Afl"][t], name=f"Balanço hidrico {t} uhe {uhe}")

    for ute in range(n_ute):
        ## Variáveis de decisão das UTEs
        gt[(ute, t)] = model.addVar(name=f"GT_UTE{ute}_POINT{t}", vtype="C", ub=system["UTE"][ute]["Capac"])
        ut[(ute, t)] = model.addVar(name=f"UT_UTE{ute}_POINT{t}", vtype="B")
        wt[(ute, t)] = model.addVar(name=f"WT_UTE{ute}_POINT{t}", vtype="B")
        yt[(ute, t)] = model.addVar(name=f"YT_UTE{ute}_POINT{t}", vtype="C", lb=0, ub=1)

    ## Definindo variável de deficit
    deficit[t] = model.addVar(name=f"DEFICIT{t}", vtype="C", lb=0)

    ## Restrições: Atendimento da demanda
    uhe_gen = quicksum(vt[(uhe, t)] * system["UHE"][uhe]["Prod"] for uhe in range(n_uhe))
    ute_gen = quicksum(gt[(ute, t)] for ute in range(n_ute))
    model.addCons(uhe_gen + ute_gen + deficit[t] == system["DGer"]["Carga"][t], name=f"Atendimento da demanda {t}")


for t in range(total_points):
    for ute in range(n_ute):
        # Parâmetros de inicialização da UTE (t = -1)
        prev_ut = system["UTE"][ute]["PrevStatus"]
        prev_gt = system["UTE"][ute]["PrevGen"]
        initial_hours = system["UTE"][ute]["PrevHours"]

        # Modelagem das variáveis "w" e "y"
        model.addCons(yt[(ute, t)] == wt[(ute, t)] + (ut[(ute, t)] - (ut[(ute, t - 1)] if t > 0 else prev_ut)), name=f"Start_up_1_{ute}_{t}")
        model.addCons(yt[(ute, t)] + wt[(ute, t)] <= 1, name=f"Start_up_2_{ute}_{t}")

        # Parâmetros da UTE para restrição de Ton e Toff
        t_on = system["UTE"][ute]["Ton"]
        t_off = system["UTE"][ute]["Toff"]

        # Ton e Toff
        if t == 0:
            if prev_ut == 1:
                effective_ton = max(t_on - initial_hours, 0)
                model.addCons(quicksum(ut[(ute, t + i)] for i in range(effective_ton)) >= effective_ton, name=f"T_on_{ute}_{t}")
            else:
                effective_toff = max(t_off - initial_hours, 0)
                model.addCons(quicksum((1 - ut[(ute, t + i)]) for i in range(effective_toff)) >= effective_toff, name=f"T_off_{ute}_{t}")
        else:
            model.addCons(quicksum(ut[(ute, t + i)] if t + i < total_points else 0 for i in range(t_on)) >= min(t_on, total_points - t) * (ut[(ute, t)] - ut[(ute, t - 1)]), name=f"T_on_{ute}_{t}")
            model.addCons(quicksum((1 - ut[(ute, t + i)]) if t + i < total_points else 0 for i in range(t_off)) >= min(t_off, total_points - t) * (ut[(ute, t - 1)] - ut[(ute, t)]), name=f"T_off_{ute}_{t}")
 
        # Parâmetros da UTE para restrições de trajetoria de acionamento/desacionamento
        gt_min = system["UTE"][ute]["Gmin"]
        gt_max = system["UTE"][ute]["Capac"]
        TrUp = system["UTE"][ute]["TrUp"]
        TrDn = system["UTE"][ute]["TrDn"]
        NUp = len(TrUp)
        NDn = len(TrDn)

        # Variaveis auxiliares para trajetoria de acionamento/desacionamento
        sum_y = quicksum(yt[(ute, t - k + 1)] for k in range(1, NUp + 1) if t - k + 1 >= 0)
        sum_w = quicksum(wt[(ute, t + k)] for k in range(1, NDn + 1) if t + k < total_points)
        term_TrUp = quicksum(TrUp[k - 1] * yt[(ute, t - k + 1)] for k in range(1, NUp + 1) if t - k + 1 >= 0)
        term_TrDn = quicksum(TrDn[NDn - k] * wt[(ute, t + k)] for k in range(1, NDn + 1) if t + k < total_points)

        # Trajetória de acionamento/desacionamento
        model.addCons(gt[(ute, t)] >= gt_min * (ut[(ute, t)] - sum_y - sum_w) + term_TrUp + term_TrDn, name=f"traj_min_ute{ute}_t{t}")
        model.addCons(gt[(ute, t)] <= gt_max * (ut[(ute, t)] - sum_y - sum_w) + term_TrUp + term_TrDn, name=f"traj_max_ute{ute}_t{t}")
        
        # Parâmetros da UTE para restrições de rampa
        Ramp_up = system["UTE"][ute]["RampUp"]
        Ramp_down = system["UTE"][ute]["RampDown"]

        # Rampas de subida e descida
        g_prev = prev_gt if t == 0 else gt[(ute, t-1)]
        model.addCons(gt[(ute, t)] - g_prev <= Ramp_up , name=f"RampEq_Up_ute{ute}_t{t}")
        model.addCons(g_prev - gt[(ute, t)] <= Ramp_down , name=f"RampEq_Dn_ute{ute}_t{t}")

## FOB
ute_cost_total = quicksum(gt[(ute, t)] * system["UTE"][ute]["Custo"] for ute in range(n_ute) for t in range(total_points))
vv_cost_total = quicksum(vv[(uhe, t)] * system["UHE"][uhe]["VertCost"] for uhe in range(n_uhe) for t in range(total_points))
deficit_cost_total = quicksum(deficit[t] * system["DGer"]["CDef"] for t in range(total_points))

model.setObjective(ute_cost_total + vv_cost_total + deficit_cost_total, sense="minimize")

## Otimiza
model.optimize()

if model.getStatus() == "optimal":
    fob = model.getObjVal()
    print(f"\n✅ Resultado ótimo encontrado! FOB: {fob:.4f}")

    # Obtem dataframe de resultados
    df_final = get_dict_result(system, model)

    # Salva resultados
    file_name = "Resultados_Unit_Commitment"
    save_sheet(df_final, file_name)
    generate_graph_result(n_ute, n_uhe, df_final, file_name, fob)
else:
    print("❌ Deu pau na otimização!")