shader_type canvas_item;
// Vaivén de árboles y arbustos en el atlas de objetos (celdas de 16x32).
// Desplaza filas enteras de píxeles: la copa se mueve, la base queda quieta y el pixel art no se emborrona.

uniform vec2 celdas = vec2(16.0, 5.0);   // columnas y filas del atlas
uniform float fuerza = 1.0;              // amplitud máxima en píxeles
uniform float rapidez = 1.6;

varying vec2 mundo;

void vertex() {
	mundo = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy;
}

void fragment() {
	vec2 local = fract(UV * celdas);                       // 0..1 dentro de la celda
	float columna = floor(mundo.x / 16.0);
	// ráfaga que recorre el mapa de oeste a este, distinta en cada columna
	float fase = TIME * rapidez - columna * 0.55 + sin(columna * 1.7) * 1.3;
	float altura = pow(clamp(1.0 - local.y, 0.0, 1.0), 1.5);
	float px = round(sin(fase) * fuerza * altura * 1.4);
	float lx = local.x - px / 16.0;
	vec4 c = texture(TEXTURE, UV - vec2(px * TEXTURE_PIXEL_SIZE.x, 0.0));
	COLOR = (lx < 0.0 || lx >= 1.0) ? vec4(0.0) : c;
}
