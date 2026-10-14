"""Textos del panel de información de cada hito, verificados el 13-oct-2026.

Cuando las fuentes no coinciden se usa la cifra más respaldada o se redondea ("más de", "unos").
Clave: el nombre del hito tal como aparece en HITOS (build.py). 'Estación' cubre todas las del cable.
"""

INFO = {
    'Catedral Basílica': (
        'Templo',
        'Catedral neogótica levantada en concreto para resistir incendios y sismos. La diseñó el arquitecto '
        'francés Julien Polti; las obras empezaron en 1928 y se consagró en 1939. Su aguja central supera los '
        '100 m y es la iglesia más alta de Colombia. En el sismo de agosto de 2026 la torre principal colapsó '
        'en parte.',
        'Radio Nacional de Colombia; Forbes Argentina (ago. 2026)'),
    'Gobernación de Caldas': (
        'Edificio patrimonial',
        'Palacio de estilo republicano frente a la Plaza de Bolívar, sede del gobierno departamental. Se '
        'construyó en la segunda mitad de la década de 1920, tras los incendios que arrasaron el centro.',
        'Radio Nacional de Colombia; guías de patrimonio de Manizales'),
    'Plaza de Bolívar': (
        'Plaza',
        'Corazón del centro histórico, entre la Catedral y la Gobernación. Su escultura Bolívar Cóndor, del '
        'maestro Rodrigo Arenas Betancourt, se inauguró en 1991 y muestra al Libertador convertido en cóndor.',
        'Lonely Planet; Wanderlog'),
    'Monumento a los Colonizadores': (
        'Monumento',
        'Obra del artista manizaleño Luis Guillermo Vallejo, construida entre 1997 y 2002 en el alto de Chipre. '
        'Tiene unas 50 toneladas de bronce, en parte donado por los manizaleños en llaves y otros objetos, y '
        'rinde homenaje a la colonización antioqueña.',
        'Radio Nacional de Colombia; Lonely Planet'),
    'Torre al Cielo': (
        'Mirador',
        'Mirador de unos 30 m en el barrio Chipre, inaugurado en 2008 sobre un antiguo tanque de agua. Tiene '
        'una pasarela exterior (Sky Walk) con vista de 360° sobre la ciudad y los nevados.',
        'Blu Radio; Lonely Planet'),
    'Mall Plaza': (
        'Centro comercial',
        'Centro comercial abierto en 2018 sobre la Avenida Kevin Ángel, con más de 80.000 m² construidos.',
        'Perú Retail (ago. 2018)'),
    'Ecoparque Alcázares': (
        'Ecoparque',
        'Primer ecoparque urbano de Manizales, creado para proteger las laderas de Chipre y Alcázares. '
        'Ofrece senderos, recorridos guiados y avistamiento de aves; hace parte de la Red de Ecoparques.',
        'Boletín ambiental IDEA – U. Nacional sede Manizales'),
    'Ecoparque Los Yarumos': (
        'Ecoparque',
        'Ecoparque del oriente de la ciudad con senderos, mariposario, canopy, puente tibetano y caídas de '
        'agua. Hace parte de la Red de Ecoparques de Manizales.',
        'Alcaldía de Manizales (2023)'),
    'Bosque Popular El Prado': (
        'Parque',
        'Gran parque urbano de unas 53 hectáreas, con zonas verdes, senderos entre el bosque, aves y monos. '
        'Hace parte de la Red de Ecoparques de Manizales.',
        'Boletín ambiental IDEA – U. Nacional; Live the World'),
    'Plaza de Toros': (
        'Escenario',
        'Inaugurada el 23 de diciembre de 1951 y diseñada para unos 12.000 espectadores. Es escenario '
        'tradicional de la Feria de Manizales, en enero.',
        'Wikipedia'),
    'Estadio Palogrande': (
        'Estadio',
        'Casa del Once Caldas. El estadio actual se inauguró el 30 de julio de 1994 y, tras la remodelación '
        'para el Mundial Sub-20 de 2011, tiene capacidad para unas 32.000 personas.',
        'Wikipedia; StadiumDB'),
    'Torre de Herveo · El Cable': (
        'Monumento nacional',
        'Torre de madera del antiguo Cable Aéreo Manizales–Mariquita, terminado en 1922. Se hizo en madera '
        'porque el barco que traía la torre de acero desde Inglaterra fue hundido por un submarino alemán. '
        'Hoy es monumento nacional en el sector de El Cable.',
        'Wikipedia; Radio Nacional de Colombia'),
    'U. Nacional · Palogrande': (
        'Universidad',
        'La sede Manizales de la Universidad Nacional nació en 1948 con la Facultad de Ingeniería. Tiene '
        'tres campus: Palogrande, El Cable y La Nubia.',
        'Repositorio U. Nacional de Colombia'),
    'Recinto del Pensamiento': (
        'Parque',
        'Parque y centro de convenciones en el bosque de niebla, a las afueras de la ciudad. Tiene mariposario, '
        'huerto de plantas aromáticas, mirador de colibríes y un gran pabellón de guadua.',
        'Lonely Planet; Rough Guides'),
    'Nevado del Ruiz': (
        'Volcán (fuera de escala)',
        'Volcán de 5.321 msnm en la cordillera Central, entre Caldas y Tolima. Su erupción del 13 de '
        'noviembre de 1985 causó la tragedia de Armero.',
        'Servicio Geológico Colombiano (2024)'),
    'Estación': (
        'Cable Aéreo de Manizales',
        'Línea 1 (Fundadores–Cámbulos) desde 2009, Línea 2 (Cámbulos–Villamaría) desde 2013 y Línea 3 '
        '(Cámbulos–Fátima–Universidades–El Cable) desde septiembre de 2025.',
        'Wikipedia; Remontées mécaniques'),
}


def info(nombre):
    if nombre.startswith('Estación'):
        return INFO['Estación']
    return INFO.get(nombre, ('', '', ''))
