extends Node2D
## Lo que el clima le hace al mapa: luz de día, atardecer y noche (con farolas y ventanas
## encendidas), nubes y lluvia sobre cada comuna, niebla, insignias de temperatura y el
## contorno de la comuna bajo el mouse. Lee los datos de %Clima.

const CELDA := 16
const COLOR_NOCHE := Color(0.24, 0.28, 0.48)
const COLOR_CREPUSCULO := Color(1.0, 0.78, 0.62)

@export var nubes: Node2D
@export var resplandor: Texture2D
@export var gota: Texture2D
@export var iconos: Texture2D
@export var faroles := PackedVector2Array()
@export var ventanas := PackedVector2Array()
@export var velocidad_transicion := 0.6

var _clima: Node
var _luz: CanvasModulate
var _capa_luces: CanvasLayer
var _luces: Array[MultiMeshInstance2D] = []
var _insignias: Array[Dictionary] = []
var _lluvias: Array[CPUParticles2D] = []
var _rect_comuna: Array[Rect2] = []
var _bordes: Array[PackedVector2Array] = []
var _niebla: ColorRect
var _resaltada := -1

var _luz_objetivo := Color.WHITE
var _noche_objetivo := 0.0
var _niebla_objetivo := 0.0
var _primera_vez := true
var capa := 0
var escala := Vector2(0, 1)              ## valores de la capa que van a los extremos del color (leyenda)
var _colores: Array[Color] = []
var _superposicion: Node2D


func _ready() -> void:
	_clima = %Clima
	_luz = CanvasModulate.new()
	add_child(_luz)
	_crear_luces()
	_crear_niebla()
	_preparar_comunas.call_deferred()
	_clima.actualizado.connect(aplicar)


func _preparar_comunas() -> void:
	var capa_insignias := CanvasLayer.new()          # las insignias no se oscurecen de noche
	capa_insignias.layer = 2
	capa_insignias.follow_viewport_enabled = true
	add_child(capa_insignias)
	for i in _clima.comunas.size():
		var c: Dictionary = _clima.comunas[i]
		var celdas: Array[Vector2i] = c["celdas"]
		var caja := Rect2i(celdas[0], Vector2i.ONE)
		var propias := {}
		for celda in celdas:
			caja = caja.expand(celda).expand(celda + Vector2i.ONE)
			propias[celda] = true
		_rect_comuna.append(Rect2(caja.position * CELDA, caja.size * CELDA))
		_bordes.append(_contorno(celdas, propias))
		_lluvias.append(_crear_lluvia(_rect_comuna[i]))
		_insignias.append(_crear_insignia(capa_insignias, c))
	aplicar()


func aplicar() -> void:
	if not _clima.hay_datos() or _lluvias.size() != _clima.comunas.size():
		return                               # aún no hay datos o las comunas no están montadas
	var sol: Dictionary = _clima.sol()
	var total_nubes := 0.0
	var niebla := 0.0
	var zonas := []
	for i in _clima.comunas.size():
		var e: Dictionary = _clima.estado(i)
		var codigo: int = e["codigo"]
		var lluvia := float(e["lluvia"])
		var cobertura := float(e["nubes"]) / 100.0
		total_nubes += cobertura
		if codigo == 45 or codigo == 48:
			niebla += 1.0
		var llueve := lluvia > 0.05 or (codigo >= 51 and codigo <= 67) or (codigo >= 80)
		var p := _lluvias[i]
		p.emitting = llueve
		p.amount = clampi(int(40 + lluvia * 90.0), 40, 320) if llueve else p.amount
		zonas.append({"rect": _rect_comuna[i], "cobertura": cobertura, "gris": llueve or codigo == 3})
		var ins: Dictionary = _insignias[i]
		(ins["icono"] as Sprite2D).region_rect = Rect2(_clima.icono(codigo, sol["dia"] > 0.5) * 16, 0, 16, 16)
		(ins["temp"] as Label).text = "%d°" % roundi(float(e["temp"]))
	total_nubes /= maxf(1.0, _clima.comunas.size())
	if nubes and nubes.has_method("configurar"):
		nubes.configurar(zonas, total_nubes)
	# luz: noche azul, crepúsculo anaranjado, y el cielo cubierto apaga un poco el día
	var dia: float = sol["dia"]
	var base := COLOR_NOCHE.lerp(Color.WHITE, dia)
	base = base.lerp(base * COLOR_CREPUSCULO, float(sol["crepusculo"]) * 0.8)
	_luz_objetivo = base.darkened(0.16 * total_nubes * dia)
	_luz_objetivo.a = 1.0
	_noche_objetivo = clampf(1.0 - dia * 1.4, 0.0, 1.0)
	_niebla_objetivo = clampf(niebla / maxf(1.0, _clima.comunas.size()) * 1.5, 0.0, 0.45)
	_colorear()
	if _primera_vez:                         # al abrir, sin transición desde el blanco
		_primera_vez = false
		_luz.color = _luz_objetivo
		for m in _luces:
			m.modulate.a = _noche_objetivo
		_niebla.color.a = _niebla_objetivo


func resaltar(i: int) -> void:
	if i != _resaltada:
		_resaltada = i
		_superposicion.queue_redraw()


## 0 sin capa · 1 temperatura · 2 probabilidad de lluvia · 3 ajuste del modelo de ML
func poner_capa(n: int) -> void:
	capa = n
	_colorear()


## Color de una comuna en la capa activa; `t` va de 0 a 1 dentro de `escala`
## (en el ajuste del ML, de −1 a 1).
static func color_capa(n: int, t: float) -> Color:
	match n:
		1:   # frío azul → amarillo → cálido rojo
			t = clampf(t, 0.0, 1.0)
			return Color(0.2, 0.42, 0.9).lerp(Color(0.98, 0.85, 0.25), t * 2.0) if t < 0.5 \
				else Color(0.98, 0.85, 0.25).lerp(Color(0.88, 0.2, 0.15), (t - 0.5) * 2.0)
		2:   # sin lluvia blanco → azul intenso
			return Color(0.96, 0.96, 0.93).lerp(Color(0.1, 0.3, 0.85), clampf(t, 0.0, 1.0))
		3:   # el modelo baja la temperatura: azul · la sube: rojo
			var a := clampf(t, -1.0, 1.0)
			return Color.WHITE.lerp(Color(0.88, 0.2, 0.15), a) if a > 0 else Color.WHITE.lerp(Color(0.2, 0.42, 0.9), -a)
	return Color.TRANSPARENT


## La temperatura usa el rango del momento (mínimo 2 °C de ancho) para que se noten las
## diferencias entre comunas, que suelen ser de 1 o 2 grados.
func _colorear() -> void:
	_colores.clear()
	if capa != 0 and _clima.hay_datos():
		var valores: Array[float] = []
		for i in _clima.comunas.size():
			var e: Dictionary = _clima.estado(i)
			valores.append(float(e["temp"]) if capa == 1 else (float(e["prob"]) if capa == 2 else float(e["ajuste_ml"])))
		match capa:
			1:
				var lo: float = valores.min()
				escala = Vector2(lo, maxf(valores.max(), lo + 2.0))
			2:
				escala = Vector2(0, 100)
			3:
				escala = Vector2(-1, 1)
		for v in valores:
			var c := color_capa(capa, v if capa == 3 else (v - escala.x) / (escala.y - escala.x))
			c.a = 0.55
			_colores.append(c)
	if _superposicion:
		_superposicion.queue_redraw()


func _process(delta: float) -> void:
	var k := clampf(delta * velocidad_transicion, 0.0, 1.0)
	_luz.color = _luz.color.lerp(_luz_objetivo, k)
	for m in _luces:
		m.modulate.a = lerpf(m.modulate.a, _noche_objetivo, k)
		m.visible = m.modulate.a > 0.01
	_niebla.color.a = lerpf(_niebla.color.a, _niebla_objetivo, k)


func _dibujar_superposicion() -> void:
	var lienzo := _superposicion
	if _colores.size() == _clima.comunas.size():
		for i in _colores.size():
			for celda in _clima.comunas[i]["celdas"]:
				lienzo.draw_rect(Rect2(Vector2(celda * CELDA), Vector2(CELDA, CELDA)), _colores[i])
			lienzo.draw_multiline(_bordes[i], Color(0.16, 0.15, 0.2, 0.6), 1.0)
	if _resaltada >= 0 and _resaltada < _bordes.size():
		lienzo.draw_multiline(_bordes[_resaltada], Color(1, 0.96, 0.75, 0.95), 2.0)


# ------------------------------------------------------------------ construcción

func _crear_luces() -> void:
	_capa_luces = CanvasLayer.new()          # aparte de la CanvasModulate: brillan de noche
	_capa_luces.layer = 1
	_capa_luces.follow_viewport_enabled = true
	add_child(_capa_luces)
	_superposicion = Node2D.new()            # capa de datos y contorno: tampoco se apagan de noche
	_superposicion.draw.connect(_dibujar_superposicion)
	_capa_luces.add_child(_superposicion)
	var aditivo := CanvasItemMaterial.new()
	aditivo.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	for grupo in [[faroles, 0.85, Color(1.0, 0.85, 0.55, 0.8)], [ventanas, 0.45, Color(1.0, 0.8, 0.45)]]:
		var puntos: PackedVector2Array = grupo[0]
		if puntos.is_empty():
			continue
		var malla := QuadMesh.new()
		malla.size = Vector2(32, 32) * float(grupo[1])
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_2D
		mm.mesh = malla
		mm.instance_count = puntos.size()
		for j in puntos.size():
			mm.set_instance_transform_2d(j, Transform2D(0.0, puntos[j]))
		var inst := MultiMeshInstance2D.new()
		inst.multimesh = mm
		inst.texture = resplandor
		inst.material = aditivo
		inst.self_modulate = grupo[2]
		inst.modulate.a = 0.0
		_capa_luces.add_child(inst)
		_luces.append(inst)


func _crear_niebla() -> void:
	_niebla = ColorRect.new()
	_niebla.color = Color(0.9, 0.93, 0.95, 0.0)
	_niebla.position = Vector2(-6000, -6000)
	_niebla.size = Vector2(16000, 14000)
	_niebla.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_niebla.z_index = 3
	add_child(_niebla)


func _crear_lluvia(rect: Rect2) -> CPUParticles2D:
	var p := CPUParticles2D.new()
	p.texture = gota
	p.emitting = false
	p.amount = 120
	p.lifetime = 0.5
	p.position = rect.get_center() - Vector2(0, 30)
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = rect.size / 2.0
	p.direction = Vector2(0.12, 1.0)
	p.spread = 3.0
	p.initial_velocity_min = 230.0
	p.initial_velocity_max = 290.0
	p.gravity = Vector2(0, 300)
	p.z_index = 2
	add_child(p)
	return p


func _crear_insignia(capa: CanvasLayer, c: Dictionary) -> Dictionary:
	var raiz := Node2D.new()
	raiz.position = c["insignia"]
	capa.add_child(raiz)
	var fondo := Panel.new()
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = Color(0.98, 0.96, 0.9, 0.88)
	estilo.border_color = Color(0.16, 0.15, 0.2, 0.9)
	estilo.set_border_width_all(1)
	estilo.set_corner_radius_all(3)
	fondo.add_theme_stylebox_override("panel", estilo)
	fondo.position = Vector2(-20, -10)
	fondo.size = Vector2(40, 18)
	fondo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	raiz.add_child(fondo)
	var icono := Sprite2D.new()
	icono.texture = iconos
	icono.region_enabled = true
	icono.region_rect = Rect2(0, 0, 16, 16)
	icono.position = Vector2(-10, -1)
	raiz.add_child(icono)
	var temp := Label.new()
	temp.position = Vector2(-1, -10)
	temp.size = Vector2(22, 18)
	temp.add_theme_font_size_override("font_size", 11)
	temp.add_theme_color_override("font_color", Color(0.16, 0.15, 0.2))
	temp.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	temp.mouse_filter = Control.MOUSE_FILTER_IGNORE
	raiz.add_child(temp)
	return {"raiz": raiz, "icono": icono, "temp": temp}


## Segmentos del borde de una comuna (lados de celda que dan a otra comuna o al vacío).
func _contorno(celdas: Array[Vector2i], propias: Dictionary) -> PackedVector2Array:
	var lineas := PackedVector2Array()
	for celda in celdas:
		var p := Vector2(celda * CELDA)
		if not propias.has(celda + Vector2i.UP):
			lineas.append_array([p, p + Vector2(CELDA, 0)])
		if not propias.has(celda + Vector2i.DOWN):
			lineas.append_array([p + Vector2(0, CELDA), p + Vector2(CELDA, CELDA)])
		if not propias.has(celda + Vector2i.LEFT):
			lineas.append_array([p, p + Vector2(0, CELDA)])
		if not propias.has(celda + Vector2i.RIGHT):
			lineas.append_array([p + Vector2(CELDA, 0), p + Vector2(CELDA, CELDA)])
	return lineas
