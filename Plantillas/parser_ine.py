# parser_ine.py
import re

class ParserClaveElectorINE:
    ENTIDADES_VALIDAS = {
        "01": "Aguascalientes", "02": "Baja California", "03": "Baja California Sur",
        "04": "Campeche", "05": "Coahuila", "06": "Colima", "07": "Chiapas",
        "08": "Chihuahua", "09": "Ciudad de México", "10": "Durango",
        "11": "Guanajuato", "12": "Guerrero", "13": "Hidalgo", "14": "Jalisco",
        "15": "Estado de México", "16": "Michoacán", "17": "Morelos",
        "18": "Nayarit", "19": "Nuevo León", "20": "Oaxaca", "21": "Puebla",
        "22": "Querétaro", "23": "Quintana Roo", "24": "San Luis Potosí",
        "25": "Sinaloa", "26": "Sonora", "27": "Tabasco", "28": "Tamaulipas",
        "29": "Tlaxcala", "30": "Veracruz", "31": "Yucatán", "32": "Zacatecas",
        "33": "Nacido en el Extranjero"
    }

    @classmethod
    def parsear(cls, texto_ocr: str) -> dict:
        # 1. Normalización (quitamos todo lo que no sea letra o número)
        limpio = re.sub(r"[^A-Z0-9]", "", texto_ocr.upper())

        # 2. Verificamos longitud
        if len(limpio) != 18:
            return {
                "valida": False,
                "error": f"La clave debe tener 18 caracteres (recibidos: {len(limpio)}). Texto leído: {limpio}",
                "texto_normalizado": limpio,
            }

        # 3. Extraemos por posiciones (Slicing)
        apellidos = limpio[0:6]
        fecha = limpio[6:12]
        entidad = limpio[12:14]
        sexo = limpio[14]
        homoclave = limpio[15:18]

        # 4. Corrección de errores del OCR en la Fecha (deben ser números)
        fecha_corregida = ""
        for c in fecha:
            if c == 'O': fecha_corregida += '0'
            elif c in 'IL': fecha_corregida += '1'
            elif c.isdigit(): fecha_corregida += c
            else: fecha_corregida += '0' # Fallback por si el OCR leyó una letra rara

        # 5. Corrección de errores del OCR en la Entidad (deben ser números)
        entidad_corregida = ""
        for c in entidad:
            if c == 'O':
                entidad_corregida += '0'
            elif c in 'IL':
                entidad_corregida += '1'
            elif c == 'Z':
                entidad_corregida += '2'
            elif c == 'S':
                entidad_corregida += '5'
            elif c.isdigit():
                entidad_corregida += c
            else:
                entidad_corregida += '0'

        # 6. Corrección del Sexo
        if 'H' in sexo: sexo_corregido = 'H'
        elif 'M' in sexo: sexo_corregido = 'M'
        else: sexo_corregido = 'H' # Por defecto

        # 7. Validación Semántica
        if entidad_corregida not in cls.ENTIDADES_VALIDAS:
            return {
                "valida": False,
                "error": f"Código de entidad '{entidad_corregida}' no válido. Clave leída: {limpio}",
                "texto_normalizado": limpio,
            }

        aa, mm, dd = fecha_corregida[0:2], fecha_corregida[2:4], fecha_corregida[4:6]
        try:
            dia, mes = int(dd), int(mm)
            if not (1 <= dia <= 31 and 1 <= mes <= 12):
                raise ValueError
        except ValueError:
            return {
                "valida": False,
                "error": f"Fecha de nacimiento inválida: {dd}/{mm}/{aa}. Clave leída: {limpio}",
                "texto_normalizado": limpio,
            }

        # 8. Éxito
        return {
            "valida": True,
            "clave": limpio,
            "ast": {
                "apellidos_nombre": apellidos,
                "fecha_nacimiento": f"{dd}/{mm}/20{aa}",
                "entidad": cls.ENTIDADES_VALIDAS[entidad_corregida],
                "sexo": "Hombre" if sexo_corregido == "H" else "Mujer",
                "homoclave": homoclave,
            },
        }