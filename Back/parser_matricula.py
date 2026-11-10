import re


class ParserMatriculaUAEMex:
    # Precompilamos los patrones para mayor velocidad
    GRAMATICA_9 = re.compile(r"^(?P<anio>20[0-9]{2})(?P<periodo>10|20)(?P<consecutivo>[0-9]{3})$")
    GRAMATICA_7 = re.compile(r"^(?P<anio>[0-9]{2})(?P<consecutivo>[0-9]{5})$")
    LIMPIAR = re.compile(r"[\s\-]")

    ANIO_MIN = 2015
    ANIO_MAX = 2030

    @classmethod
    def parsear(cls, texto_ocr: str) -> dict:
        limpio = cls.LIMPIAR.sub("", texto_ocr.upper())

        if not limpio.isdigit():
            return {"valida": False, "error": "La matrícula contiene caracteres no numéricos"}

        match9 = cls.GRAMATICA_9.match(limpio)
        if match9:
            anio = int(match9.group("anio"))
            if not (cls.ANIO_MIN <= anio <= cls.ANIO_MAX):
                return {"valida": False, "error": f"Año fuera de rango: {anio}"}
            return {
                "valida": True,
                "matricula": limpio,
                "ast": {
                    "anio_ingreso": anio,
                    "periodo": "Enero-Junio" if match9.group("periodo") == "10" else "Agosto-Diciembre",
                    "consecutivo": match9.group("consecutivo"),
                },
            }

        match7 = cls.GRAMATICA_7.match(limpio)
        if match7:
            anio_completo = 2000 + int(match7.group("anio"))
            if not (cls.ANIO_MIN <= anio_completo <= cls.ANIO_MAX):
                return {"valida": False, "error": f"Año fuera de rango: {anio_completo}"}
            return {
                "valida": True,
                "matricula": limpio,
                "ast": {
                    "anio_ingreso": anio_completo,
                    "periodo": "No especificado",
                    "consecutivo": match7.group("consecutivo"),
                },
            }

        return {"valida": False, "error": "No cumple con ningún formato válido"}