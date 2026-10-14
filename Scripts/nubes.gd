extends Node2D
## Nubes que cruzan el mapa despacio de oeste a este. Sin datos de clima flotan unas pocas al azar;
## con clima, %ClimaMapa llama a `configurar()` y cada comuna lleva tantas nubes como su cobertura
## (grises si llueve o está cubierto), más unas cuantas sobre las montañas según el promedio.

const MAXIMO_POR_COMUNA := 5
const MAXIMO_FONDO := 10

@export var texturas: Array[Texture2D] = []
@export var cantidad := 9
@export var area := Rect2(0, 0, 2736, 1760)
@export var velocidad := 6.0

var _nubes: Array[Dictionary] = []      ## {sprite, zona: Rect2, ritmo, gris: bool}


func _ready() -> void:
	if texturas.is_empty():
		return
	for i in cantidad:
		_nubes.append(_nueva(area, false, true))


func configurar(zonas: Array, promedio: float) -> void:
	_repartir(zonas, promedio)


func _repartir(zonas: Array, promedio: float) -> void:
	if texturas.is_empty():
		return
	var deseadas := []
	for z in zonas:
		for k in roundi(clampf(z["cobertura"], 0.0, 1.0) * MAXIMO_POR_COMUNA):
			deseadas.append([z["rect"], z["gris"]])
	if not zonas.is_empty():
		for k in roundi(clampf(promedio, 0.0, 1.0) * MAXIMO_FONDO):
			deseadas.append([area, false])
	# se reutilizan las nubes que ya existen para que no haya saltos
	while _nubes.size() > deseadas.size():
		var n: Dictionary = _nubes.pop_back()
		(n["sprite"] as Sprite2D).queue_free()
	for k in deseadas.size():
		var rect: Rect2 = deseadas[k][0]
		var gris: bool = deseadas[k][1]
		if k < _nubes.size():
			_nubes[k]["zona"] = rect
			_nubes[k]["gris"] = gris
			if not rect.grow(120).has_point((_nubes[k]["sprite"] as Sprite2D).position):
				(_nubes[k]["sprite"] as Sprite2D).position = _punto_en(rect, true)
		else:
			_nubes.append(_nueva(rect, gris, true))


func _nueva(rect: Rect2, gris: bool, en_cualquier_x: bool) -> Dictionary:
	var s := Sprite2D.new()
	s.texture = texturas[randi() % texturas.size()]
	s.position = _punto_en(rect, en_cualquier_x)
	s.scale = Vector2.ONE * (2.0 if randf() < 0.3 else 1.0)
	s.flip_h = randf() < 0.5
	add_child(s)
	return {"sprite": s, "zona": rect, "ritmo": randf_range(0.6, 1.4), "gris": gris}


func _punto_en(rect: Rect2, en_cualquier_x: bool) -> Vector2:
	var x := randf_range(rect.position.x, rect.end.x) if en_cualquier_x else rect.position.x - 60.0
	return Vector2(x, randf_range(rect.position.y, rect.end.y))


func _process(delta: float) -> void:
	for n in _nubes:
		var s: Sprite2D = n["sprite"]
		var zona: Rect2 = n["zona"]
		s.position.x += velocidad * float(n["ritmo"]) * delta
		if s.position.x > zona.end.x + 60.0:
			s.position = _punto_en(zona, false)
		var objetivo := Color(0.72, 0.75, 0.8, 0.95) if n["gris"] else Color(1, 1, 1, 0.9)
		s.modulate = s.modulate.lerp(objetivo, clampf(delta, 0.0, 1.0))
