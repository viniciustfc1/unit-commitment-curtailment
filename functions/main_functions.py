from openpyxl.styles import Font

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import webbrowser
import numpy as np
import re


def get_system():
    # Lê e ajusta curva da ONS
    ons_curve = pd.read_csv("./curva_carga_semanal.csv",sep=';')
    ons_curve = ons_curve.loc[:24*7 - 1]
    ons_curve['load'] = ons_curve['load'].str.replace('.', '', regex=False)
    ons_curve['load'] = ons_curve['load'].str.replace(',', '.', regex=False)
    ons_curve['load'] = ons_curve['load'].astype(float)

    # Normalizando consumos para base mensal do caso original e convertendo em kw
    load_curve = list((ons_curve['load'] * (50 / (ons_curve["load"].sum())) * (len(ons_curve)/((24*30)))) * 1000 * 1.2)

    return {
        "UHE": [
            {
                "Vmax": 100.0,
                "Vmin": 20.0,
                "VI": 30,
                "Engol": 60 / (24*30), # Valor original do PDDE didática convertida em horas
                "Prod": 0.95 * 1000, # Para converter em kw
                "Afl": [np.mean(np.mean(np.array([[23, 16], [19, 14], [15, 11]]), axis=1)) / (24*30) for i in range(24*7)],
                "VertCost": 0.01
            }
        ],
        "UTE": [
            {
                "Capac": 15.0,
                "Custo": 10.0,
                "Gmin": 7.0,
                "TrUp": [1, 2, 3, 4, 4.5, 5, 6, 6.5, 6.5],
                "TrDn": [6, 5, 3, 1, 0.5, 0],
                "Ton": 8,
                "Toff": 7,
                "RampUp": 3.0,
                "RampDown": 3.0,
                "PrevStatus": 0,
                "PrevHours": 2,
                "PrevGen": 0
            },
            {
                "Capac": 10.0,
                "Custo": 25.0,
                "Gmin": 5.0,
                "TrUp": [0.5, 1.0, 1.5, 2.0, 4],
                "TrDn": [4, 3, 1],
                "Ton": 14,
                "Toff": 4,
                "RampUp": 2.0,
                "RampDown": 2.0,
                "PrevStatus": 1,
                "PrevHours": 1,
                "PrevGen": 8
            }
        ],
        "DGer": {
            "CDef": 1e6,
            "Carga": load_curve
        }
    }

def load_solar_normalization(file_path="./Simples Geração Solar Normalizado.csv"):
    """Lê as colunas 'Data' e 'Normalização Máximo' do CSV e retorna um dicionário.

    Retorna um dicionário com as chaves:
    - 'Data': lista de strings com as datas
    - 'Normalização Máximo': lista de floats com os valores normalizados
    - 'mapping': dicionário mapeando cada data para seu valor
    """
    df = pd.read_csv(file_path, sep=',')

    # Suporta variações na coluna de normalização (sem/ com acento e variações comuns)
    possible_norm_cols = [
        'Normalização Máximo', 'Normalizacao Máximo', 'Normalizacao Maximo', 'Normalização Maximo', 'Normalizacao Máximo'
    ]
    norm_col = next((c for c in possible_norm_cols if c in df.columns), None)

    if norm_col is None:
        raise KeyError(
            f"O arquivo CSV deve conter uma coluna de normalização ({possible_norm_cols}).\n"
            f"Colunas encontradas: {list(df.columns)}"
        )

    norm_list = df[norm_col].astype(float).tolist()

    return  norm_list

def get_dict_result(system, model):
    total_points = len(system["DGer"]["Carga"])
    n_uhe = len(system["UHE"])
    n_ute = len(system["UTE"])

    # Preparando dicionário para armazenar resultados por ponto
    results_dict = {t: {} for t in range(total_points)}

    for v in model.getVars():
        name = v.name
        value = model.getVal(v)

        # UHEs
        match_uhe = re.match(r"(VF|VT|VV)_UHE(\d+)_POINT(\d+)", name)
        if match_uhe:
            tipo, uhe_id, t = match_uhe.groups()
            t = int(t)
            uhe_id = int(uhe_id)
            if tipo == "VF":
                results_dict[t][f"Vol final UHE {uhe_id+1}"] = round(value, 8)
            elif tipo == "VT":
                results_dict[t][f"Vol turbinado UHE {uhe_id+1}"] = round(value, 8)
            elif tipo == "VV":
                results_dict[t][f"Vol vertido UHE {uhe_id+1}"] = round(value, 8)
        # UTEs
        match_ute = re.match(r"(GT|UT|WT|YT)_UTE(\d+)_POINT(\d+)", name)
        if match_ute:
            tipo, ute_id, t = match_ute.groups()
            t = int(t)
            ute_id = int(ute_id)
            if tipo == "GT":
                results_dict[t][f"Geracao UTE {ute_id+1}"] = round(value, 8)
            elif tipo == "UT":
                results_dict[t][f"Ligado UTE {ute_id+1}"] = round(value, 0)
            elif tipo == "YT":
                results_dict[t][f"Acionamento UTE {ute_id+1}"] = round(value, 0)
            elif tipo == "WT":
                results_dict[t][f"Desacionamento UTE {ute_id+1}"] = round(value, 0)
        # Déficit
        match_def = re.match(r"DEFICIT(\d+)", name)
        if match_def:
            t = int(match_def.group(1))
            results_dict[t]["Deficit"] = round(value, 8)
        
        # Solar e Curtailment
        match_solar = re.match(r"gr_ren_(\d+)", name)
        if match_solar:
            t = int(match_solar.group(1))
            results_dict[t]["Geracao Solar"] = round(value, 8)
            
        match_curt = re.match(r"curt_ren_(\d+)", name)
        if match_curt:
            t = int(match_curt.group(1))
            results_dict[t]["Curtailment"] = round(value, 8)

    # Adiciona geração total UHE, custo de UTEs, custo de vertimento e demanda
    for t in range(total_points):
        custo_vertimento = 0
        for uhe_id in range(n_uhe):
            vt_value = results_dict[t].get(f"Vol turbinado UHE {uhe_id+1}", 0)
            vv_value = results_dict[t].get(f"Vol vertido UHE {uhe_id+1}", 0)
            prod = system["UHE"][uhe_id]["Prod"]
            results_dict[t][f"Geracao UHE {uhe_id+1}"] = round(vt_value * prod, 8)
            custo_vertimento += vv_value * system["UHE"][uhe_id]["VertCost"]
        for uhe_id in range(n_uhe):
            results_dict[t][f"Custo vertimento UHE {uhe_id+1}"] = round(custo_vertimento, 8)

        for ute_id in range(n_ute):
            gt_value = results_dict[t].get(f"Geracao UTE {ute_id+1}", 0)
            ut_value = results_dict[t].get(f"Ligado UTE {ute_id+1}", 0)
            custo_ute = gt_value * system["UTE"][ute_id]["Custo"] #+ ut_value * system["UTE"][ute_id]["Custo fixo"]
            results_dict[t][f"Custo UTE {ute_id+1}"] = round(custo_ute, 8)

        results_dict[t]["Demanda"] = round(system["DGer"]["Carga"][t], 8)

    # Converte para DataFrame
    df_final = pd.DataFrame.from_dict(results_dict, orient="index")
    df_final = df_final.sort_index()

    # Define a ordem das colunas
    columns_list = []

    # UTEs: Ligado, Geracao, Custo
    for ute_id in range(n_ute):
        columns_list += [f"Ligado UTE {ute_id+1}", f"Acionamento UTE {ute_id+1}", f"Desacionamento UTE {ute_id+1}", f"Geracao UTE {ute_id+1}", f"Custo UTE {ute_id+1}"]

    # UHEs: Vol turbinado, Vol vertido, Vol final, Geracao, Custo vertimento
    for uhe_id in range(n_uhe):
        columns_list += [f"Vol turbinado UHE {uhe_id+1}", f"Vol vertido UHE {uhe_id+1}", f"Vol final UHE {uhe_id+1}", f"Geracao UHE {uhe_id+1}", f"Custo vertimento UHE {uhe_id+1}"]

    # Déficit e Demanda no final
    columns_list += ["Geracao Solar", "Curtailment", "Deficit", "Demanda"]

    df_final = df_final[columns_list]

    return df_final


def save_sheet(df_final, file_name):
    # Salva em Excel com cabeçalhos em negrito e fixados
    with pd.ExcelWriter(f"./Resultados/{file_name}.xlsx", engine="openpyxl") as writer:
        df_final.to_excel(writer, index_label="Hora", sheet_name="Resultados")
        worksheet = writer.sheets["Resultados"]

        # Freeze na primeira linha
        worksheet.freeze_panes = "A2"

        # Cabeçalhos em negrito
        for cell in worksheet[1]:
            cell.font = Font(bold=True)

    print(f"Arquivo salvo em: {file_name}.xlsx")


def plot_to_html(fig):
    return fig.to_html(full_html=False)


def extract_columns(df, prefix, n):
    """Extrai listas de colunas com prefixo e índice, se existirem."""
    result = []
    for i in range(n):
        col = f"{prefix} {i + 1}"
        if col in df.columns:
            result.append(df[col].to_numpy())
    return result


def create_multiline_fig(x, y_lists, labels, title, yaxis_title=""):
    """Cria um gráfico de múltiplas linhas genérico."""
    fig = go.Figure()
    for y, label in zip(y_lists, labels):
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name=label))
    fig.update_layout(
        title={'text': title, 'x': 0.5, 'y': 0.9, 'xanchor': 'center',
               'font': {'size': 25, 'color': 'black', 'family': 'Arial Black'}},
        xaxis=dict(title="Hora", title_font=dict(size=20, color='black', family='Arial Black')),
        yaxis=dict(title=yaxis_title, title_font=dict(size=20, color='black', family='Arial Black')),
        height=600,
        legend=dict(font=dict(size=15, family='Arial Black'))
    )
    return fig


def generate_graph_result(n_ute, n_uhe, df_final, file_name, fob):
    html_parts = []
    eixo_x = pd.date_range(start="2025-10-13 00:00", periods=168, freq="h")

    # Extraindo dados
    list_ger_ute = extract_columns(df_final, "Geracao UTE", n_ute)
    list_ger_uhe = extract_columns(df_final, "Geracao UHE", n_uhe)
    list_vol_final_uhe = extract_columns(df_final, "Vol final UHE", n_uhe)
    list_ligado = extract_columns(df_final, "Ligado UTE", n_ute)
    list_acionamento = extract_columns(df_final, "Acionamento UTE", n_ute)
    list_desacionamento = extract_columns(df_final, "Desacionamento UTE", n_ute)

    # Gráficos
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, [df_final['Demanda']], ['Demanda'], "Curva de Carga", "Carga (kW)")))
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, list_ligado, [f'UTE-{i+1}' for i in range(n_ute)], "Estado UTE's")))
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, list_acionamento, [f'UTE-{i+1}' for i in range(n_ute)], "Acionamento UTE's")))
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, list_desacionamento, [f'UTE-{i+1}' for i in range(n_ute)], "Desacionamento UTE's")))
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, list_ger_ute, [f'UTE-{i+1}' for i in range(n_ute)], "Geração UTE's", "Geração (kW)")))
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, list_ger_uhe, [f'UHE-{i+1}' for i in range(n_uhe)], "Geração UHE's", "Geração (kW)")))
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, list_vol_final_uhe, [f'UHE-{i+1}' for i in range(n_uhe)], "Volume Final UHE's", "Volume (hm³)")))
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, [df_final['Geracao Solar']], ['Solar'], "Geração Solar", "Geração (kW)")))
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, [df_final['Curtailment']], ['Curtailment'], "Curtailment", "Geração (kW)")))
    html_parts.append(plot_to_html(create_multiline_fig(eixo_x, [df_final['Deficit']], ['Déficit'], "Déficit Horário", "Déficit (kW)")))

    # Tabela
    html_parts.append(create_html_table(df_final, n_ute))

    # Salvando HTML
    os.makedirs('./Resultados', exist_ok=True)
    file_path = f'./Resultados/{file_name}.html'

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <title>Resultado — FOB = {fob:.4f}</title>
        </head>
        <body>
        <h1 style="text-align:center; font-family: Arial Black; color:black; margin-top:20px;">
            Resultado da Otimização: FOB = R${fob:.4f}
        </h1>
        {''.join(html_parts)}
        </body>
        </html>
        """)

    webbrowser.open(f'file://{os.path.abspath(file_path)}')
    print(f"✅ Arquivo HTML gerado com sucesso: {file_path}")


def create_html_table(df_final, n_ute, titulo="Tabela de Dados"):
    df_exibicao = df_final.copy()

    # Força índice como int e insere como coluna Hora
    df_exibicao.index = df_exibicao.index.astype(int)
    df_exibicao.insert(0, "Hora", df_exibicao.index)
    df_exibicao["Hora"] = df_exibicao["Hora"].astype(int)

    # Força as colunas Ligado UTE X como inteiros, substituindo NaN por 0
    for ute_id in range(n_ute):
        col = f"Ligado UTE {ute_id + 1}"
        if col in df_exibicao.columns:
            df_exibicao[col] = df_exibicao[col].fillna(0).astype(int)

    # Cabeçalho e estilos CSS
    tabela_html = f"""
    <table style="
        width:70%;
        border-collapse:collapse;
        margin:30px auto;
        font-family:Arial, sans-serif;
        font-size:14px;
        box-shadow:0 0 10px rgba(0,0,0,0.1);
    ">
        <thead>
            <tr>
                <th colspan="{len(df_exibicao.columns)}" 
                    style="font-size:18px; padding:10px; background-color:#000C7B; color:white; text-align:center;">
                    {titulo}
                </th>
            </tr>
            <tr style="background-color:#16417C; color:white;">
    """

    # Cabeçalhos das colunas
    for col in df_exibicao.columns:
        tabela_html += f'<th style="padding:10px; border:1px solid #ddd;">{col}</th>'
    tabela_html += "</tr></thead>\n<tbody>"

    # Preenche linhas do DataFrame com alternância de cor
    for i, (_, row) in enumerate(df_exibicao.iterrows()):
        bg_color = "#f9f9f9" if i % 2 == 0 else "#e0e0e0"
        tabela_html += f'<tr style="background-color:{bg_color};">'
        for col, value in row.items():
            # Se for Hora ou Ligado UTE, força inteiro
            if col == "Hora" or col.startswith("Ligado UTE"):
                tabela_html += f'<td style="padding:6px; border:1px solid #ddd; text-align:center;">{int(value)}</td>'
            # Se for outro int
            elif isinstance(value, (int, np.integer)):
                tabela_html += f'<td style="padding:6px; border:1px solid #ddd; text-align:center;">{value}</td>'
            # Se for float
            elif isinstance(value, float):
                tabela_html += f'<td style="padding:6px; border:1px solid #ddd; text-align:center;">{value:.2f}</td>'
            else:
                tabela_html += f'<td style="padding:6px; border:1px solid #ddd; text-align:center;">{value}</td>'
        tabela_html += "</tr>\n"

    tabela_html += "</tbody></table>"

    return tabela_html