import re


class ParserClaveElectorINE:
    LIMPIAR = re.compile(r"[^A-Z0-9]")

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
        limpio = cls.LIMPIAR.sub("", texto_ocr.upper())

        if len(limpio) != 18:
            return {"valida": False, "error": f"Longitud incorrecta: {len(limpio)}"}

        apellidos = limpio[0:6]
        fecha = limpio[6:12]
        entidad = limpio[12:14]
        sexo = limpio[14]
        homoclave = limpio[15:18]

        # Corrección de errores OCR
        fecha_corregida = "".join('0' if c == 'O' else ('1' if c in 'IL' else c) for c in fecha)
        entidad_corregida = "".join(
            '0' if c == 'O' else ('1' if c in 'IL' else ('2' if c == 'Z' else ('5' if c == 'S' else c))) for c in
            entidad)
        sexo_corregido = 'H' if 'H' in sexo else ('M' if 'M' in sexo else 'H')

        if entidad_corregida not in cls.ENTIDADES_VALIDAS:
            return {"valida": False, "error": f"Entidad '{entidad_corregida}' no válida"}

        aa, mm, dd = fecha_corregida[0:2], fecha_corregida[2:4], fecha_corregida[4:6]
        if not (1 <= int(dd) <= 31 and 1 <= int(mm) <= 12):
            return {"valida": False, "error": f"Fecha inválida: {dd}/{mm}/{aa}"}

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