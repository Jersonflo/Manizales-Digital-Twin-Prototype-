extends Camera2D
## Cámara del mapa: arrastrar con clic izquierdo o medio, rueda para el zoom, flechas o WASD para moverse.

const NIVELES: Array[float] = [0.5, 1.0, 2.0, 3.0, 4.0]

## Rectángulo del mapa en píxeles; la cámara no deja que su centro salga de aquí.
@export var limite := Rect2(0, 0, 2736, 1760)
@export var velocidad := 500.0

var _nivel := 2
var _arrastrando := false


func _ready() -> void:
	zoom = Vector2.ONE * NIVELES[_nivel]


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT or event.button_index == MOUSE_BUTTON_MIDDLE:
			_arrastrando = event.pressed
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_cambiar_zoom(1)
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_cambiar_zoom(-1)
	elif event is InputEventMouseMotion and _arrastrando:
		position -= event.relative / zoom.x
		_acotar()


func _process(delta: float) -> void:
	var dir := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	if dir == Vector2.ZERO:
		dir.x = float(Input.is_physical_key_pressed(KEY_D)) - float(Input.is_physical_key_pressed(KEY_A))
		dir.y = float(Input.is_physical_key_pressed(KEY_S)) - float(Input.is_physical_key_pressed(KEY_W))
	if dir != Vector2.ZERO:
		position += dir.normalized() * velocidad * delta / zoom.x
		_acotar()


func _cambiar_zoom(paso: int) -> void:
	_nivel = clampi(_nivel + paso, 0, NIVELES.size() - 1)
	zoom = Vector2.ONE * NIVELES[_nivel]


func _acotar() -> void:
	position = position.clamp(limite.position, limite.end)
