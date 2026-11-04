import json

def cargar_plantilla(ruta="plantilla_uaemex.json") -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)

def _centro(box):
    x, y, w, h = box
    return (x + w / 2, y + h / 2)

def _solapan(a, b) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw < bx or bx + bw < ax or ay + ah < by or by + bh < ay)

def _iom(box_detectado, box_plantilla) -> float:
    """Intersection over Minimum: qué tanto del detectado cae dentro de la plantilla."""
    ax, ay, aw, ah = box_detectado
    bx, by, bw, bh = box_plantilla
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    area_min = min(aw * ah, bw * bh)
    return inter / area_min if area_min > 0 else 0.0

def verificar_maquetacion(regiones_detectadas: dict, plantilla: dict) -> dict:
    """
    regiones_detectadas: {id: [x,y,w,h]} normalizadas 0-1.
    Devuelve un reporte con las relaciones de la gramática que se cumplen/fallan.
    """
    reporte = {"valido": True, "elementos": [], "relaciones": [], "errores": []}
    tol = plantilla.get("tolerancia_posicion", 0.08)

    # 1) Verificar presencia y posición de cada elemento obligatorio
    for regla in plantilla["relaciones"]:
        eid = regla["id"]
        detectado = regiones_detectadas.get(eid)
        if detectado is None:
            if regla["obligatorio"]:
                reporte["valido"] = False
                reporte["errores"].append(f"Falta el elemento obligatorio '{eid}'")
                reporte["elementos"].append({"id": eid, "ok": False, "motivo": "no detectado"})
            continue

        iom = _iom(detectado, regla["box"])
        ok_pos = iom >= 0.5  # al menos 50% del área cae en la zona esperada
        # Además verificamos que el centro esté cerca del centro esperado
        cx_d, cy_d = _centro(detectado)
        cx_p, cy_p = _centro(regla["box"])
        dist = ((cx_d - cx_p) ** 2 + (cy_d - cy_p) ** 2) ** 0.5
        ok_centro = dist <= (tol + 0.15)  # margen relativo

        ok = ok_pos and ok_centro
        reporte["elementos"].append({
            "id": eid,
            "ok": ok,
            "iom": round(iom, 3),
            "distancia_centro": round(dist, 3),
        })
        if not ok:
            reporte["valido"] = False
            reporte["errores"].append(f"Elemento '{eid}' fuera de su zona legal (IoM={iom:.2f})")

    # 2) Verificar relaciones relativas entre elementos detectados
    for r in plantilla.get("restricciones_relativas", []):
        a = regiones_detectadas.get(r["a"])
        b = regiones_detectadas.get(r["b"])
        if not a or not b:
            continue
        ok = True
        motivo = "ok"
        if r["regla"] == "izquierda_de":
            ok = _centro(a)[0] < _centro(b)[0]
            motivo = "a debe estar a la izquierda de b"
        elif r["regla"] == "arriba_de":
            ok = _centro(a)[1] < _centro(b)[1]
            motivo = "a debe estar arriba de b"
        elif r["regla"] == "no_solapa":
            ok = not _solapan(a, b)
            motivo = "a y b no deben solaparse"
        reporte["relaciones"].append({"regla": r["regla"], "a": r["a"], "b": r["b"],
                                       "ok": ok, "motivo": motivo})
        if not ok:
            reporte["valido"] = False
            reporte["errores"].append(f"Relación '{r['regla']}' ({r['a']},{r['b']}) violada")

    return reporte