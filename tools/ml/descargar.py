"""Descarga los datos para entrenar la corrección local del pronóstico.

1. Observaciones: temperatura del aire a 2 m de las estaciones automáticas del IDEAM en Manizales
   (datos.gov.co, conjunto sbwg-7ju4 "Temperatura Ambiente del Aire"), agregadas por hora.
2. Pronósticos: lo que Open-Meteo pronosticó para esas mismas horas y lugares con 0, 1 y 2 días de
   anticipación (Previous Runs API), con las variables que el mapa recibe en vivo.

Uso: tools/ml/.venv/Scripts/python tools/ml/descargar.py   -> data/ml/*.csv
"""
import json
import os
import time
import urllib.parse
import urllib.request

import pandas as pd

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'data', 'ml')

# estaciones del IDEAM dentro de la zona urbana de Manizales con datos recientes
ESTACIONES = {
    '0026155110': ('Aeropuerto La Nubia', 5.029777778, -75.469916667),
    '0026155170': ('Tesorito Finca', 5.032222222, -75.43833333),
}
DESDE, HASTA = '2024-07-30', '2026-07-24'
VARIABLES = ['temperature_2m', 'relative_humidity_2m', 'cloud_cover', 'wind_speed_10m', 'precipitation']


def get_json(url, intentos=4):
    for k in range(intentos):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'ManizalesPixel/0.1 (portafolio)'})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except Exception as e:          # la API pública a veces se demora: se reintenta
            print('  reintento', k + 1, e)
            time.sleep(10 * (k + 1))
    raise RuntimeError('no respondió: ' + url[:120])


def observaciones(codigo):
    filas, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            '$select': 'fechaobservacion,valorobservado',
            '$where': "codigoestacion='%s' AND fechaobservacion between '%sT00:00:00' and '%sT23:59:59'" % (codigo, DESDE, HASTA),
            '$order': 'fechaobservacion', '$limit': 50000, '$offset': offset})
        lote = get_json('https://www.datos.gov.co/resource/sbwg-7ju4.json?' + q)
        filas += lote
        if len(lote) < 50000:
            break
        offset += 50000
    df = pd.DataFrame(filas)
    df['hora'] = pd.to_datetime(df['fechaobservacion']).dt.floor('h')
    df['temp_obs'] = pd.to_numeric(df['valorobservado'], errors='coerce')
    df = df[(df['temp_obs'] > -5) & (df['temp_obs'] < 40)]          # fuera de rango físico = error de sensor
    horaria = df.groupby('hora').agg(temp_obs=('temp_obs', 'mean'), n=('temp_obs', 'size')).reset_index()
    return horaria


def pronosticos(lat, lon):
    hourly = []
    for v in VARIABLES:
        hourly += [v, v + '_previous_day1', v + '_previous_day2']
    out = []
    # por trozos de ~6 meses para no pedir demasiado de una vez
    for ini, fin in zip(pd.date_range(DESDE, HASTA, freq='180D'), list(pd.date_range(DESDE, HASTA, freq='180D'))[1:] + [pd.Timestamp(HASTA)]):
        q = urllib.parse.urlencode({
            'latitude': lat, 'longitude': lon, 'hourly': ','.join(hourly), 'timezone': 'America/Bogota',
            'start_date': ini.strftime('%Y-%m-%d'), 'end_date': fin.strftime('%Y-%m-%d')})
        d = get_json('https://previous-runs-api.open-meteo.com/v1/forecast?' + q)
        df = pd.DataFrame(d['hourly'])
        df['elevacion_modelo'] = d['elevation']
        out.append(df)
    df = pd.concat(out).drop_duplicates('time')
    df['hora'] = pd.to_datetime(df['time'])
    return df.drop(columns='time')


def main():
    os.makedirs(OUT, exist_ok=True)
    for codigo, (nombre, lat, lon) in ESTACIONES.items():
        print('estación', nombre)
        obs = observaciones(codigo)
        obs.to_csv(os.path.join(OUT, 'obs_%s.csv' % codigo), index=False)
        print('  observaciones horarias:', len(obs), obs['hora'].min(), '->', obs['hora'].max())
        # control de zona horaria: el máximo diario debería caer al mediodía-tarde local
        perfil = obs.groupby(obs['hora'].dt.hour)['temp_obs'].mean()
        print('  hora más cálida en promedio:', int(perfil.idxmax()), 'h · más fría:', int(perfil.idxmin()), 'h')
        pron = pronosticos(lat, lon)
        pron.to_csv(os.path.join(OUT, 'pron_%s.csv' % codigo), index=False)
        print('  pronósticos:', len(pron), 'horas')


if __name__ == '__main__':
    main()
