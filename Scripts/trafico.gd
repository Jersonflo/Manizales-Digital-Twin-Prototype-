extends Node2D
## Carritos que recorren las vías. Lee las celdas pintadas en la capa %Vias y mueve cada carro
## de celda en celda, por el carril derecho, girando al azar en los cruces.

const CELDA := 16
const CARRIL := 2.0
const DIRECCIONES: Array[Vector2i] = [Vector2i.RIGHT, Vector2i.DOWN, Vector2i.LEFT, Vector2i.UP]

## Hoja de carros: una fila por tipo; columnas = de lado (mira a la derecha), bajando, subiendo.
@export var hoja: Texture2D
@export var tipos := 6
@export var cantidad := 70
@export var velocidad_min := 14.0
@export var velocidad_max := 28.0

var _vias: Dictionary = {}
var _carros: Array[Dictionary] = []


func _ready() -> void:
	var capa := %Vias as TileMapLayer
	for celda in capa.get_used_cells():
		_vias[celda] = true
	var celdas := _vias.keys()
	if celdas.is_empty() or hoja == null:
		return
	for i in cantidad:
		var sprite := Sprite2D.new()
		sprite.texture = hoja
		sprite.region_enabled = true
		sprite.offset = Vector2(0, -5)
		add_child(sprite)
		var inicio: Vector2i = celdas.pick_random()
		var carro := {
			"sprite": sprite,
			"tipo": randi() % tipos,
			"desde": inicio,
			"hacia": inicio,
			"t": randf(),
			"vel": randf_range(velocidad_min, velocidad_max),
			"carril": Vector2.ZERO,
		}
		_siguiente(carro, inicio)
		_carros.append(carro)
		_colocar(carro, 1.0)


func _process(delta: float) -> void:
	for carro in _carros:
		carro["t"] += delta * carro["vel"] / CELDA
		if carro["t"] >= 1.0:
			carro["t"] -= 1.0
			var anterior: Vector2i = carro["desde"]
			carro["desde"] = carro["hacia"]
			_siguiente(carro, anterior)
		_colocar(carro, delta)


## Elige la próxima celda: prefiere seguir recto y solo se devuelve en un callejón sin salida.
func _siguiente(carro: Dictionary, anterior: Vector2i) -> void:
	var aqui: Vector2i = carro["desde"]
	var recto: Vector2i = aqui + (aqui - anterior)
	var opciones: Array[Vector2i] = []
	for d in DIRECCIONES:
		var vecina: Vector2i = aqui + d
		if vecina != anterior and _vias.has(vecina):
			opciones.append(vecina)
			if vecina == recto:
				opciones.append(vecina)
				opciones.append(vecina)
	if opciones.is_empty():
		carro["hacia"] = anterior if _vias.has(anterior) else aqui
	else:
		carro["hacia"] = opciones.pick_random()


func _colocar(carro: Dictionary, delta: float) -> void:
	var desde: Vector2i = carro["desde"]
	var hacia: Vector2i = carro["hacia"]
	var d: Vector2i = hacia - desde
	var sprite: Sprite2D = carro["sprite"]
	var columna := 0
	if d.y > 0:
		columna = 1
	elif d.y < 0:
		columna = 2
	sprite.flip_h = d.x < 0
	sprite.region_rect = Rect2(columna * CELDA, carro["tipo"] * CELDA, CELDA, CELDA)
	# carril derecho según el sentido de marcha; se desliza suave al girar
	var objetivo := Vector2(-d.y, d.x) * CARRIL
	carro["carril"] = (carro["carril"] as Vector2).move_toward(objetivo, 12.0 * delta)
	var centro := (Vector2(desde).lerp(Vector2(hacia), carro["t"]) + Vector2(0.5, 0.5)) * CELDA
	sprite.position = (centro + carro["carril"]).round()
