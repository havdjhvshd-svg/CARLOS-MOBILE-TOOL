from flask import Flask, render_template, jsonify, request
from pathlib import Path
from datetime import datetime, timezone
import json
import threading
import time
import uuid

app = Flask(__name__)

DATOS_DIR = Path.home() / "CARLOS_MOBILE_TOOL" / "data"
DATOS_FILE = DATOS_DIR / "estadisticas.json"

LOCK = threading.Lock()
ACTIVOS_SEGUNDOS = 60


def cargar_datos():
    DATOS_DIR.mkdir(parents=True, exist_ok=True)

    if not DATOS_FILE.exists():
        return {
            "total_visitas": 0,
            "visitantes": {}
        }

    try:
        return json.loads(DATOS_FILE.read_text())
    except Exception:
        return {
            "total_visitas": 0,
            "visitantes": {}
        }


def guardar_datos(datos):
    DATOS_DIR.mkdir(parents=True, exist_ok=True)
    DATOS_FILE.write_text(
        json.dumps(datos, indent=2, ensure_ascii=False)
    )


@app.route("/")
def inicio():
    with LOCK:
        datos = cargar_datos()
        datos["total_visitas"] += 1
        guardar_datos(datos)

    return render_template("interfaz_nueva.html")


@app.route("/api/ping", methods=["POST"])
def ping():
    try:
        datos_recibidos = request.get_json(silent=True) or {}
        visitante_id = str(datos_recibidos.get("visitor_id", "")).strip()

        if not visitante_id:
            visitante_id = str(uuid.uuid4())

        ahora = time.time()

        with LOCK:
            datos = cargar_datos()

            datos.setdefault("total_visitas", 0)
            datos.setdefault("visitantes", {})

            datos["visitantes"][visitante_id] = {
                "ultimo_acceso": ahora,
                "fecha": datetime.now(timezone.utc).isoformat()
            }

            guardar_datos(datos)

        return jsonify({
            "ok": True,
            "visitor_id": visitante_id
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.route("/api/estadisticas")
def estadisticas():
    try:
        ahora = time.time()

        with LOCK:
            datos = cargar_datos()

            visitantes = datos.get("visitantes", {})

            activos = sum(
                1
                for info in visitantes.values()
                if ahora - float(info.get("ultimo_acceso", 0)) <= ACTIVOS_SEGUNDOS
            )

            resultado = {
                "total_visitas": datos.get("total_visitas", 0),
                "visitantes_unicos": len(visitantes),
                "activos_ahora": activos
            }

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
