# base_datos.py

LIBROS = {
    "L001": "Cálculo Diferencial e Integral - Purcell",
    "L002": "Introducción a los Algoritmos - Cormen",
    "L003": "Inteligencia Artificial - Russell & Norvig",
    "L004": "Estructuras de Datos en Python - Goodrich",
    "L005": "Física Universitaria - Sears & Zemansky"
}

ALUMNOS_ESTADO = {
    # Alumno Limpio (María)
    "202220567": {
        "nombre": "María López",
        "libros_prestados": [],
        "multas": []
    },
    # Alumno con Libro Prestado (Juan) - Úsalo para probar la Devolución
    "202110345": {
        "nombre": "Juan Pérez",
        "libros_prestados": [{"titulo": "Física Universitaria - Sears & Zemansky", "vencimiento": "2026-10-25"}],
        "multas": []
    },
    # Alumno con Multa (Carlos)
    "202310789": {
        "nombre": "Carlos Ruiz",
        "libros_prestados": [],
        "multas": [{"monto": 150.0, "motivo": "Libro dañado"}]
    },
    # Usuario INE (Julio)
    "SNVRJL03062509H200": {
        "nombre": "Julio Ángel Sánchez Vera",
        "libros_prestados": [],
        "multas": []
    }
}