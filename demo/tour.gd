extends SceneTree
## Recorrido automático para grabar el video de la demo con el Movie Maker de Godot:
##   godot --path . --script res://demo/tour.gd --resolution 1152x648 --write-movie demo.avi --fixed-fps 30
## Espera el clima en vivo, recorre el centro, abre la Catedral, adelanta el pronóstico de la noche
## al día, abre una comuna, muestra las capas de datos y termina con el mapa completo.

var escena: Node
var camara: Camera2D
var clima: Node
var ui: Node


func _initialize() -> void:
	escena = load("res://Scenes/ManizalesPixel.tscn").instantiate()
	root.add_child(escena)
	camara = escena.get_node("Camara")
	clima = escena.get_node("Clima")
	ui = escena.get_node("ClimaUI")
	camara.set_process(false)                      # la cámara la mueve el recorrido, no el teclado
	camara.set_process_unhandled_input(false)
	camara.position = Vector2(860, 760)
	camara.zoom = Vector2(2, 2)
	_recorrido()


func _recorrido() -> void:
	var espera := 0
	while not clima.en_vivo and espera < 150:
		await process_frame
		espera += 1
	await _pausa(1.5)
	await _mover(Vector2(1250, 900), 2.0, 6.0)
	await _mover(Vector2(800, 760), 2.0, 3.0)
	var hitos: Node = escena.get_node("Mundo/Hitos")
	for h in hitos.get_children():
		if h.get_meta("nombre", "") == "Catedral Basílica":
			escena.get_node("Info")._mostrar(h)
	await _pausa(3.0)
	escena.get_node("Info")._cerrar()
	# de la noche al día: el selector avanza hasta media mañana
	var objetivo := 0
	for d in range(1, 30):
		clima.desfase_horas = d
		if clima.sol()["dia"] > 0.99 and Time.get_datetime_dict_from_unix_time(clima.sol()["local"])["hour"] >= 10:
			objetivo = d
			break
	clima.desfase_horas = 0
	var t := 0.0
	while t < 7.0:
		ui._selector.value = roundi(objetivo * t / 7.0)
		await process_frame
		t += root.get_process_delta_time()
	ui._selector.value = objetivo
	ui._comuna = 2
	ui._llenar_panel()
	await _mover(Vector2(1000, 900), 1.0, 2.5)
	await _pausa(1.5)
	ui.opcion_capa.select(1)
	ui._al_elegir_capa(1)
	await _pausa(3.0)
	ui.opcion_capa.select(3)
	ui._al_elegir_capa(3)
	await _pausa(3.0)
	ui.opcion_capa.select(0)
	ui._al_elegir_capa(0)
	ui._comuna = -1
	ui._llenar_panel()
	await _mover(Vector2(1368, 880), 0.5, 3.0)
	await _pausa(3.0)
	quit()


func _pausa(segundos: float) -> void:
	await create_timer(segundos).timeout


func _mover(destino: Vector2, zoom: float, segundos: float) -> void:
	var tw := create_tween().set_parallel().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_property(camara, "position", destino, segundos)
	tw.tween_property(camara, "zoom", Vector2(zoom, zoom), segundos)
	await tw.finished
