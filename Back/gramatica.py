import json


def cargar_plantilla(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _centro(box):
    return (box[0] + box[2] / 2, box[1] + box[3] / 2)


def _solapan(a, b):
    return not (a[0] + a[2] < b[0] or b[0] + b[2] < a[0] or a[1] + a[3] < b[1] or b[1] + b[3] < a[1])


def _iom(box_det, box_plant):
    ax, ay, aw, ah = box_det
    bx, by, bw, bh = box_plant
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    area_min = min(aw * ah, bw * bh)
    return inter / area_min if area_min > 0 else 0.0


def verificar_maquetacion(regiones, plantilla):
    reporte = {"valido": True, "elementos": [], "relaciones": [], "errores": []}

    for regla in plantilla["relaciones"]:
        det = regiones.get(regla["id"])
        if not det and regla["obligatorio"]:
            reporte["valido"] = False
            reporte["errores"].append(f"Falta elemento: {regla['id']}")
            continue
        if det:
            iom = _iom(det, regla["box"])
            ok = iom >= 0.5
            reporte["elementos"].append({"id": regla["id"], "ok": ok, "iom": round(iom, 2)})
            if not ok and regla["obligatorio"]:
                reporte["valido"] = False

    for r in plantilla.get("restricciones_relativas", []):
        a, b = regiones.get(r["a"]), regiones.get(r["b"])
        if not a or not b: continue

        ok = True
        if r["regla"] == "izquierda_de":
            ok = _centro(a)[0] < _centro(b)[0]
        elif r["regla"] == "arriba_de":
            ok = _centro(a)[1] < _centro(b)[1]
        elif r["regla"] == "no_solapa":
            ok = not _solapan(a, b)

        reporte["relaciones"].append({"regla": r["regla"], "ok": ok})
        if not ok: reporte["valido"] = False

    return reporte