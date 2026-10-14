extends Node
## Clima en vivo y pronóstico por comuna, desde Open-Meteo (gratis, sin clave).
## Pide las 12 comunas en una sola consulta (una coordenada por comuna; Open-Meteo ajusta la
## temperatura a la altura de cada punto). Si no hay internet usa la última respuesta guardada
## y, si nunca hubo una, la muestra de data/clima_ejemplo.json.
## Los demás nodos leen `estado(i)`, `sol()` y escuchan `actualizado`.

signal actualizado

const URL := "https://api.open-meteo.com/v1/forecast"
const CACHE := "user://clima_cache.json"
const EJEMPLO := "res://data/clima_ejemplo.json"
const DATOS := "res://data/comunas.json"
const CELDA := 16
const VARIABLES_ACTUALES := "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,cloud_cover,wind_speed_10m"
const VARIABLES_HORARIAS := "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,cloud_cover,wind_speed_10m,is_day"
const VARIABLES_DIARIAS := "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"

const MODELO := "res://data/modelo_correccion.json"
const METRICAS := "res://data/metricas_modelo.json"

@export var refresco_minutos := 15.0
## Si es verdadero, la temperatura se corrige con el modelo entrenado con estaciones del IDEAM.
@export var usar_ml := true

var comunas: Array[Dictionary] = []      ## {numero, nombre, lat, lon, insignia: Vector2, celdas: Array[Vector2i]}
var celda_comuna := {}                   ## Vector2i -> índice de comuna
var desfase_horas := 0                   ## 0 = ahora; 1..72 = pronóstico
var fuente := "Cargando clima…"
var en_vivo := false

var metricas := {}                       ## resultado de la validación del modelo (data/metricas_modelo.json)

var _respuestas: Array = []              ## una respuesta de Open-Meteo por comuna (mismo orden)
var _http: HTTPRequest
var _ultima_consulta := 0.0
var _modelo := {}


func _ready() -> void:
	_cargar_comunas()
	var m = JSON.parse_string(FileAccess.get_file_as_string(MODELO)) if FileAccess.file_exists(MODELO) else null
	if m is Dictionary:
		_modelo = m
	var met = JSON.parse_string(FileAccess.get_file_as_string(METRICAS)) if FileAccess.file_exists(METRICAS) else null
	if met is Dictionary:
		metricas = met
	_http = HTTPRequest.new()
	_http.timeout = 20.0
	add_child(_http)
	_http.request_completed.connect(_al_responder)
	if not _usar_guardado(CACHE, "Sin conexión · datos guardados"):
		_usar_guardado(EJEMPLO, "Sin conexión · datos de muestra")
	consultar()
	var reloj := Timer.new()
	reloj.wait_time = refresco_minutos * 60.0
	reloj.autostart = true
	reloj.timeout.connect(consultar)
	add_child(reloj)


func hay_datos() -> bool:
	return _respuestas.size() == comunas.size() and not comunas.is_empty()


func consultar() -> void:
	if comunas.is_empty() or _http.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		return
	var lats := PackedStringArray()
	var lons := PackedStringArray()
	for c in comunas:
		lats.append(str(c["lat"]))
		lons.append(str(c["lon"]))
	var url := "%s?latitude=%s&longitude=%s&current=%s&hourly=%s&daily=%s&timezone=America%%2FBogota&forecast_days=5" % [
		URL, ",".join(lats), ",".join(lons), VARIABLES_ACTUALES, VARIABLES_HORARIAS, VARIABLES_DIARIAS]
	_ultima_consulta = Time.get_unix_time_from_system()
	if _http.request(url) != OK:
		_al_fallar()


func comuna_en(pos_mundo: Vector2) -> int:
	return celda_comuna.get(Vector2i(floori(pos_mundo.x / CELDA), floori(pos_mundo.y / CELDA)), -1)


## Estado de una comuna a la hora elegida con `desfase_horas`.
## "temp" es la temperatura que se muestra (corregida si `usar_ml`); "temp_om" la de Open-Meteo y
## "ajuste_ml" cuánto la mueve el modelo.
func estado(i: int) -> Dictionary:
	if not hay_datos():
		return {}
	var r: Dictionary = _respuestas[i]
	var e: Dictionary
	if desfase_horas == 0:
		var c: Dictionary = r["current"]
		e = {
			"temp_om": float(c["temperature_2m"]), "sensacion": c["apparent_temperature"],
			"humedad": c["relative_humidity_2m"], "lluvia": c["precipitation"],
			"prob": _horario(r, 0, "precipitation_probability"), "nubes": c["cloud_cover"],
			"codigo": int(c["weather_code"]), "viento": c["wind_speed_10m"], "es_dia": int(c["is_day"]) == 1,
		}
	else:
		e = {
			"temp_om": float(_horario(r, desfase_horas, "temperature_2m")), "sensacion": null,
			"humedad": _horario(r, desfase_horas, "relative_humidity_2m"),
			"lluvia": _horario(r, desfase_horas, "precipitation"),
			"prob": _horario(r, desfase_horas, "precipitation_probability"),
			"nubes": _horario(r, desfase_horas, "cloud_cover"),
			"codigo": int(_horario(r, desfase_horas, "weather_code")),
			"viento": _horario(r, desfase_horas, "wind_speed_10m"),
			"es_dia": int(_horario(r, desfase_horas, "is_day")) == 1,
		}
	var local := _ahora_local() + desfase_horas * 3600
	e["ajuste_ml"] = _ajuste(e["temp_om"], e["humedad"], e["nubes"], e["viento"], e["lluvia"], local, desfase_horas)
	e["temp"] = e["temp_om"] + (e["ajuste_ml"] if usar_ml else 0.0)
	if e["sensacion"] != null and usar_ml:
		e["sensacion"] = float(e["sensacion"]) + e["ajuste_ml"]
	return e


func tiene_modelo() -> bool:
	return not _modelo.is_empty()


## Corrección del modelo (°C) para un pronóstico: gradient boosting exportado desde tools/ml/entrenar.py.
## Variables en el mismo orden que FEATURES allí: t_pron, humedad, nubes, viento, lluvia,
## hora_sin, hora_cos, dia_sin, dia_cos, anticipacion (días).
func _ajuste(t_pron, humedad, nubes, viento, lluvia, local: int, desfase: int) -> float:
	if _modelo.is_empty():
		return 0.0
	var fecha := Time.get_datetime_dict_from_unix_time(local)
	var hora := float(fecha["hour"]) + float(fecha["minute"]) / 60.0
	var dia := float(Time.get_unix_time_from_datetime_dict({"year": fecha["year"], "month": fecha["month"], "day": fecha["day"]})
		- Time.get_unix_time_from_datetime_dict({"year": fecha["year"], "month": 1, "day": 1})) / 86400.0 + 1.0
	var x := [float(t_pron), float(humedad), float(nubes), float(viento), float(lluvia),
		sin(TAU * hora / 24.0), cos(TAU * hora / 24.0), sin(TAU * dia / 365.25), cos(TAU * dia / 365.25),
		float(clampi(desfase / 24, 0, 2))]
	var total: float = _modelo["base"]
	var tasa: float = _modelo["tasa"]
	for arbol in _modelo["arboles"]:
		var izq: Array = arbol["izq"]
		var nodo := 0
		while int(izq[nodo]) != -1:
			nodo = int(izq[nodo]) if x[int(arbol["var"][nodo])] <= float(arbol["umbral"][nodo]) else int(arbol["der"][nodo])
		total += tasa * float(arbol["valor"][nodo])
	return total


## Próximas `n` horas cada `paso` horas desde la hora elegida: [{hora, temp, prob, codigo, es_dia}].
func proximas_horas(i: int, n := 4, paso := 3) -> Array:
	var out := []
	if not hay_datos():
		return out
	var r: Dictionary = _respuestas[i]
	for k in range(1, n + 1):
		var d := desfase_horas + k * paso
		var t: String = _horario(r, d, "time")
		if t == "":
			break
		out.append({"hora": t.substr(11, 5), "temp": _temp_horaria(r, d),
			"prob": _horario(r, d, "precipitation_probability"), "codigo": int(_horario(r, d, "weather_code")),
			"es_dia": int(_horario(r, d, "is_day")) == 1})
	return out


## Hoy y los dos días siguientes: [{fecha, min, max, prob, codigo}].
func proximos_dias(i: int, n := 3) -> Array:
	var out := []
	if not hay_datos():
		return out
	var d: Dictionary = _respuestas[i]["daily"]
	var hoy := _indice_dia(_respuestas[i], desfase_horas)
	var horas: Array = _respuestas[i]["hourly"]["time"]
	var inicio := _indice_hora(_respuestas[i], 0)
	for k in range(hoy, mini(hoy + n, (d["time"] as Array).size())):
		# mínima y máxima a partir de la serie horaria, para que también reflejen la corrección
		var minimo := float(d["temperature_2m_min"][k])
		var maximo := float(d["temperature_2m_max"][k])
		if usar_ml and inicio >= 0:
			minimo = 99.0
			maximo = -99.0
			for j in horas.size():
				if (horas[j] as String).begins_with(d["time"][k]):
					var temp := _temp_horaria(_respuestas[i], j - inicio)
					minimo = minf(minimo, temp)
					maximo = maxf(maximo, temp)
		out.append({"fecha": d["time"][k], "min": minimo, "max": maximo,
			"prob": d["precipitation_probability_max"][k], "codigo": int(d["weather_code"][k])})
	return out


func _temp_horaria(r: Dictionary, desfase: int) -> float:
	var t := float(_horario(r, desfase, "temperature_2m"))
	if not usar_ml:
		return t
	var local := _ahora_local() - (_ahora_local() % 3600) + desfase * 3600
	return t + _ajuste(t, _horario(r, desfase, "relative_humidity_2m"), _horario(r, desfase, "cloud_cover"),
		_horario(r, desfase, "wind_speed_10m"), _horario(r, desfase, "precipitation"), local, maxi(desfase, 0))


## Hora local de Manizales para el desfase elegido y cuánto hay de día (0 noche, 1 día) y de
## crepúsculo (1 justo al amanecer o al atardecer), a partir de las horas reales de salida y puesta del sol.
func sol() -> Dictionary:
	var local := _ahora_local() + desfase_horas * 3600
	var info := {"local": local, "dia": 1.0, "crepusculo": 0.0}
	if not hay_datos():
		return info
	var r: Dictionary = _respuestas[0]
	var fecha := Time.get_date_string_from_unix_time(local)
	var dias: Array = r["daily"]["time"]
	var k := dias.find(fecha)
	if k < 0:
		return info
	var minuto := float(local % 86400) / 60.0
	var sale := _minuto_del_dia(r["daily"]["sunrise"][k])
	var pone := _minuto_del_dia(r["daily"]["sunset"][k])
	info["dia"] = smoothstep(sale - 35.0, sale + 35.0, minuto) * (1.0 - smoothstep(pone - 35.0, pone + 35.0, minuto))
	info["crepusculo"] = clampf(1.0 - minf(absf(minuto - sale), absf(minuto - pone)) / 70.0, 0.0, 1.0)
	info["sale"] = r["daily"]["sunrise"][k].substr(11, 5)
	info["pone"] = r["daily"]["sunset"][k].substr(11, 5)
	return info


static func icono(codigo: int, es_dia: bool) -> int:
	## Índice en Sprites/clima_iconos.png: sol, luna, sol_nube, luna_nube, nublado, niebla, llovizna, lluvia, tormenta
	if codigo <= 1:
		return 0 if es_dia else 1
	if codigo == 2:
		return 2 if es_dia else 3
	if codigo == 45 or codigo == 48:
		return 5
	if codigo >= 51 and codigo <= 57:
		return 6
	if (codigo >= 61 and codigo <= 67) or (codigo >= 80 and codigo <= 82):
		return 7
	if codigo >= 95:
		return 8
	return 4


static func descripcion(codigo: int) -> String:
	match codigo:
		0: return "Despejado"
		1: return "Casi despejado"
		2: return "Parcialmente nublado"
		3: return "Nublado"
		45, 48: return "Niebla"
		51, 53, 55, 56, 57: return "Llovizna"
		61, 66: return "Lluvia débil"
		63: return "Lluvia"
		65, 67: return "Lluvia fuerte"
		80: return "Chubascos débiles"
		81: return "Chubascos"
		82: return "Chubascos fuertes"
		95: return "Tormenta"
		96, 99: return "Tormenta con granizo"
	return "Nublado"


# ------------------------------------------------------------------ interno

func _cargar_comunas() -> void:
	var lista = JSON.parse_string(FileAccess.get_file_as_string(DATOS))
	if not lista is Array:
		push_error("No se pudo leer %s" % DATOS)
		return
	for i in lista.size():
		var c: Dictionary = lista[i]
		var celdas: Array[Vector2i] = []
		var plano: Array = c["celdas"]
		for k in range(0, plano.size(), 2):
			var celda := Vector2i(int(plano[k]), int(plano[k + 1]))
			celdas.append(celda)
			celda_comuna[celda] = i
		comunas.append({"numero": int(c["numero"]), "nombre": c["nombre"], "lat": c["lat"], "lon": c["lon"],
			"insignia": Vector2(c["insignia"][0], c["insignia"][1]), "celdas": celdas})


func _al_responder(resultado: int, codigo: int, _cabeceras: PackedStringArray, cuerpo: PackedByteArray) -> void:
	if resultado != HTTPRequest.RESULT_SUCCESS or codigo != 200:
		_al_fallar()
		return
	var texto := cuerpo.get_string_from_utf8()
	if not _aplicar(JSON.parse_string(texto)):
		_al_fallar()
		return
	en_vivo = true
	fuente = "En vivo · Open-Meteo · %s" % Time.get_time_string_from_unix_time(_ahora_local()).substr(0, 5)
	var f := FileAccess.open(CACHE, FileAccess.WRITE)
	if f:
		f.store_string(texto)
	actualizado.emit()


func _al_fallar() -> void:
	en_vivo = false
	if hay_datos() and not fuente.begins_with("Sin conexión"):
		fuente = "Sin conexión · últimos datos"
	actualizado.emit()


func _usar_guardado(ruta: String, texto: String) -> bool:
	if not FileAccess.file_exists(ruta):
		return false
	if not _aplicar(JSON.parse_string(FileAccess.get_file_as_string(ruta))):
		return false
	var hora: String = (_respuestas[0]["current"]["time"] as String).replace("T", " ")
	fuente = "%s (%s)" % [texto, hora]
	actualizado.emit.call_deferred()
	return true


func _aplicar(datos) -> bool:
	if datos is Dictionary:
		datos = [datos]
	if not datos is Array or (datos as Array).size() != comunas.size():
		return false
	for r in datos:
		if not (r is Dictionary and r.has("current") and r.has("hourly") and r.has("daily")):
			return false
	_respuestas = datos
	return true


## Segundos "unix" en hora local de Manizales (UTC-5, sin horario de verano).
func _ahora_local() -> int:
	var desfase_utc := -5 * 3600
	if hay_datos():
		desfase_utc = int(_respuestas[0].get("utc_offset_seconds", desfase_utc))
	return int(Time.get_unix_time_from_system()) + desfase_utc


func _indice_hora(r: Dictionary, desfase: int) -> int:
	var objetivo := Time.get_datetime_string_from_unix_time(_ahora_local() + desfase * 3600).substr(0, 13) + ":00"
	return (r["hourly"]["time"] as Array).find(objetivo)


func _indice_dia(r: Dictionary, desfase: int) -> int:
	var fecha := Time.get_date_string_from_unix_time(_ahora_local() + desfase * 3600)
	return maxi(0, (r["daily"]["time"] as Array).find(fecha))


func _horario(r: Dictionary, desfase: int, variable: String):
	var k := _indice_hora(r, desfase)
	var serie: Array = r["hourly"][variable]
	if k < 0 or k >= serie.size():
		return "" if variable == "time" else 0
	return serie[k]


func _minuto_del_dia(fecha_hora: String) -> float:
	return float(fecha_hora.substr(11, 2)) * 60.0 + float(fecha_hora.substr(14, 2))
