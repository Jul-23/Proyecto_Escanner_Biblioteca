# app.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import numpy as np
import pytesseract
import re
import datetime
from PIL import Image, ImageTk

# --- CONFIGURACIÓN DE TESSERACT ---
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from parser_matricula import ParserMatriculaUAEMex
from parser_ine import ParserClaveElectorINE
from gramatica import cargar_plantilla, verificar_maquetacion
from basededatos import LIBROS, ALUMNOS_ESTADO

PLANTILLAS = {
    "UAEMEX": cargar_plantilla("plantilla_uaemex.json"),
    "INE": cargar_plantilla("plantilla_ine.json"),
}


class AppBibliotecario(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Panel de Control - Préstamo Bibliotecario UAEMéx")
        self.geometry("1250x780")
        self.configure(bg="#181825")
        self.resizable(False, False)

        self.cap = None
        self.frame_actual = None
        self.camara_activa = False
        self.pausa_camara = False
        self.tipo_documento = tk.StringVar(value="UAEMEX")

        self.alumno_actual = None
        self.libro_seleccionado = tk.StringVar()
        self.libro_a_devolver = tk.StringVar()

        self._configurar_estilos()
        self._construir_ui()
        self._iniciar_camara()

    def _configurar_estilos(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground="#313244", background="#313244", foreground="#cdd6f4",
                        arrowcolor="#89b4fa")
        style.map('TCombobox', fieldbackground=[('readonly', '#313244')], selectbackground=[('readonly', '#313244')],
                  selectforeground=[('readonly', '#cdd6f4')])

    def _construir_ui(self):
        # --- HEADER ---
        header = tk.Frame(self, bg="#1e1e2e", height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header, text="💻 Terminal de Préstamos - Biblioteca UAEMéx",
                 font=("Segoe UI", 18, "bold"), fg="#89b4fa", bg="#1e1e2e").pack(side="left", padx=30, pady=15)

        selector = tk.Frame(header, bg="#1e1e2e")
        selector.pack(side="right", padx=30)
        tk.Label(selector, text="Tipo de ID:", font=("Segoe UI", 10, "bold"), fg="#a6adc8", bg="#1e1e2e").pack(
            side="left", padx=5)
        tk.Radiobutton(selector, text="UAEMéx", variable=self.tipo_documento, value="UAEMEX",
                       font=("Segoe UI", 10, "bold"), fg="#cdd6f4", bg="#1e1e2e", selectcolor="#1e1e2e",
                       activebackground="#1e1e2e", activeforeground="#89b4fa").pack(side="left", padx=5)
        tk.Radiobutton(selector, text="INE", variable=self.tipo_documento, value="INE",
                       font=("Segoe UI", 10, "bold"), fg="#cdd6f4", bg="#1e1e2e", selectcolor="#1e1e2e",
                       activebackground="#1e1e2e", activeforeground="#89b4fa").pack(side="left", padx=5)

        # --- CONTENEDOR PRINCIPAL ---
        main = tk.Frame(self, bg="#181825")
        main.pack(fill="both", expand=True, padx=20, pady=20)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.columnconfigure(2, weight=1)

        # 1. COLUMNA IZQUIERDA: CÁMARA
        frame_cam = tk.Frame(main, bg="#1e1e2e", highlightthickness=1, highlightbackground="#313244")
        frame_cam.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        tk.Label(frame_cam, text="📷 Lector de Credenciales", font=("Segoe UI", 12, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(pady=10)

        self.lbl_video = tk.Label(frame_cam, bg="#000", width=400, height=300)
        self.lbl_video.pack(padx=15, pady=10)

        btn_frame = tk.Frame(frame_cam, bg="#1e1e2e")
        btn_frame.pack(fill="x", padx=15, pady=10)

        self.btn_escanear = tk.Button(btn_frame, text="🔍 Escanear Credencial", font=("Segoe UI", 11, "bold"),
                                      bg="#89b4fa", fg="#11111b", activebackground="#b4befe", relief="flat",
                                      cursor="hand2",
                                      command=self.escanear)
        self.btn_escanear.pack(fill="x", pady=5)

        tk.Button(btn_frame, text="📂 Cargar Imagen desde Archivo", font=("Segoe UI", 10),
                  bg="#45475a", fg="#cdd6f4", activebackground="#585b70", relief="flat", cursor="hand2",
                  command=self.cargar_imagen).pack(fill="x", pady=5)

        # 2. COLUMNA CENTRAL: FICHA DEL ALUMNO
        self.frame_alumno = tk.Frame(main, bg="#1e1e2e", highlightthickness=1, highlightbackground="#313244")
        self.frame_alumno.grid(row=0, column=1, padx=10, sticky="nsew")

        tk.Label(self.frame_alumno, text="🪪 Ficha del Alumno", font=("Segoe UI", 12, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(pady=10)

        self.lbl_nombre = tk.Label(self.frame_alumno, text="Esperando escaneo...", font=("Segoe UI", 14, "bold"),
                                   fg="#a6adc8", bg="#1e1e2e")
        self.lbl_nombre.pack(pady=5)

        self.lbl_id = tk.Label(self.frame_alumno, text="ID: ---", font=("Segoe UI", 11), fg="#89b4fa", bg="#1e1e2e")
        self.lbl_id.pack()

        self.lbl_tipo = tk.Label(self.frame_alumno, text="Documento: ---", font=("Segoe UI", 10), fg="#a6adc8",
                                 bg="#1e1e2e")
        self.lbl_tipo.pack()

        self.lbl_estado = tk.Label(self.frame_alumno, text="ESTADO: DESCONOCIDO", font=("Segoe UI", 12, "bold"),
                                   fg="#6c7086", bg="#1e1e2e")
        self.lbl_estado.pack(pady=15)

        self.txt_alertas = tk.Text(self.frame_alumno, wrap="word", font=("Segoe UI", 10), bg="#181825", fg="#f9e2af",
                                   height=8, bd=0, padx=10, pady=10, state="disabled")
        self.txt_alertas.pack(fill="both", expand=True, padx=15, pady=10)

        # 3. COLUMNA DERECHA: ACCIONES (PRÉSTAMO / DEVOLUCIÓN)
        self.frame_acciones = tk.Frame(main, bg="#1e1e2e", highlightthickness=1, highlightbackground="#313244")
        self.frame_acciones.grid(row=0, column=2, padx=(10, 0), sticky="nsew")

        tk.Label(self.frame_acciones, text="⚙️ Acciones Disponibles", font=("Segoe UI", 12, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(pady=10)

        self.lbl_instruccion = tk.Label(self.frame_acciones, text="Escanee una credencial para habilitar acciones.",
                                        font=("Segoe UI", 10, "italic"), fg="#6c7086", bg="#1e1e2e", wraplength=200)
        self.lbl_instruccion.pack(pady=10)

        # --- PANEL DE PRÉSTAMO (Oculto por defecto) ---
        self.frame_prestamo = tk.Frame(self.frame_acciones, bg="#1e1e2e")

        tk.Label(self.frame_prestamo, text="Seleccione libro para PRESTAR:", font=("Segoe UI", 10, "bold"),
                 fg="#a6e3a1", bg="#1e1e2e").pack(anchor="w", padx=15, pady=(5, 0))
        self.combo_libros = ttk.Combobox(self.frame_prestamo, textvariable=self.libro_seleccionado, state="readonly",
                                         font=("Segoe UI", 10))
        self.combo_libros.pack(fill="x", padx=15, pady=5)

        self.btn_prestar = tk.Button(self.frame_prestamo, text="📤 Registrar Préstamo", font=("Segoe UI", 11, "bold"),
                                     bg="#a6e3a1", fg="#11111b", activebackground="#94e2d5", relief="flat",
                                     command=self.registrar_prestamo)
        self.btn_prestar.pack(fill="x", padx=15, pady=15)

        # --- PANEL DE DEVOLUCIÓN (Oculto por defecto) ---
        self.frame_devolucion = tk.Frame(self.frame_acciones, bg="#1e1e2e")

        tk.Label(self.frame_devolucion, text="Seleccione libro a DEVOLVER:", font=("Segoe UI", 10, "bold"),
                 fg="#f38ba8", bg="#1e1e2e").pack(anchor="w", padx=15, pady=(5, 0))
        self.combo_devolver = ttk.Combobox(self.frame_devolucion, textvariable=self.libro_a_devolver, state="readonly",
                                           font=("Segoe UI", 10))
        self.combo_devolver.pack(fill="x", padx=15, pady=5)

        self.btn_devolver = tk.Button(self.frame_devolucion, text="📥 Registrar Devolución",
                                      font=("Segoe UI", 11, "bold"),
                                      bg="#f38ba8", fg="#11111b", activebackground="#eba0ac", relief="flat",
                                      command=self.registrar_devolucion)
        self.btn_devolver.pack(fill="x", padx=15, pady=15)

        # --- CONSOLA DE LOGS ---
        self.frame_logs = tk.Frame(self, bg="#11111b", height=120)
        self.frame_logs.pack(fill="x", side="bottom")
        self.frame_logs.pack_propagate(False)

        self.txt_logs = tk.Text(self.frame_logs, bg="#11111b", fg="#a6adc8", font=("Consolas", 9), bd=0, padx=15,
                                pady=10, state="disabled")
        self.txt_logs.pack(fill="both", expand=True)
        self.txt_logs.tag_configure("ok", foreground="#a6e3a1")
        self.txt_logs.tag_configure("error", foreground="#f38ba8")
        self.txt_logs.tag_configure("info", foreground="#89b4fa")

        self._log("Sistema iniciado. Cámara en vivo.", "info")

    def _iniciar_camara(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self._log("Error: No se pudo abrir la cámara.", "error")
            return
        self.camara_activa = True
        self._actualizar_frame()

    def _actualizar_frame(self):
        if not self.camara_activa:
            return
        if not self.pausa_camara:
            ret, frame = self.cap.read()
            if ret:
                self.frame_actual = frame.copy()
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(rgb).resize((400, 300))
                self.img_tk = ImageTk.PhotoImage(img_pil)
                self.lbl_video.config(image=self.img_tk)
        self.after(30, self._actualizar_frame)

    def escanear(self):
        if self.frame_actual is None:
            return
        self._log("Capturando imagen...", "info")
        self.update()
        self.pausa_camara = True
        try:
            self._procesar(self.frame_actual.copy())
        except Exception as e:
            self._log(f"Error interno: {str(e)}", "error")
            self.pausa_camara = False

    def cargar_imagen(self):
        ruta = filedialog.askopenfilename(title="Selecciona imagen", filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
        if not ruta:
            return
        img = cv2.imread(ruta)
        if img is not None:
            self.pausa_camara = True
            self._procesar(img)

    def _procesar(self, img):
        tipo = self.tipo_documento.get()
        H, W = img.shape[:2]
        regiones = {}
        texto_completo = ""

        # 1. Procesamiento OCR
        gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gris = cv2.bilateralFilter(gris, 9, 75, 75)
        umbral = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)

        if tipo == "UAEMEX":
            ocr_data = pytesseract.image_to_data(umbral, lang="spa", output_type=pytesseract.Output.DICT)
            textos, boxes = [], []
            for i, txt in enumerate(ocr_data["text"]):
                if txt.strip() and int(ocr_data["conf"][i]) > 60:
                    textos.append(txt)
                    boxes.append([ocr_data["left"][i], ocr_data["top"][i], ocr_data["width"][i], ocr_data["height"][i]])
            texto_completo = " ".join(textos)

            if boxes:
                x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
                x1, y1 = max(b[0] + b[2] for b in boxes), max(b[1] + b[3] for b in boxes)
                regiones["texto_nombre"] = [x0 / W, y0 / H, (x1 - x0) / W, (y1 - y0) / H * 0.45]
                regiones["matricula"] = [x0 / W, (y0 + (y1 - y0) * 0.55) / H, (x1 - x0) / W, (y1 - y0) / H * 0.45]
        else:
            texto_completo = pytesseract.image_to_string(umbral, lang="spa", config="--psm 6")
            regiones["escudo"] = [0.03, 0.05, 0.20, 0.20]
            regiones["foto"] = [0.08, 0.25, 0.20, 0.55]
            regiones["nombre"] = [0.32, 0.28, 0.35, 0.18]
            regiones["clave_elector"] = [0.32, 0.70, 0.50, 0.08]

        # 2. Validaciones
        plantilla = PLANTILLAS[tipo]
        reporte_maqueta = verificar_maquetacion(regiones, plantilla)

        if tipo == "UAEMEX":
            m = re.search(r"\b\d{9}\b", texto_completo)
            reporte_doc = (ParserMatriculaUAEMex.parsear(m.group(0)) if m else {"valida": False,
                                                                                "error": "No se detectó matrícula"})
        else:
            texto_limpio = re.sub(r"[^A-Z0-9]", "", texto_completo.upper())
            reporte_doc = {"valida": False, "error": "No se encontró clave válida"}
            for i in range(len(texto_limpio) - 17):
                posible_clave = texto_limpio[i:i + 18]
                if not (posible_clave[0:6].isalpha() and posible_clave[14] in ['H', 'M']):
                    continue
                resultado = ParserClaveElectorINE.parsear(posible_clave)
                if resultado["valida"]:
                    reporte_doc = resultado
                    break

        # 3. Evaluar Alumno y Actualizar UI
        if reporte_maqueta["valido"] and reporte_doc["valida"]:
            if tipo == "UAEMEX":
                identificador = reporte_doc["matricula"]
            else:
                identificador = reporte_doc["clave"]

            self._evaluar_alumno(identificador, tipo)
        else:
            self._limpiar_ficha()
            self.lbl_nombre.config(text="Documento No Válido", fg="#f38ba8")
            self.lbl_estado.config(text="ESTADO: ERROR", fg="#f38ba8")
            self._log("Error de lectura: Documento no válido.", "error")
            self._mostrar_mensaje_alerta(
                f"Error: {reporte_doc.get('error', 'No se pudo leer')}\n\nIntente de nuevo con mejor iluminación.",
                "#f38ba8")

        # Mostrar imagen procesada
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(rgb).resize((400, 300))
        self.img_anotada = ImageTk.PhotoImage(img_pil)
        self.lbl_video.config(image=self.img_anotada)

    def _evaluar_alumno(self, identificador, tipo):
        """Evalúa el estado del alumno y muestra los paneles correspondientes."""
        self._limpiar_ficha(keep_camera_paused=True)

        estado = ALUMNOS_ESTADO.get(identificador)
        if not estado:
            estado = {"nombre": "Alumno Registrado (Nuevo)", "libros_prestados": [], "multas": []}
            ALUMNOS_ESTADO[identificador] = estado

        self.alumno_actual = {"id": identificador, "nombre": estado["nombre"], "tipo": tipo}

        # Actualizar ficha visual
        self.lbl_nombre.config(text=estado["nombre"], fg="#cdd6f4")
        self.lbl_id.config(text=f"ID: {identificador}")
        doc_txt = "Credencial UAEMéx" if tipo == "UAEMEX" else "INE (Credencial para Votar)"
        self.lbl_tipo.config(text=f"Documento: {doc_txt}")

        tiene_libros = len(estado["libros_prestados"]) > 0
        tiene_multas = len(estado["multas"]) > 0

        if tiene_libros or tiene_multas:
            # TIENE ADEUDOS
            self.lbl_estado.config(text="ESTADO: CON ADEUDOS", fg="#f38ba8")
            self._log(f"Alumno {estado['nombre']} tiene adeudos.", "error")

            txt = "El alumno presenta los siguientes adeudos:\n\n"
            for lib in estado["libros_prestados"]:
                txt += f"📕 Libro sin devolver: {lib['titulo']}\n   (Vence: {lib['vencimiento']})\n\n"
            for multa in estado["multas"]:
                txt += f"💰 Multa: ${multa['monto']} - {multa['motivo']}\n"
            self._mostrar_mensaje_alerta(txt, "#f9e2af")

            if tiene_libros:
                # Habilitar panel de devolución
                self.lbl_instruccion.config(text="Puede registrar la devolución del libro.", fg="#89b4fa")
                self.frame_devolucion.pack(fill="x", pady=5)
                self.combo_devolver['values'] = [lib['titulo'] for lib in estado["libros_prestados"]]
                self.combo_devolver.current(0)
            else:
                self.lbl_instruccion.config(text="No hay libros que devolver. Solo multas.", fg="#f38ba8")
        else:
            # ESTÁ LIMPIO
            self.lbl_estado.config(text="ESTADO: SIN ADEUDOS", fg="#a6e3a1")
            self._log(f"Alumno {estado['nombre']} verificado. Listo.", "ok")
            self._mostrar_mensaje_alerta(
                "El alumno no tiene libros pendientes ni multas.\n\nPuede registrar un nuevo préstamo.", "#a6e3a1")

            # Habilitar panel de préstamo
            self.lbl_instruccion.config(text="Seleccione el libro a prestar:", fg="#89b4fa")
            self.frame_prestamo.pack(fill="x", pady=5)
            self.combo_libros['values'] = list(LIBROS.values())
            self.combo_libros.current(0)

    def registrar_prestamo(self):
        if not self.alumno_actual or not self.libro_seleccionado.get():
            return

        libro = self.libro_seleccionado.get()
        id_usuario = self.alumno_actual['id']
        fecha_devolucion = (datetime.datetime.now() + datetime.timedelta(days=15)).strftime("%d/%m/%Y")

        ALUMNOS_ESTADO[id_usuario]["libros_prestados"].append({
            "titulo": libro,
            "vencimiento": (datetime.datetime.now() + datetime.timedelta(days=15)).strftime("%Y-%m-%d")
        })

        self._log(f"Préstamo: {self.alumno_actual['nombre']} -> {libro}", "ok")
        messagebox.showinfo("Préstamo Exitoso",
                            f"Se registró el préstamo.\n\nLibro: {libro}\nDevolución: {fecha_devolucion}")

        # Actualizamos la ficha (ahora el alumno tendrá un libro pendiente)
        self._evaluar_alumno(id_usuario, self.alumno_actual['tipo'])

    def registrar_devolucion(self):
        if not self.alumno_actual or not self.libro_a_devolver.get():
            return

        libro_devuelto = self.libro_a_devolver.get()
        id_usuario = self.alumno_actual['id']

        # Buscar el libro y eliminarlo de la lista de prestados
        nuevos_prestamos = [lib for lib in ALUMNOS_ESTADO[id_usuario]["libros_prestados"] if
                            lib["titulo"] != libro_devuelto]
        ALUMNOS_ESTADO[id_usuario]["libros_prestados"] = nuevos_prestamos

        self._log(f"Devolución: {self.alumno_actual['nombre']} devolvió {libro_devuelto}", "ok")
        messagebox.showinfo("Devolución Exitosa", f"Se registró la devolución de:\n{libro_devuelto}")

        # Refrescamos la ficha del alumno. Si ya no tiene libros ni multas, se pondrá en verde.
        self._evaluar_alumno(id_usuario, self.alumno_actual['tipo'])

    def _limpiar_ficha(self, keep_camera_paused=False):
        self.alumno_actual = None
        self.lbl_nombre.config(text="Esperando escaneo...", fg="#a6adc8")
        self.lbl_id.config(text="ID: ---")
        self.lbl_tipo.config(text="Documento: ---")
        self.lbl_estado.config(text="ESTADO: DESCONOCIDO", fg="#6c7086")

        self._mostrar_mensaje_alerta("", "#f9e2af")

        self.lbl_instruccion.config(text="Escanee una credencial para habilitar acciones.", fg="#6c7086")
        self.frame_prestamo.pack_forget()
        self.frame_devolucion.pack_forget()

        self.combo_libros.set("")
        self.combo_devolver.set("")

        self.pausa_camara = keep_camera_paused

    def _mostrar_mensaje_alerta(self, texto, color):
        self.txt_alertas.config(state="normal")
        self.txt_alertas.delete("1.0", "end")
        self.txt_alertas.insert("end", texto)
        self.txt_alertas.config(state="disabled", fg=color)

    def _log(self, mensaje, tag="info"):
        hora = datetime.datetime.now().strftime("%H:%M:%S")
        self.txt_logs.config(state="normal")
        self.txt_logs.insert("end", f"[{hora}] {mensaje}\n", tag)
        self.txt_logs.see("end")
        self.txt_logs.config(state="disabled")

    def on_close(self):
        self.camara_activa = False
        if self.cap:
            self.cap.release()
        self.destroy()


if __name__ == "__main__":
    app = AppBibliotecario()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()