# parser_matricula.py
import re


class ParserMatriculaUAEMex:
    """
    Parser sintáctico para validar la matrícula de la UAEMéx.
    Gramática formal:
        MATRICULA -> ANIO PERIODO CONSECUTIVO
        ANIO      -> '20' DIGITO DIGITO
        PERIODO   -> '10' | '20'
        CONSECUTIVO -> DIGITO DIGITO DIGITO
    """

    # Gramática compilada con regex (equivalente a la BNF de arriba)
    GRAMATICA = re.compile(
        r"^(?P<anio>20[0-9]{2})(?P<periodo>10|20)(?P<consecutivo>[0-9]{3})$"
    )

    # Rango válido de años de ingreso (para evitar "199910345")
    ANIO_MIN = 2015
    ANIO_MAX = 2030

    @classmethod
    def parsear(cls, texto_ocr: str) -> dict:
        """
        Recibe el texto detectado por OCR y devuelve un AST sintáctico
        o un error si no cumple con la gramática.
        """
        # 1) Normalización léxica: quitar espacios, guiones y mayúsculas
        limpio = re.sub(r"[\s\-]", "", texto_ocr.upper())

        # 2) Regla léxica: solo dígitos
        if not limpio.isdigit():
            return {
                "valida": False,
                "error": "La matrícula contiene caracteres no numéricos",
                "texto_original": texto_ocr,
                "texto_normalizado": limpio,
            }

        # 3) Regla sintáctica: debe cumplir AAAA+PP+NNN
        match = cls.GRAMATICA.match(limpio)
        if not match:
            return {
                "valida": False,
                "error": "No cumple con el formato AAAA+PP+NNN",
                "texto_original": texto_ocr,
                "texto_normalizado": limpio,
            }

        # 4) Regla semántica: año dentro del rango válido
        anio = int(match.group("anio"))
        if not (cls.ANIO_MIN <= anio <= cls.ANIO_MAX):
            return {
                "valida": False,
                "error": f"Año de ingreso fuera de rango ({cls.ANIO_MIN}-{cls.ANIO_MAX}): {anio}",
                "texto_original": texto_ocr,
                "texto_normalizado": limpio,
            }

        # 5) Construcción del AST sintáctico (resultado exitoso)
        periodo = match.group("periodo")
        return {
            "valida": True,
            "matricula": limpio,
            "ast": {
                "anio_ingreso": anio,
                "periodo": "Enero-Junio" if periodo == "10" else "Agosto-Diciembre",
                "consecutivo": match.group("consecutivo"),
            },
        }