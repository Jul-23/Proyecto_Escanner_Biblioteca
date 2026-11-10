# app.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import numpy as np
import pytesseract
import re
import datetime
import threading
from PIL import Image, ImageTk
import rutas

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from parser_matricula import ParserMatriculaUAEMex
from parser_ine import ParserClaveElectorINE
from gramatica import cargar_plantilla, verificar_maquetacion
from basededatos import BibliotecaDB

PLANTILLAS = {
    "UAEMEX": cargar_plantilla(rutas.obtener_ruta_recurso("plantilla_uaemex.json")),
    "INE": cargar_plantilla(rutas.obtener_ruta_recurso("plantilla_ine.json")),
}

# --- PALETA DE COLORES ---
UAEM_GREEN = "#005A3C"
UAEM_GOLD = "#F2A900"
DANGER_RED = "#D32F2F"

# MODO OSCURO
DARK_BG_MAIN = "#121212"
DARK_BG_PANEL = "#1E1E1E"
DARK_BORDER = "#333333"
DARK_TEXT_PRIMARY = "#FFFFFF"
DARK_TEXT_SECONDARY = "#A0A0A0"
DARK_BTN_HOVER = "#008A5C"

# MODO CLARO
LIGHT_BG_MAIN = "#F3F4F6"
LIGHT_BG_PANEL = "#FFFFFF"
LIGHT_BORDER = "#D1D5DB"
LIGHT_TEXT_PRIMARY = "#111827"
LIGHT_TEXT_SECONDARY = "#4B5563"
LIGHT_BTN_HOVER = "#007A52"


class SplashScreen(tk.Toplevel):
    def __init__(self, parent, is_dark):
        super().__init__(parent)
        self.geometry("500x300")
        self.overrideredirect(True)

        bg_color = DARK_BG_MAIN if is_dark else LIGHT_BG_MAIN
        text_color = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY

        self.configure(bg=bg_color)

        self.update_idletasks()
        width, height = 500, 300
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        tk.Label(self, text="Universidad Autónoma del Estado de México", font=("Segoe UI", 12), fg=text_color,
                 bg=bg_color).pack(pady=(40, 10))
        tk.Label(self, text="SISTEMA DE PRÉSTAMOS", font=("Segoe UI", 24, "bold"), fg=UAEM_GOLD, bg=bg_color).pack()
        tk.Label(self, text="Cargando módulos...", font=("Segoe UI", 10), fg=text_color, bg=bg_color).pack(pady=20)

        self.progress = ttk.Progressbar(self, orient="horizontal", length=300, mode="indeterminate")
        self.progress.pack(pady=10)
        self.progress.start(10)


class AppBibliotecario(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Préstamos - Biblioteca UAEMéx")
        self.geometry("1350x800")
        self.state('zoomed')

        self.is_dark_mode = True  # <-- INICIA EN MODO OSCURO
        self.cap = None
        self.frame_actual = None
        self.camara_activa = False
        self.pausa_camara = False
        self.procesando_ocr = False

        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0

        self.tipo_documento = tk.StringVar(value="UAEMEX")
        self.alumno_actual = None
        self.id_credencial_actual = None
        self.libro_seleccionado = tk.StringVar()
        self.libro_a_devolver = tk.StringVar()

        self.db = BibliotecaDB()
        self._configurar_estilos()
        self._construir_ui()
        threading.Thread(target=self._iniciar_camara, daemon=True).start()

        # Atajos
        self.bind("<Return>", lambda e: self.escanear())
        self.bind("<Escape>", lambda e: self._limpiar_ficha(keep_camera_paused=False))
        self.bind("<F11>", lambda e: self.attributes('-fullscreen', not self.attributes('-fullscreen')))

    def toggle_theme(self):
        """Cambia entre modo oscuro y claro reconstruyendo la UI"""
        self.is_dark_mode = not self.is_dark_mode

        # Pausar la cámara temporalmente para evitar errores al destruir el label
        self.pausa_camara = True

        # Destruir todos los widgets actuales
        for widget in self.winfo_children():
            widget.destroy()

        # Reconstruir todo con el nuevo tema
        self._configurar_estilos()
        self._construir_ui()

        # Reanudar cámara
        self.pausa_camara = False
        self._log(f"Modo {'Oscuro' if self.is_dark_mode else 'Claro'} activado.", "info")

    def _configurar_estilos(self):
        style = ttk.Style()
        style.theme_use('clam')

        bg_main = DARK_BG_MAIN if self.is_dark_mode else LIGHT_BG_MAIN
        bg_panel = DARK_BG_PANEL if self.is_dark_mode else LIGHT_BG_PANEL
        text_primary = DARK_TEXT_PRIMARY if self.is_dark_mode else LIGHT_TEXT_PRIMARY
        border = DARK_BORDER if self.is_dark_mode else LIGHT_BORDER

        style.configure("TCombobox", fieldbackground=bg_main, background=bg_panel, foreground=text_primary,
                        arrowcolor=UAEM_GOLD, bordercolor=border, lightcolor=border, darkcolor=border)
        style.map('TCombobox', fieldbackground=[('readonly', bg_main)], selectbackground=[('readonly', bg_main)],
                  selectforeground=[('readonly', text_primary)])

    def _construir_ui(self):
        # Variables de color según el tema actual
        bg_main = DARK_BG_MAIN if self.is_dark_mode else LIGHT_BG_MAIN
        bg_panel = DARK_BG_PANEL if self.is_dark_mode else LIGHT_BG_PANEL
        border = DARK_BORDER if self.is_dark_mode else LIGHT_BORDER
        text_primary = DARK_TEXT_PRIMARY if self.is_dark_mode else LIGHT_TEXT_PRIMARY
        text_secondary = DARK_TEXT_SECONDARY if self.is_dark_mode else LIGHT_TEXT_SECONDARY
        btn_hover = DARK_BTN_HOVER if self.is_dark_mode else LIGHT_BTN_HOVER

        self.configure(bg=bg_main)

        # --- HEADER ---
        self.header_frame = tk.Frame(self, bg=UAEM_GREEN, height=80)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        tk.Label(self.header_frame, text="UAEMéx | Sistema de Préstamos", font=("Segoe UI", 22, "bold"), fg=UAEM_GOLD,
                 bg=UAEM_GREEN).pack(side="left", padx=30, pady=20)

        # Botones del Header (Historial y Tema)
        btn_header_frame = tk.Frame(self.header_frame, bg=UAEM_GREEN)
        btn_header_frame.pack(side="right", padx=20)

        # Botón Modo Oscuro/Claro
        icon_theme = "☀️ Modo Claro" if self.is_dark_mode else "🌙 Modo Oscuro"
        tk.Button(btn_header_frame, text=icon_theme, font=("Segoe UI", 10, "bold"), bg=bg_panel, fg=text_primary,
                  activebackground=border, relief="flat", cursor="hand2", command=self.toggle_theme).pack(side="right",
                                                                                                          padx=10)

        # Botón Historial
        tk.Button(btn_header_frame, text="📋 Historial del Día", font=("Segoe UI", 10, "bold"), bg=bg_panel,
                  fg=text_primary, activebackground=border, relief="flat", cursor="hand2",
                  command=self.abrir_historial).pack(side="right", padx=10)

        # Selector de Documento
        selector = tk.Frame(self.header_frame, bg=UAEM_GREEN)
        selector.pack(side="right", padx=20)
        tk.Label(selector, text="TIPO DE ID:", font=("Segoe UI", 9, "bold"), fg=DARK_TEXT_PRIMARY, bg=UAEM_GREEN).pack(
            side="left", padx=(0, 5))

        rb_style = {"font": ("Segoe UI", 10, "bold"), "bg": UAEM_GREEN, "fg": DARK_TEXT_PRIMARY,
                    "selectcolor": UAEM_GREEN, "activebackground": UAEM_GREEN, "activeforeground": UAEM_GOLD,
                    "cursor": "hand2"}
        tk.Radiobutton(selector, text="UAEMéx", variable=self.tipo_documento, value="UAEMEX", **rb_style).pack(
            side="left", padx=5)
        tk.Radiobutton(selector, text="INE", variable=self.tipo_documento, value="INE", **rb_style).pack(side="left",
                                                                                                         padx=5)

        # --- CONTENEDOR PRINCIPAL ---
        main = tk.Frame(self, bg=bg_main)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.columnconfigure(2, weight=1)

        # 1. COLUMNA CÁMARA
        frame_cam = tk.Frame(main, bg=bg_panel, highlightthickness=1, highlightbackground=border)
        frame_cam.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        tk.Label(frame_cam, text="LECTOR DE CREDENCIALES", font=("Segoe UI", 11, "bold"), fg=UAEM_GOLD,
                 bg=bg_panel).pack(pady=(20, 10))

        video_container = tk.Frame(frame_cam, bg="#000000", highlightthickness=2, highlightbackground=border)
        video_container.pack(padx=20, pady=10)
        self.lbl_video = tk.Label(video_container, bg="#000000", width=400, height=300)
        self.lbl_video.pack()

        btn_frame = tk.Frame(frame_cam, bg=bg_panel)
        btn_frame.pack(fill="x", padx=20, pady=20)

        self.btn_escanear = tk.Button(btn_frame, text="📷 Escanear Credencial", font=("Segoe UI", 11, "bold"),
                                      bg=UAEM_GOLD, fg="#000000", activebackground="#D19A00", relief="flat", pady=10,
                                      cursor="hand2", command=self.escanear)
        self.btn_escanear.pack(fill="x", pady=(0, 10))

        tk.Button(btn_frame, text="📂 Cargar Imagen", font=("Segoe UI", 10, "bold"), bg=UAEM_GREEN, fg=DARK_TEXT_PRIMARY,
                  activebackground=btn_hover, relief="flat", pady=8, cursor="hand2", command=self.cargar_imagen).pack(
            fill="x")

        # 2. COLUMNA FICHA
        frame_alumno = tk.Frame(main, bg=bg_panel, highlightthickness=1, highlightbackground=border)
        frame_alumno.grid(row=0, column=1, padx=10, sticky="nsew")
        tk.Label(frame_alumno, text="FICHA DEL ALUMNO", font=("Segoe UI", 11, "bold"), fg=UAEM_GOLD, bg=bg_panel).pack(
            pady=(20, 15))

        ficha_card = tk.Frame(frame_alumno, bg=bg_main, highlightthickness=1, highlightbackground=border)
        ficha_card.pack(fill="x", padx=20, pady=5)
        self.lbl_nombre = tk.Label(ficha_card, text="Esperando escaneo...", font=("Segoe UI", 18, "bold"),
                                   fg=text_primary, bg=bg_main)
        self.lbl_nombre.pack(pady=(20, 5))
        self.lbl_id = tk.Label(ficha_card, text="ID: ---", font=("Consolas", 14), fg=UAEM_GOLD, bg=bg_main)
        self.lbl_id.pack()
        self.lbl_tipo = tk.Label(ficha_card, text="Documento: ---", font=("Segoe UI", 10), fg=text_secondary,
                                 bg=bg_main)
        self.lbl_tipo.pack(pady=(0, 20))
        self.lbl_estado = tk.Label(frame_alumno, text="ESTADO: ESPERANDO", font=("Segoe UI", 14, "bold"),
                                   fg=text_secondary, bg=bg_panel)
        self.lbl_estado.pack(pady=20)
        tk.Label(frame_alumno, text="DETALLES DEL ESTADO DE CUENTA:", font=("Segoe UI", 9, "bold"), fg=text_secondary,
                 bg=bg_panel).pack(anchor="w", padx=20)
        self.txt_alertas = tk.Text(frame_alumno, wrap="word", font=("Segoe UI", 11), bg=bg_main, fg=text_primary,
                                   height=8, bd=0, padx=15, pady=15, state="disabled", highlightthickness=1,
                                   highlightbackground=border)
        self.txt_alertas.pack(fill="both", expand=True, padx=20, pady=(5, 20))

        # 3. COLUMNA ACCIONES
        self.frame_acciones = tk.Frame(main, bg=bg_panel, highlightthickness=1, highlightbackground=border)
        self.frame_acciones.grid(row=0, column=2, padx=(10, 0), sticky="nsew")
        tk.Label(self.frame_acciones, text="ACCIONES", font=("Segoe UI", 11, "bold"), fg=UAEM_GOLD, bg=bg_panel).pack(
            pady=(20, 15))
        self.lbl_instruccion = tk.Label(self.frame_acciones, text="Escanee una credencial...",
                                        font=("Segoe UI", 10, "italic"), fg=text_secondary, bg=bg_panel, wraplength=250)
        self.lbl_instruccion.pack(pady=10, padx=10)

        self.frame_prestamo = tk.Frame(self.frame_acciones, bg=bg_panel)
        tk.Label(self.frame_prestamo, text="Libro a prestar:", font=("Segoe UI", 10, "bold"), fg=UAEM_GOLD,
                 bg=bg_panel).pack(anchor="w", padx=15, pady=(10, 5))
        self.combo_libros = ttk.Combobox(self.frame_prestamo, textvariable=self.libro_seleccionado, state="readonly",
                                         font=("Segoe UI", 10))
        self.combo_libros.pack(fill="x", padx=15, pady=(0, 15))
        self.btn_prestar = tk.Button(self.frame_prestamo, text="✅ Registrar Préstamo", font=("Segoe UI", 11, "bold"),
                                     bg=UAEM_GREEN, fg=DARK_TEXT_PRIMARY, activebackground=btn_hover, relief="flat",
                                     pady=10, cursor="hand2", command=self.registrar_prestamo)
        self.btn_prestar.pack(fill="x", padx=15, pady=10)

        self.frame_devolucion = tk.Frame(self.frame_acciones, bg=bg_panel)
        tk.Label(self.frame_devolucion, text="Libro a devolver:", font=("Segoe UI", 10, "bold"), fg=DANGER_RED,
                 bg=bg_panel).pack(anchor="w", padx=15, pady=(10, 5))
        self.combo_devolver = ttk.Combobox(self.frame_devolucion, textvariable=self.libro_a_devolver, state="readonly",
                                           font=("Segoe UI", 10))
        self.combo_devolver.pack(fill="x", padx=15, pady=(0, 15))
        self.btn_devolver = tk.Button(self.frame_devolucion, text="📥 Registrar Devolución",
                                      font=("Segoe UI", 11, "bold"), bg=DANGER_RED, fg=DARK_TEXT_PRIMARY,
                                      activebackground="#B71C1C", relief="flat", pady=10, cursor="hand2",
                                      command=self.registrar_devolucion)
        self.btn_devolver.pack(fill="x", padx=15, pady=10)

        # 4. CONSOLA DE LOGS
        self.frame_logs = tk.Frame(self, bg="#000000" if self.is_dark_mode else "#1E1E1E", height=140)
        self.frame_logs.pack(fill="x", side="bottom")
        self.frame_logs.pack_propagate(False)
        log_header = tk.Frame(self.frame_logs, bg=bg_panel, height=25)
        log_header.pack(fill="x")
        log_header.pack_propagate(False)
        tk.Label(log_header, text=">_ Registro de Actividad", font=("Consolas", 9), fg=UAEM_GOLD, bg=bg_panel).pack(
            side="left", padx=10)
        self.txt_logs = tk.Text(self.frame_logs, bg="#000000" if self.is_dark_mode else "#FFFFFF", fg=text_secondary,
                                font=("Consolas", 9), bd=0, padx=15, pady=10, state="disabled")
        self.txt_logs.pack(fill="both", expand=True)
        self.txt_logs.tag_configure("ok", foreground="#4CAF50")
        self.txt_logs.tag_configure("error", foreground="#F44336")
        self.txt_logs.tag_configure("info", foreground=UAEM_GOLD)

        self._log("Sistema iniciado. Presione 'Enter' para escanear.", "info")

    # --- LÓGICA DE LA CÁMARA Y OCR ---
    def _iniciar_camara(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.after(0, lambda: self.lbl_video.config(text="❌ Cámara no detectada", font=("Segoe UI", 14),
                                                        fg=DANGER_RED))
            self.after(0, lambda: self.btn_escanear.config(state="disabled"))
            return
        self.camara_activa = True
        self.after(0, self._actualizar_frame)

    def _actualizar_frame(self):
        if not self.camara_activa: return
        if not self.pausa_camara:
            ret, frame = self.cap.read()
            if ret:
                self.frame_actual = frame.copy()
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(rgb).resize((400, 300))
                self.img_tk = ImageTk.PhotoImage(img_pil)
                # Verificamos que el label exista (por si se cambió el tema rápido)
                if hasattr(self, 'lbl_video') and self.lbl_video.winfo_exists():
                    self.lbl_video.config(image=self.img_tk)
        self.after(30, self._actualizar_frame)

    def _animar_spinner(self):
        if self.procesando_ocr and hasattr(self, 'btn_escanear') and self.btn_escanear.winfo_exists():
            char = self.spinner_chars[self.spinner_index]
            self.btn_escanear.config(text=f"{char} Procesando...")
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            self.after(100, self._animar_spinner)

    def escanear(self):
        if self.frame_actual is None or self.procesando_ocr: return
        self.procesando_ocr = True
        self.btn_escanear.config(state="disabled")
        self._animar_spinner()
        self.pausa_camara = True
        threading.Thread(target=self._procesar_bg, args=(self.frame_actual.copy(),), daemon=True).start()

    def cargar_imagen(self):
        ruta = filedialog.askopenfilename(title="Selecciona imagen", filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
        if not ruta: return
        img = cv2.imread(ruta)
        if img is not None:
            self.pausa_camara = True
            self.procesando_ocr = True
            self.btn_escanear.config(state="disabled")
            self._animar_spinner()
            threading.Thread(target=self._procesar_bg, args=(img,), daemon=True).start()

    def _procesar_bg(self, img):
        tipo = self.tipo_documento.get()
        reporte_doc = {"valida": False, "error": "Error desconocido"}

        try:
            gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            if tipo == "UAEMEX":
                gris_suave = cv2.GaussianBlur(gris, (5, 5), 0)
                _, umbral_inv = cv2.threshold(gris_suave, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                texto_completo = pytesseract.image_to_string(umbral_inv, lang="spa", config="--psm 11")

                lineas = texto_completo.split('\n')
                nombre_detectado = "Alumno Nuevo"
                for linea in lineas:
                    linea_limpia = linea.strip()
                    if re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', linea_limpia):
                        palabras = linea_limpia.split()
                        if 3 <= len(palabras) <= 5:
                            palabras_ignorar = ["UNIVERSIDAD", "CENTRO", "INGENIERO", "ALUMNO", "MEXICO", "ESTADO"]
                            if not any(p.upper() in palabras_ignorar for p in palabras):
                                nombre_detectado = linea_limpia
                                break

                texto_upper = texto_completo.upper().replace("O", "0")
                solo_numeros = re.sub(r"[^0-9]", " ", texto_upper)
                candidatos = re.findall(r"\d{7,9}", solo_numeros)

                if candidatos:
                    for cand in candidatos:
                        res = ParserMatriculaUAEMex.parsear(cand)
                        if res["valida"]:
                            res["nombre_ocr"] = nombre_detectado
                            reporte_doc = res
                            break
                else:
                    reporte_doc = {"valida": False, "error": "No se encontraron números válidos"}

            else:
                gris_suave = cv2.bilateralFilter(gris, 9, 75, 75)
                umbral = cv2.adaptiveThreshold(gris_suave, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31,
                                               15)
                texto_completo = pytesseract.image_to_string(umbral, lang="spa", config="--psm 6")
                texto_limpio = re.sub(r"[^A-Z0-9]", "", texto_completo.upper())

                for i in range(len(texto_limpio) - 17):
                    posible_clave = texto_limpio[i:i + 18]
                    if not (posible_clave[0:6].isalpha() and posible_clave[14] in ['H', 'M']):
                        continue
                    resultado = ParserClaveElectorINE.parsear(posible_clave)
                    if resultado["valida"]:
                        reporte_doc = resultado
                        break

            self.after(0, self._actualizar_ui_post_ocr, img, tipo, reporte_doc)

        except Exception as e:
            self.after(0, lambda: self._log(f"Error en OCR: {str(e)}", "error"))
            self.after(0, self._reset_estado_ocr)

    def _actualizar_ui_post_ocr(self, img, tipo, reporte_doc):
        if reporte_doc["valida"]:
            if tipo == "UAEMEX":
                self._evaluar_alumno(reporte_doc["matricula"], tipo, reporte_doc.get("nombre_ocr", "Alumno Nuevo"))
            else:
                self._evaluar_alumno(reporte_doc["clave"], tipo, "Ciudadano INE")
        else:
            self._limpiar_ficha()
            self._log("Error de lectura: Documento no válido.", "error")
            self._mostrar_mensaje_alerta(f"Error: {reporte_doc.get('error')}\n\nRevise el log inferior.", DANGER_RED)

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(rgb).resize((400, 300))
        self.img_anotada = ImageTk.PhotoImage(img_pil)
        self.lbl_video.config(image=self.img_anotada)
        self._reset_estado_ocr()

    def _reset_estado_ocr(self):
        self.procesando_ocr = False
        if hasattr(self, 'btn_escanear') and self.btn_escanear.winfo_exists():
            self.btn_escanear.config(state="normal", text="📷 Escanear Credencial")

    def _evaluar_alumno(self, numero_cuenta, tipo, nombre_ocr="Alumno Nuevo"):
        self._limpiar_ficha(keep_camera_paused=True)

        alumno = self.db.buscar_alumno(numero_cuenta)

        if not alumno:
            if self.db.registrar_alumno(numero_cuenta, nombre_ocr):
                self._log(f"✨ Alumno nuevo registrado: {nombre_ocr}", "ok")
                messagebox.showinfo("Alta de Alumno",
                                    f"Alumno no registrado.\nAlta exitosa:\n\nNombre: {nombre_ocr}\nID: {numero_cuenta}")
                alumno = self.db.buscar_alumno(numero_cuenta)
            else:
                messagebox.showerror("Error", "No se pudo registrar al alumno en la BD.")
                return

        id_credencial = alumno['id_credencial']
        nombre_completo = f"{alumno['nombre']} {alumno['apellido_paterno'] or ''} {alumno['apellido_materno'] or ''}".strip()

        self.alumno_actual = {"nombre": nombre_completo}
        self.id_credencial_actual = id_credencial

        text_primary = DARK_TEXT_PRIMARY if self.is_dark_mode else LIGHT_TEXT_PRIMARY

        self.lbl_nombre.config(text=nombre_completo, fg=text_primary)
        self.lbl_id.config(text=f"ID: {numero_cuenta}")
        self.lbl_tipo.config(text=f"Documento: {'Credencial UAEMéx' if tipo == 'UAEMEX' else 'INE'}")

        adeudos = self.db.obtener_adeudos(id_credencial)

        if adeudos:
            self.lbl_estado.config(text="ESTADO: CON ADEUDOS", fg=DANGER_RED)
            self._log(f"{nombre_completo} tiene {len(adeudos)} adeudo(s).", "error")

            txt = "El alumno presenta los siguientes adeudos:\n\n"
            for ad in adeudos:
                txt += f"📕 Libro sin devolver: {ad['libro']}\n   (Vence: {ad['fecha_devolucion']})\n\n"
            self._mostrar_mensaje_alerta(txt, UAEM_GOLD)

            self.lbl_instruccion.config(text="Registre la devolución.")
            self.frame_devolucion.pack(fill="x", pady=5)

            opciones = [f"ID:{ad['id_prestamo']} - {ad['libro']}" for ad in adeudos]
            self.combo_devolver['values'] = opciones
            if opciones: self.combo_devolver.current(0)
        else:
            self.lbl_estado.config(text="ESTADO: SIN ADEUDOS", fg="#4CAF50")
            self._log(f"{nombre_completo} verificado. Listo.", "ok")
            self._mostrar_mensaje_alerta("El alumno no tiene libros pendientes.\n\nPuede registrar un nuevo préstamo.",
                                         "#4CAF50")

            self.lbl_instruccion.config(text="Seleccione libro a prestar:")
            self.frame_prestamo.pack(fill="x", pady=5)

            libros = self.db.obtener_libros_disponibles()
            self.combo_libros['values'] = [lib['texto'] for lib in libros]
            if libros: self.combo_libros.current(0)

    def registrar_prestamo(self):
        if not self.id_credencial_actual or not self.libro_seleccionado.get(): return

        confirm = messagebox.askyesno("Confirmar Préstamo", "¿Está seguro de registrar este préstamo?")
        if not confirm: return

        seleccion = self.libro_seleccionado.get()
        id_ejemplar = int(seleccion.split(" - ")[0].replace("ID: ", ""))

        exito, fecha_devolucion = self.db.registrar_prestamo(self.id_credencial_actual, id_ejemplar)

        if exito:
            self._log(f"Préstamo exitoso para {self.alumno_actual['nombre']}", "ok")
            messagebox.showinfo("Préstamo Exitoso", f"Se registró el préstamo.\n\nDevolución: {fecha_devolucion}")
            self._evaluar_alumno(self.lbl_id.cget("text").replace("ID: ", ""), self.tipo_documento.get())
        else:
            self._log(f"Error al prestar: {fecha_devolucion}", "error")
            messagebox.showerror("Error", "No se pudo registrar el préstamo.")

    def registrar_devolucion(self):
        if not self.id_credencial_actual or not self.libro_a_devolver.get(): return

        confirm = messagebox.askyesno("Confirmar Devolución", "¿Confirma que el alumno devolvió el libro?")
        if not confirm: return

        seleccion = self.libro_a_devolver.get()
        id_prestamo = int(seleccion.split(" - ")[0].replace("ID:", "").strip())

        if self.db.registrar_devolucion(id_prestamo):
            self._log(f"Devolución registrada.", "ok")
            messagebox.showinfo("Devolución Exitosa", "Se registró la devolución del libro.")
            self._evaluar_alumno(self.lbl_id.cget("text").replace("ID: ", ""), self.tipo_documento.get())
        else:
            self._log(f"Error al devolver.", "error")
            messagebox.showerror("Error", "No se pudo registrar la devolución.")

    def abrir_historial(self):
        if not self.db:
            messagebox.showerror("Error", "Base de datos no conectada.")
            return

        try:
            historial = self.db.obtener_historial_dia()

            bg_main = DARK_BG_MAIN if self.is_dark_mode else LIGHT_BG_MAIN
            text_primary = DARK_TEXT_PRIMARY if self.is_dark_mode else LIGHT_TEXT_PRIMARY

            modal = tk.Toplevel(self)
            modal.title("Historial de Préstamos del Día")
            modal.geometry("700x400")
            modal.configure(bg=bg_main)

            # Esto hace que la ventana salga al frente y bloquee la de atrás
            modal.transient(self)
            modal.grab_set()
            modal.lift()
            modal.focus_force()

            tk.Label(modal, text="Préstamos Registrados Hoy", font=("Segoe UI", 14, "bold"), fg=UAEM_GOLD,
                     bg=bg_main).pack(pady=10)

            style = ttk.Style()
            style.configure("Treeview", background=DARK_BG_PANEL if self.is_dark_mode else "#FFFFFF",
                            foreground=text_primary, fieldbackground=DARK_BG_PANEL if self.is_dark_mode else "#FFFFFF",
                            borderwidth=0)
            style.configure("Treeview.Heading", background=UAEM_GREEN, foreground=UAEM_GOLD,
                            font=("Segoe UI", 10, "bold"))

            tree = ttk.Treeview(modal, columns=("Alumno", "Libro", "Estado"), show="headings", height=15)
            tree.heading("Alumno", text="Alumno")
            tree.heading("Libro", text="Libro")
            tree.heading("Estado", text="Estado")
            tree.column("Alumno", width=250)
            tree.column("Libro", width=250)
            tree.column("Estado", width=100, anchor="center")
            tree.pack(fill="both", expand=True, padx=20, pady=10)

            if historial:
                for h in historial:
                    nombre = f"{h['nombre']} {h['apellido_paterno']}"
                    tree.insert("", "end", values=(nombre, h['libro'], h['estado_prestamo'].upper()))
            else:
                # Si no hay datos, mostramos un mensaje en la tabla
                tree.insert("", "end", values=("No hay préstamos registrados hoy", "-", "-"))

            tk.Button(modal, text="Cerrar", font=("Segoe UI", 10, "bold"), bg=DANGER_RED, fg="#FFFFFF", relief="flat",
                      command=modal.destroy).pack(pady=10, ipadx=20)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el historial: {e}")

    def _limpiar_ficha(self, keep_camera_paused=False):
        self.alumno_actual = None
        self.id_credencial_actual = None

        text_primary = DARK_TEXT_PRIMARY if self.is_dark_mode else LIGHT_TEXT_PRIMARY
        text_secondary = DARK_TEXT_SECONDARY if self.is_dark_mode else LIGHT_TEXT_SECONDARY

        self.lbl_nombre.config(text="Esperando escaneo...", fg=text_primary)
        self.lbl_id.config(text="ID: ---")
        self.lbl_tipo.config(text="Documento: ---")
        self.lbl_estado.config(text="ESTADO: ESPERANDO", fg=text_secondary)
        self._mostrar_mensaje_alerta("", text_primary)
        self.lbl_instruccion.config(text="Escanee una credencial para habilitar acciones.", fg=text_secondary)
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
        if hasattr(self, 'txt_logs') and self.txt_logs.winfo_exists():
            self.txt_logs.config(state="normal")
            self.txt_logs.insert("end", f"[{hora}] {mensaje}\n", tag)
            self.txt_logs.see("end")
            self.txt_logs.config(state="disabled")

    def on_close(self):
        self.camara_activa = False
        if self.cap: self.cap.release()
        self.db.cerrar()
        self.destroy()


if __name__ == "__main__":
    app = AppBibliotecario()
    app.withdraw()
    splash = SplashScreen(app, app.is_dark_mode)

    def cargar():
        splash.destroy()
        app.deiconify()

    app.after(2000, cargar)
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()