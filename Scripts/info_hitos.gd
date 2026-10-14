extends CanvasLayer
## Panel de información de los hitos. Clic (sin arrastrar) sobre un hito para abrirlo; clic en el vacío
## o Esc para cerrarlo. Al pasar el mouse por encima, el hito se ilumina.
## Cada hito es un Sprite2D hijo de `hitos` con metadata: nombre, tipo, info, fuente.

const ARRASTRE_MAXIMO := 5.0

@export var hitos: Node2D

var _panel: PanelContainer
var _titulo: Label
var _tipo: Label
var _texto: Label
var _fuente: Label
var _resaltado: Sprite2D
var _seleccionado: Sprite2D
var _inicio_clic := Vector2.ZERO


func _ready() -> void:
	_crear_panel()
	_panel.hide()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_resaltar(_hito_bajo(event.position))
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_inicio_clic = event.position
		elif event.position.distance_to(_inicio_clic) <= ARRASTRE_MAXIMO:
			var hito := _hito_bajo(event.position)
			if hito:
				_mostrar(hito)
			else:
				_cerrar()
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		_cerrar()


## Hito cuyo dibujo está bajo el puntero; si hay varios, el que está más al frente (más abajo en pantalla).
func _hito_bajo(pos_pantalla: Vector2) -> Sprite2D:
	if hitos == null:
		return null
	var pos := hitos.get_viewport().get_canvas_transform().affine_inverse() * pos_pantalla
	var mejor: Sprite2D = null
	for hijo in hitos.get_children():
		var s := hijo as Sprite2D
		if s == null or not s.has_meta("nombre"):
			continue
		var rect := s.get_rect()
		rect.position += s.global_position
		if rect.has_point(pos) and s.is_pixel_opaque(pos - s.global_position):
			if mejor == null or s.global_position.y > mejor.global_position.y:
				mejor = s
	return mejor


func _resaltar(hito: Sprite2D) -> void:
	if hito == _resaltado:
		return
	if _resaltado and _resaltado != _seleccionado:
		_resaltado.modulate = Color.WHITE
	_resaltado = hito
	if hito:
		hito.modulate = Color(1.25, 1.25, 1.15)
	Input.set_default_cursor_shape(Input.CURSOR_POINTING_HAND if hito else Input.CURSOR_ARROW)


func _mostrar(hito: Sprite2D) -> void:
	if _seleccionado and _seleccionado != hito:
		_seleccionado.modulate = Color.WHITE
	_seleccionado = hito
	hito.modulate = Color(1.25, 1.25, 1.15)
	_titulo.text = hito.get_meta("nombre", "")
	_tipo.text = String(hito.get_meta("tipo", "")).to_upper()
	_texto.text = hito.get_meta("info", "")
	var fuente: String = hito.get_meta("fuente", "")
	_fuente.text = "Fuente: " + fuente if fuente != "" else ""
	_panel.show()


func _cerrar() -> void:
	if _seleccionado:
		_seleccionado.modulate = Color.WHITE
		_seleccionado = null
	_panel.hide()


func _crear_panel() -> void:
	_panel = PanelContainer.new()
	_panel.anchor_top = 1.0
	_panel.anchor_bottom = 1.0
	_panel.offset_left = 12
	_panel.offset_top = -28
	_panel.offset_bottom = -28
	_panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_panel.custom_minimum_size = Vector2(300, 0)
	_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = Color(0.98, 0.96, 0.9, 0.96)
	estilo.border_color = Color(0.16, 0.15, 0.2)
	estilo.set_border_width_all(2)
	estilo.set_corner_radius_all(4)
	estilo.set_content_margin_all(12)
	estilo.shadow_color = Color(0, 0, 0, 0.25)
	estilo.shadow_size = 4
	_panel.add_theme_stylebox_override("panel", estilo)
	add_child(_panel)

	var caja := VBoxContainer.new()
	caja.add_theme_constant_override("separation", 6)
	_panel.add_child(caja)

	var fila := HBoxContainer.new()
	caja.add_child(fila)
	_tipo = _etiqueta(10, Color(0.75, 0.3, 0.24))
	_tipo.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	fila.add_child(_tipo)
	var cerrar := Button.new()
	cerrar.text = "×"
	cerrar.flat = true
	cerrar.focus_mode = Control.FOCUS_NONE
	cerrar.add_theme_color_override("font_color", Color(0.16, 0.15, 0.2))
	cerrar.pressed.connect(_cerrar)
	fila.add_child(cerrar)

	_titulo = _etiqueta(18, Color(0.16, 0.15, 0.2))
	caja.add_child(_titulo)
	_texto = _etiqueta(13, Color(0.22, 0.21, 0.26))
	caja.add_child(_texto)
	_fuente = _etiqueta(10, Color(0.45, 0.44, 0.48))
	caja.add_child(_fuente)


func _etiqueta(tamano: int, color: Color) -> Label:
	var l := Label.new()
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(276, 0)
	l.add_theme_font_size_override("font_size", tamano)
	l.add_theme_color_override("font_color", color)
	return l
