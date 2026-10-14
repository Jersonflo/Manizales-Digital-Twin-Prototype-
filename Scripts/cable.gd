extends Node2D
## Cabinas del cable aéreo. Cada Line2D hija es una línea: las cabinas suben por un cable
## y bajan por el otro, separado unos píxeles.

const SEPARACION_CABLES := 3.0

@export var cabina: Texture2D
@export var separacion := 36.0   ## px entre cabinas
@export var velocidad := 9.0     ## px por segundo

var _lineas: Array[Dictionary] = []
var _tiempo := 0.0


func _ready() -> void:
	for hijo in get_children():
		var linea := hijo as Line2D
		if linea == null or linea.points.size() < 2:
			continue
		var puntos := linea.points
		var largos: Array[float] = [0.0]
		for i in range(1, puntos.size()):
			largos.append(largos[-1] + puntos[i].distance_to(puntos[i - 1]))
		var vuelta := linea.duplicate() as Line2D     # segundo cable, de bajada
		vuelta.position = Vector2(0, SEPARACION_CABLES)
		add_child(vuelta)
		var total := largos[-1]
		var cabinas: Array[Sprite2D] = []
		for i in maxi(2, int(2.0 * total / separacion)):
			var s := Sprite2D.new()
			s.texture = cabina
			s.offset = Vector2(0, 4)
			add_child(s)
			cabinas.append(s)
		_lineas.append({"puntos": puntos, "largos": largos, "total": total, "cabinas": cabinas})


func _process(delta: float) -> void:
	_tiempo += delta
	for l in _lineas:
		var total: float = l["total"]
		var cabinas: Array[Sprite2D] = l["cabinas"]
		for i in cabinas.size():
			var s := fmod(_tiempo * velocidad + i * 2.0 * total / cabinas.size(), 2.0 * total)
			if s < total:
				cabinas[i].position = _punto(l, s).round()
			else:
				cabinas[i].position = (_punto(l, 2.0 * total - s) + Vector2(0, SEPARACION_CABLES)).round()


func _punto(l: Dictionary, s: float) -> Vector2:
	var puntos: PackedVector2Array = l["puntos"]
	var largos: Array[float] = l["largos"]
	for i in range(1, largos.size()):
		if s <= largos[i]:
			var tramo := largos[i] - largos[i - 1]
			var t := 0.0 if tramo <= 0.0 else (s - largos[i - 1]) / tramo
			return puntos[i - 1].lerp(puntos[i], t)
	return puntos[puntos.size() - 1]
