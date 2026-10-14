"""Entrena la corrección local del pronóstico de temperatura de Open-Meteo con estaciones del IDEAM.

Idea (post-procesamiento tipo MOS): el modelo global no conoce bien el microclima de una ciudad de
montaña. Se aprende el error (observado − pronosticado) en función de lo que dice el propio
pronóstico, la hora, la época del año y la anticipación, y luego se resta ese error esperado.

Validación honesta: la división es por tiempo (se entrena con lo anterior a CORTE y se evalúa con lo
posterior), nunca aleatoria. Se comparan:
  - Open-Meteo sin corregir
  - corrección simple: sesgo medio por hora del día
  - regresión lineal (Ridge)
  - gradient boosting (el modelo que se exporta)

Uso: tools/ml/.venv/Scripts/python tools/ml/entrenar.py
Escribe data/modelo_correccion.json (árboles para evaluar en Godot), data/metricas_modelo.json y gráficas en docs/img/.
"""
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ML = os.path.join(ROOT, 'data', 'ml')
IMG = os.path.join(ROOT, 'docs', 'img')
ESTACIONES = {'0026155110': 'Aeropuerto La Nubia', '0026155170': 'Tesorito Finca'}
UTC_A_LOCAL = pd.Timedelta(hours=-5)     # FechaObservacion del IDEAM viene en UTC (verificado con el ciclo diario)
CORTE = pd.Timestamp('2026-01-01')       # entrenamiento: antes; prueba: desde aquí
MIN_MUESTRAS_HORA = 1                    # estas estaciones reportan una vez por hora

# mismas variables, en el mismo orden, que calcula Scripts/correccion.gd con el pronóstico en vivo
FEATURES = ['t_pron', 'humedad', 'nubes', 'viento', 'lluvia', 'hora_sin', 'hora_cos', 'dia_sin', 'dia_cos', 'anticipacion']


def dataset():
    filas = []
    for codigo, nombre in ESTACIONES.items():
        obs = pd.read_csv(os.path.join(ML, 'obs_%s.csv' % codigo), parse_dates=['hora'])
        obs = obs[obs['n'] >= MIN_MUESTRAS_HORA].copy()
        obs['hora'] = obs['hora'] + UTC_A_LOCAL
        pron = pd.read_csv(os.path.join(ML, 'pron_%s.csv' % codigo), parse_dates=['hora'])
        df = obs.merge(pron, on='hora')
        for lead, suf in ((0, ''), (1, '_previous_day1'), (2, '_previous_day2')):
            d = pd.DataFrame({
                'hora': df['hora'], 'estacion': nombre, 'temp_obs': df['temp_obs'],
                't_pron': df['temperature_2m' + suf], 'humedad': df['relative_humidity_2m' + suf],
                'nubes': df['cloud_cover' + suf], 'viento': df['wind_speed_10m' + suf],
                'lluvia': df['precipitation' + suf], 'anticipacion': lead})
            filas.append(d)
    d = pd.concat(filas).dropna()
    h = d['hora'].dt.hour + d['hora'].dt.minute / 60.0
    doy = d['hora'].dt.dayofyear
    d['hora_sin'], d['hora_cos'] = np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24)
    d['dia_sin'], d['dia_cos'] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    d['error'] = d['temp_obs'] - d['t_pron']
    return d.reset_index(drop=True)


def mae(a):
    return float(np.mean(np.abs(a)))


def rmse(a):
    return float(np.sqrt(np.mean(np.square(a))))


def exportar(gbm, ruta):
    arboles = []
    for est in gbm.estimators_[:, 0]:
        t = est.tree_
        arboles.append({'izq': t.children_left.tolist(), 'der': t.children_right.tolist(),
                        'var': t.feature.tolist(), 'umbral': [round(float(v), 5) for v in t.threshold],
                        'valor': [round(float(v), 5) for v in t.value[:, 0, 0]]})
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump({'variables': FEATURES, 'base': float(gbm.init_.constant_.ravel()[0]),
                   'tasa': gbm.learning_rate, 'arboles': arboles}, f, separators=(',', ':'))


def main():
    os.makedirs(IMG, exist_ok=True)
    d = dataset()
    tr, te = d[d['hora'] < CORTE], d[d['hora'] >= CORTE]
    print('filas: entrenamiento %d · prueba %d (%s → %s)' % (len(tr), len(te), te['hora'].min().date(), te['hora'].max().date()))

    # 1) sesgo medio por hora del día y anticipación
    sesgo = tr.groupby([tr['hora'].dt.hour, 'anticipacion'])['error'].mean()
    pred_sesgo = te.apply(lambda r: sesgo.get((r['hora'].hour, r['anticipacion']), 0.0), axis=1)
    # 2) lineal
    ridge = Ridge(alpha=1.0).fit(tr[FEATURES], tr['error'])
    # 3) gradient boosting sobre el error
    gbm = GradientBoostingRegressor(loss='huber', n_estimators=250, max_depth=3, learning_rate=0.05,
                                    subsample=0.8, min_samples_leaf=40, random_state=7).fit(tr[FEATURES], tr['error'])
    te = te.copy()
    te['corr_sesgo'] = te['t_pron'] + pred_sesgo
    te['corr_lineal'] = te['t_pron'] + ridge.predict(te[FEATURES])
    te['corr_gbm'] = te['t_pron'] + gbm.predict(te[FEATURES])

    metricas = {'periodo_prueba': [str(te['hora'].min().date()), str(te['hora'].max().date())],
                'filas_entrenamiento': int(len(tr)), 'filas_prueba': int(len(te)), 'modelos': {}}
    for nombre, col in (('Open-Meteo', 't_pron'), ('Sesgo por hora', 'corr_sesgo'),
                        ('Regresión lineal', 'corr_lineal'), ('Gradient boosting', 'corr_gbm')):
        e = te['temp_obs'] - te[col]
        por_lead = {int(k): round(mae(g['temp_obs'] - g[col]), 3) for k, g in te.groupby('anticipacion')}
        metricas['modelos'][nombre] = {'mae': round(mae(e), 3), 'rmse': round(rmse(e), 3), 'sesgo': round(float(e.mean()), 3),
                                       'mae_por_anticipacion': por_lead}
        print('%-18s MAE %.2f °C · RMSE %.2f °C · sesgo %+.2f °C · MAE por días de anticipación %s'
              % (nombre, mae(e), rmse(e), e.mean(), por_lead))
    base, mejor = metricas['modelos']['Open-Meteo']['mae'], metricas['modelos']['Gradient boosting']['mae']
    metricas['mejora_mae_pct'] = round(100 * (base - mejor) / base, 1)
    print('mejora del MAE: %.1f %%' % metricas['mejora_mae_pct'])
    importancia = sorted(zip(FEATURES, gbm.feature_importances_), key=lambda kv: -kv[1])
    metricas['importancia'] = {k: round(float(v), 3) for k, v in importancia}
    with open(os.path.join(ROOT, 'data', 'metricas_modelo.json'), 'w', encoding='utf-8') as f:
        json.dump(metricas, f, ensure_ascii=False, indent=1)
    exportar(gbm, os.path.join(ROOT, 'data', 'modelo_correccion.json'))

    # gráficas para el README
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(7, 3.6))
    h = te['hora'].dt.hour
    for col, lab, c in (('t_pron', 'Open-Meteo', '#c9573e'), ('corr_gbm', 'Corregido con ML', '#2f7d4f')):
        ax.plot(range(24), [(te['temp_obs'] - te[col])[h == k].abs().mean() for k in range(24)], marker='o', ms=3, label=lab, color=c)
    ax.set_xlabel('Hora local')
    ax.set_ylabel('Error absoluto medio (°C)')
    ax.set_title('Error del pronóstico de temperatura por hora · estaciones IDEAM en Manizales')
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, 'error_por_hora.png'), dpi=140)

    fig, ax = plt.subplots(figsize=(7, 3.6))
    semana = te[(te['estacion'] == 'Aeropuerto La Nubia') & (te['anticipacion'] == 1)].sort_values('hora')
    semana = semana[(semana['hora'] >= semana['hora'].min() + pd.Timedelta(days=30)) &
                    (semana['hora'] < semana['hora'].min() + pd.Timedelta(days=37))]
    ax.plot(semana['hora'], semana['temp_obs'], color='#2a2733', lw=1.6, label='Observado (IDEAM)')
    ax.plot(semana['hora'], semana['t_pron'], color='#c9573e', lw=1.2, label='Open-Meteo (1 día antes)')
    ax.plot(semana['hora'], semana['corr_gbm'], color='#2f7d4f', lw=1.2, label='Corregido con ML')
    ax.set_ylabel('°C')
    ax.set_title('Una semana en Aeropuerto La Nubia')
    ax.legend(frameon=False, ncol=3, fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, 'semana_la_nubia.png'), dpi=140)
    print('listo: data/modelo_correccion.json, data/metricas_modelo.json, docs/img/*.png')


if __name__ == '__main__':
    main()
