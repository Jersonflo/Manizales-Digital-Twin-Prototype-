extends CanvasLayer
## Interfaz del clima: barra superior (hora de Manizales, estado general, fuente de los datos y
## selector de hora para ver el pronóstico) y panel de la comuna que se toca en el mapa.

const ARRASTRE_MAXIMO := 5.0
const DIAS := ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"]
const MESES := ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
const TINTA := Color(0.16, 0.15, 0.2)

@export var iconos: Texture2D

var _clima: Node
var _mapa: Node
var _hora: Label
var _resumen: Label
var _fuente: Label
var _selector: HSlider
var _selector_texto: Label
var _leyenda: Label
var boton_ml: CheckButton          ## expuestos para el recorrido de demostración (demo/tour.gd)
var opcion_capa: OptionButton
var _panel: PanelContainer
var _panel_caja: VBoxContainer
var _comuna := -1
var _inicio_clic := Vector2.ZERO


func _ready() -> void:
	_clima = %Clima
	_mapa = %ClimaMapa
	_crear_barra()
	_crear_panel()
	_clima.actualizado.connect(_refrescar)
	var reloj := Timer.new()           # la hora y la luz avanzan aunque no lleguen datos nuevos
	reloj.wait_time = 30.0
	reloj.autostart = true
	reloj.timeout.connect(_refrescar)
	add_child(reloj)
	_refrescar()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_mapa.resaltar(_comuna_bajo(event.position))
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_inicio_clic = event.position
		elif event.position.distance_to(_inicio_clic) <= ARRASTRE_MAXIMO:
			_comuna = _comuna_bajo(event.position)
			_llenar_panel()
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		_comuna = -1
		_llenar_panel()


func _comuna_bajo(pos_pantalla: Vector2) -> int:
	var mundo := get_viewport().get_canvas_transform().affine_inverse() * pos_pantalla
	return _clima.comuna_en(mundo)


func _refrescar() -> void:
	var sol: Dictionary = _clima.sol()
	var t := Time.get_datetime_dict_from_unix_time(sol["local"])
	var momento := "Noche"
	if sol["dia"] > 0.5:
		momento = "Día"
	if sol["crepusculo"] > 0.4:
		momento = "Amanecer" if t["hour"] < 12 else "Atardecer"
	_hora.text = "Manizales · %s %d %s · %02d:%02d · %s" % [DIAS[t["weekday"]], t["day"], MESES[t["month"] - 1],
		t["hour"], t["minute"], momento]
	if _clima.hay_datos():
		var suma := 0.0
		var minimo := 99.0
		var maximo := -99.0
		var nubes := 0.0
		for i in _clima.comunas.size():
			var e: Dictionary = _clima.estado(i)
			var temp := float(e["temp"])
			suma += temp
			minimo = minf(minimo, temp)
			maximo = maxf(maximo, temp)
			nubes += float(e["nubes"])
		var n := float(_clima.comunas.size())
		_resumen.text = "%d °C en promedio (de %d a %d °C) · nubosidad %d %%" % [
			roundi(suma / n), roundi(minimo), roundi(maximo), roundi(nubes / n)]
		if sol.has("sale"):
			_resumen.text += " · sol %s–%s" % [sol["sale"], sol["pone"]]
	else:
		_resumen.text = "Esperando datos del clima…"
	_fuente.text = _clima.fuente
	_fuente.add_theme_color_override("font_color", Color(0.2, 0.55, 0.3) if _clima.en_vivo else Color(0.7, 0.4, 0.2))
	_mapa.aplicar()
	_actualizar_leyenda()
	_llenar_panel()


func _al_mover_selector(valor: float) -> void:
	_clima.desfase_horas = int(valor)
	_selector_texto.text = "Ahora" if valor == 0 else "+%d h" % int(valor)
	_refrescar()


# ------------------------------------------------------------------ panel de la comuna

func _llenar_panel() -> void:
	for hijo in _panel_caja.get_children():
		hijo.queue_free()
	if _comuna < 0 or not _clima.hay_datos():
		_panel.hide()
		return
	var c: Dictionary = _clima.comunas[_comuna]
	var e: Dictionary = _clima.estado(_comuna)
	var sol: Dictionary = _clima.sol()
	var fila := HBoxContainer.new()
	var tipo := _texto("COMUNA %d" % c["numero"], 10, Color(0.75, 0.3, 0.24))
	tipo.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	fila.add_child(tipo)
	var cerrar := Button.new()
	cerrar.text = "×"
	cerrar.flat = true
	cerrar.focus_mode = Control.FOCUS_NONE
	cerrar.add_theme_color_override("font_color", TINTA)
	cerrar.pressed.connect(func(): _comuna = -1; _llenar_panel())
	fila.add_child(cerrar)
	_panel_caja.add_child(fila)
	_panel_caja.add_child(_texto(c["nombre"], 18, TINTA))
	if _clima.desfase_horas > 0:
		_panel_caja.add_child(_texto("Pronóstico para dentro de %d h" % _clima.desfase_horas, 11, Color(0.4, 0.4, 0.5)))

	var actual := HBoxContainer.new()
	actual.add_theme_constant_override("separation", 8)
	actual.add_child(_icono(_clima.icono(e["codigo"], sol["dia"] > 0.5), 2))
	actual.add_child(_texto("%d °C" % roundi(float(e["temp"])), 26, TINTA))
	actual.add_child(_texto(_clima.descripcion(e["codigo"]), 13, TINTA))
	_panel_caja.add_child(actual)
	var detalle := "Humedad %d %% · Viento %d km/h · Lluvia %.1f mm · Prob. %d %%" % [
		roundi(float(e["humedad"])), roundi(float(e["viento"])), float(e["lluvia"]), roundi(float(e["prob"]))]
	if e["sensacion"] != null:
		detalle = "Sensación %d °C · " % roundi(float(e["sensacion"])) + detalle
	var detalle_l := _texto(detalle, 11, Color(0.3, 0.3, 0.36))
	detalle_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	detalle_l.custom_minimum_size = Vector2(296, 0)
	_panel_caja.add_child(detalle_l)
	if _clima.tiene_modelo():
		var ajuste := float(e["ajuste_ml"])
		var ml_texto := "Open-Meteo %.1f °C · el modelo local ajusta %+.1f °C" % [float(e["temp_om"]), ajuste]
		if not _clima.usar_ml:
			ml_texto += " (desactivado)"
		_panel_caja.add_child(_texto(ml_texto, 11, Color(0.18, 0.49, 0.31)))

	_panel_caja.add_child(_texto("Próximas horas", 11, Color(0.75, 0.3, 0.24)))
	var horas := HBoxContainer.new()
	horas.add_theme_constant_override("separation", 14)
	for h in _clima.proximas_horas(_comuna):
		var col := VBoxContainer.new()
		col.add_child(_texto(h["hora"], 10, Color(0.4, 0.4, 0.5)))
		col.add_child(_icono(_clima.icono(h["codigo"], h["es_dia"]), 1))
		col.add_child(_texto("%d°" % roundi(float(h["temp"])), 12, TINTA))
		col.add_child(_texto("%d %%" % roundi(float(h["prob"])), 10, Color(0.25, 0.5, 0.75)))
		horas.add_child(col)
	_panel_caja.add_child(horas)

	_panel_caja.add_child(_texto("Próximos días", 11, Color(0.75, 0.3, 0.24)))
	for d in _clima.proximos_dias(_comuna):
		var f := HBoxContainer.new()
		f.add_theme_constant_override("separation", 8)
		var fecha := Time.get_datetime_dict_from_datetime_string(d["fecha"] + "T12:00:00", true)
		var nombre := _texto("%s %d" % [DIAS[fecha["weekday"]], fecha["day"]], 12, TINTA)
		nombre.custom_minimum_size = Vector2(56, 0)
		f.add_child(nombre)
		f.add_child(_icono(_clima.icono(d["codigo"], true), 1))
		f.add_child(_texto("%d° / %d°" % [roundi(float(d["min"])), roundi(float(d["max"]))], 12, TINTA))
		f.add_child(_texto("lluvia %d %%" % roundi(float(d["prob"])), 11, Color(0.25, 0.5, 0.75)))
		_panel_caja.add_child(f)
	_panel_caja.add_child(_texto("Open-Meteo en el centro de la comuna (ajustado a su altura)%s." % [
		" + corrección local con ML" if _clima.usar_ml and _clima.tiene_modelo() else ""], 9, Color(0.45, 0.44, 0.48)))
	_panel.show()


# ------------------------------------------------------------------ construcción

func _crear_barra() -> void:
	var barra := PanelContainer.new()
	barra.add_theme_stylebox_override("panel", _estilo())
	barra.anchor_left = 0.5
	barra.anchor_right = 0.5
	barra.offset_left = -270
	barra.offset_right = 270
	barra.offset_top = 8
	barra.grow_horizontal = Control.GROW_DIRECTION_BOTH
	add_child(barra)
	var caja := VBoxContainer.new()
	caja.add_theme_constant_override("separation", 2)
	barra.add_child(caja)
	_hora = _texto("", 14, TINTA)
	_resumen = _texto("", 11, Color(0.3, 0.3, 0.36))
	_fuente = _texto("", 10, Color(0.45, 0.44, 0.48))
	for l in [_hora, _resumen, _fuente]:
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		caja.add_child(l)
	var fila := HBoxContainer.new()
	fila.add_theme_constant_override("separation", 8)
	fila.add_child(_texto("Ver:", 11, TINTA))
	_selector = HSlider.new()
	_selector.min_value = 0
	_selector.max_value = 72
	_selector.step = 1
	_selector.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_selector.focus_mode = Control.FOCUS_NONE
	_selector.value_changed.connect(_al_mover_selector)
	fila.add_child(_selector)
	_selector_texto = _texto("Ahora", 11, TINTA)
	_selector_texto.custom_minimum_size = Vector2(44, 0)
	fila.add_child(_selector_texto)
	caja.add_child(fila)

	var opciones := HBoxContainer.new()
	opciones.add_theme_constant_override("separation", 10)
	var ml := CheckButton.new()
	boton_ml = ml
	ml.text = "Corregido con ML"
	ml.button_pressed = _clima.usar_ml and _clima.tiene_modelo()
	ml.disabled = not _clima.tiene_modelo()
	ml.focus_mode = Control.FOCUS_NONE
	ml.add_theme_font_size_override("font_size", 11)
	ml.add_theme_color_override("font_color", TINTA)
	ml.add_theme_color_override("font_pressed_color", TINTA)
	ml.add_theme_color_override("font_hover_color", TINTA)
	ml.add_theme_color_override("font_hover_pressed_color", TINTA)
	ml.toggled.connect(func(activo: bool): _clima.usar_ml = activo; _refrescar())
	opciones.add_child(ml)
	opciones.add_child(_texto("Capa:", 11, TINTA))
	var capa := OptionButton.new()
	opcion_capa = capa
	for nombre in ["Ninguna", "Temperatura", "Prob. de lluvia", "Ajuste del ML"]:
		capa.add_item(nombre)
	capa.focus_mode = Control.FOCUS_NONE
	capa.add_theme_font_size_override("font_size", 11)
	capa.item_selected.connect(_al_elegir_capa)
	opciones.add_child(capa)
	caja.add_child(opciones)
	_leyenda = _texto("", 10, Color(0.3, 0.3, 0.36))
	_leyenda.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_leyenda.hide()
	caja.add_child(_leyenda)
	var met: Dictionary = _clima.metricas
	if met.has("modelos"):
		var om: Dictionary = met["modelos"]["Open-Meteo"]
		var gb: Dictionary = met["modelos"]["Gradient boosting"]
		var nota := _texto("Modelo validado con estaciones IDEAM (%s a %s): error medio %.2f → %.2f °C (−%d %%)" % [
			met["periodo_prueba"][0], met["periodo_prueba"][1], om["mae"], gb["mae"], roundi(met["mejora_mae_pct"])],
			9, Color(0.45, 0.44, 0.48))
		nota.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		caja.add_child(nota)


func _al_elegir_capa(n: int) -> void:
	_mapa.poner_capa(n)
	_actualizar_leyenda()


func _actualizar_leyenda() -> void:
	var n: int = _mapa.capa
	_leyenda.visible = n != 0
	var e: Vector2 = _mapa.escala
	_leyenda.text = ["", "Temperatura:  azul %.1f °C → amarillo → rojo %.1f °C" % [e.x, e.y],
		"Probabilidad de lluvia:  blanco 0 % → azul 100 %",
		"Ajuste del ML:  azul = el modelo baja la temperatura · rojo = la sube (±1 °C)"][n]


func _crear_panel() -> void:
	_panel = PanelContainer.new()
	_panel.add_theme_stylebox_override("panel", _estilo())
	_panel.anchor_left = 1.0
	_panel.anchor_right = 1.0
	_panel.anchor_top = 1.0
	_panel.anchor_bottom = 1.0
	_panel.offset_left = -332
	_panel.offset_right = -12
	_panel.offset_top = -28
	_panel.offset_bottom = -28
	_panel.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	add_child(_panel)
	_panel_caja = VBoxContainer.new()
	_panel_caja.add_theme_constant_override("separation", 5)
	_panel.add_child(_panel_caja)
	_panel.hide()


func _estilo() -> StyleBoxFlat:
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = Color(0.98, 0.96, 0.9, 0.95)
	estilo.border_color = TINTA
	estilo.set_border_width_all(2)
	estilo.set_corner_radius_all(4)
	estilo.set_content_margin_all(10)
	estilo.shadow_color = Color(0, 0, 0, 0.25)
	estilo.shadow_size = 4
	return estilo


func _texto(t: String, tamano: int, color: Color) -> Label:
	var l := Label.new()
	l.text = t
	l.add_theme_font_size_override("font_size", tamano)
	l.add_theme_color_override("font_color", color)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	return l


func _icono(indice: int, escala: int) -> TextureRect:
	var at := AtlasTexture.new()
	at.atlas = iconos
	at.region = Rect2(indice * 16, 0, 16, 16)
	var r := TextureRect.new()
	r.texture = at
	r.custom_minimum_size = Vector2(16, 16) * escala
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	r.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	return r
