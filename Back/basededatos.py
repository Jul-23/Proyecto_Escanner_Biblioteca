import sqlite3
import os
import sys
from datetime import datetime, timedelta
import re

# Esta función asegura que la BD se guarde en la misma carpeta del .exe o de app.py
def obtener_ruta_db():
    if getattr(sys, 'frozen', False):
        ruta_base = os.path.dirname(sys.executable)
    else:
        ruta_base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(ruta_base, "biblioteca.db")


class BibliotecaDB:
    def __init__(self):
        self.db_path = obtener_ruta_db()
        self.conn = None
        self.conectar()

    def conectar(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON;")
            self.crear_tablas()
        except Exception as e:
            print(f"Error al conectar a SQLite: {e}")

    def crear_tablas(self):
        with self.conn:
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS alumnos
                              (
                                  id_alumno
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  nombre
                                  TEXT
                                  NOT
                                  NULL,
                                  apellido_paterno
                                  TEXT
                                  NOT
                                  NULL,
                                  apellido_materno
                                  TEXT
                              )
                              """)
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS credenciales
                              (
                                  id_credencial
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  id_alumno
                                  INTEGER,
                                  numero_cuenta
                                  TEXT
                                  UNIQUE,
                                  FOREIGN
                                  KEY
                              (
                                  id_alumno
                              ) REFERENCES alumnos
                              (
                                  id_alumno
                              )
                                  )
                              """)
            # TABLA LIBROS ACTUALIZADA (Con autor, editorial, etc.)
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS libros
                              (
                                  id_libro
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  nombre
                                  TEXT
                                  NOT
                                  NULL,
                                  autor
                                  TEXT,
                                  editorial
                                  TEXT,
                                  edicion
                                  TEXT,
                                  estado_libro
                                  TEXT
                              )
                              """)
            # TABLA EJEMPLARES ACTUALIZADA (Con código de barras)
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS ejemplares
                              (
                                  id_ejemplar
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  id_libro
                                  INTEGER,
                                  codigo_barras
                                  TEXT
                                  UNIQUE,
                                  estado_ejemplar
                                  TEXT,
                                  FOREIGN
                                  KEY
                              (
                                  id_libro
                              ) REFERENCES libros
                              (
                                  id_libro
                              )
                                  )
                              """)
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS prestamo
                              (
                                  id_prestamo
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  id_credencial
                                  INTEGER,
                                  id_ejemplar
                                  INTEGER,
                                  fecha_prestamo
                                  TEXT,
                                  fecha_devolucion
                                  TEXT,
                                  estado_prestamo
                                  TEXT,
                                  FOREIGN
                                  KEY
                              (
                                  id_credencial
                              ) REFERENCES credenciales
                              (
                                  id_credencial
                              ),
                                  FOREIGN KEY
                              (
                                  id_ejemplar
                              ) REFERENCES ejemplares
                              (
                                  id_ejemplar
                              )
                                  )
                              """)

            # --- INSERTAR DATOS DE PRUEBA SI LA TABLA ESTÁ VACÍA ---
            cursor = self.conn.execute("SELECT COUNT(*) FROM libros")
            if cursor.fetchone()[0] == 0:
                # Insertar los 15 libros
                libros_data = [
                    # Ingeniería en Sistemas Inteligentes
                    ('Inteligencia Artificial. Teoría y Aplicaciones',
                     'Marco Antonio Ramos Corchado, Vianney Muñoz Jiménez', 'UAEMéx', '1ra', 'Disponible'),
                    ('Sistemas de Control para Ingeniería', 'Norman S. Nise', 'CECSA', '1ra', 'Disponible'),
                    ('Ingeniería de Control Moderna', 'Katsuhiko Ogata', 'Prentice Hall', '3ra', 'Disponible'),
                    # Licenciatura en Comercio
                    ('Fundamentos de Comercio Internacional', 'Lourdes Rocío Villalobos Torres', 'Porrúa', '1ra',
                     'Disponible'),
                    ('Marco Jurídico del Comercio Exterior de México', 'José Ignacio Martínez Cortés', 'UNAM', '1ra',
                     'Disponible'),
                    ('Marketing Internacional', 'Brenda González Bureos', 'UAEMéx', '1ra', 'Disponible'),
                    # Licenciatura en Salud
                    ('Anatomía y Fisiología para estudiantes de enfermería', 'Irma Guadalupe Rangel Enríquez',
                     'Editorial UAT', '1ra', 'Disponible'),
                    ('Bioestadística: principios, métodos y aplicaciones', 'Miriam Janet Cervantes López, et al.',
                     'Editorial UAT', '1ra', 'Disponible'),
                    ('Educación para la Salud', 'Vargas, A. y Palacios, P.', 'Grupo Editorial Patria', '1ra',
                     'Disponible'),
                    # Ingeniería en Transporte
                    ('Ingeniería de Tránsito y Carreteras', 'J. N. Garber, A. L. Hoel', 'Thomson', '3ra', 'Disponible'),
                    ('Ingeniería de Carreteras, Vol. I y II', 'C. Kraemer, et al.', 'Mc Graw Hill', '1ra',
                     'Disponible'),
                    ('Ingeniería de Tránsito (Fundamentos y Aplicaciones)', 'R. Cal y Mayor, J. Cárdenas', 'Alfaomega',
                     '1ra', 'Disponible'),
                    # Licenciatura en Seguridad Ciudadana
                    ('Seguridad Ciudadana: Visiones Compartidas', 'José Luis Estrada Rodríguez (Coord.)',
                     'UAEMéx / IAPEM', '1ra', 'Disponible'),
                    ('Seguridad ciudadana, participación social y buen gobierno', 'Maurice Chalom, et al.',
                     'Ediciones Sur', '1ra', 'Disponible'),
                    ('La Seguridad Pública', 'Luis Carlos Cruz Torrero', 'Trillas', '1ra', 'Disponible')
                ]
                self.conn.executemany(
                    "INSERT INTO libros (nombre, autor, editorial, edicion, estado_libro) VALUES (?, ?, ?, ?, ?)",
                    libros_data)

                # Insertar los 15 ejemplares
                ejemplares_data = [
                    # ISI
                    (1, 'UAEM-ISI-001', 'Buen estado'),
                    (2, 'UAEM-ISI-002', 'Buen estado'),
                    (3, 'UAEM-ISI-003', 'Buen estado'),
                    # LCO
                    (4, 'UAEM-LCO-001', 'Buen estado'),
                    (5, 'UAEM-LCO-002', 'Buen estado'),
                    (6, 'UAEM-LCO-003', 'Buen estado'),
                    # LSA
                    (7, 'UAEM-LSA-001', 'Buen estado'),
                    (8, 'UAEM-LSA-002', 'Buen estado'),
                    (9, 'UAEM-LSA-003', 'Buen estado'),
                    # ITR
                    (10, 'UAEM-ITR-001', 'Buen estado'),
                    (11, 'UAEM-ITR-002', 'Buen estado'),
                    (12, 'UAEM-ITR-003', 'Buen estado'),
                    # LSC
                    (13, 'UAEM-LSC-001', 'Buen estado'),
                    (14, 'UAEM-LSC-002', 'Buen estado'),
                    (15, 'UAEM-LSC-003', 'Buen estado')
                ]
                self.conn.executemany(
                    "INSERT INTO ejemplares (id_libro, codigo_barras, estado_ejemplar) VALUES (?, ?, ?)",
                    ejemplares_data)

    def cerrar(self):
        if self.conn:
            self.conn.close()

    def buscar_alumno(self, numero_cuenta):
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT c.id_credencial, a.nombre, a.apellido_paterno, a.apellido_materno
                       FROM credenciales c
                                JOIN alumnos a ON c.id_alumno = a.id_alumno
                       WHERE c.numero_cuenta = ?
                       """, (numero_cuenta,))
        resultado = cursor.fetchone()
        if resultado:
            return {"id_credencial": resultado[0], "nombre": resultado[1], "apellido_paterno": resultado[2],
                    "apellido_materno": resultado[3]}
        return None

    def registrar_alumno(self, numero_cuenta, nombre_completo):
        try:
            nombre_limpio = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', nombre_completo).strip()
            partes = nombre_limpio.split()
            nombre = partes[0] if partes else "Alumno"
            apellido_pat = partes[-2] if len(partes) >= 3 else (partes[1] if len(partes) == 2 else "Sin Apellido")
            apellido_mat = partes[-1] if len(partes) >= 3 else None

            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("INSERT INTO alumnos (nombre, apellido_paterno, apellido_materno) VALUES (?, ?, ?)",
                               (nombre, apellido_pat, apellido_mat))
                id_alumno = cursor.lastrowid
                cursor.execute("INSERT INTO credenciales (id_alumno, numero_cuenta) VALUES (?, ?)",
                               (id_alumno, numero_cuenta))
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def obtener_libros_disponibles(self):
        cursor = self.conn.cursor()
        # ACTUALIZADO: Traemos el autor para mostrarlo en el menú
        cursor.execute("""
                       SELECT e.id_ejemplar, l.nombre, l.autor
                       FROM ejemplares e
                                JOIN libros l ON e.id_libro = l.id_libro
                       WHERE e.id_ejemplar NOT IN (SELECT id_ejemplar FROM prestamo WHERE estado_prestamo = 'activo')
                       """)
        # Retorna el formato: "ID: 1 - Inteligencia Artificial (Marco Antonio...)"
        return [{"id": r[0], "texto": f"ID: {r[0]} - {r[1]} ({r[2]})"} for r in cursor.fetchall()]

    def obtener_adeudos(self, id_credencial):
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT p.id_prestamo, l.nombre, p.fecha_devolucion
                       FROM prestamo p
                                JOIN ejemplares e ON p.id_ejemplar = e.id_ejemplar
                                JOIN libros l ON e.id_libro = l.id_libro
                       WHERE p.id_credencial = ?
                         AND p.estado_prestamo = 'activo'
                       """, (id_credencial,))
        return [{"id_prestamo": r[0], "libro": r[1], "fecha_devolucion": r[2]} for r in cursor.fetchall()]

    def registrar_prestamo(self, id_credencial, id_ejemplar):
        try:
            fecha_prestamo = datetime.now().strftime('%Y-%m-%d')
            fecha_devolucion = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')
            with self.conn:
                self.conn.execute("""
                                  INSERT INTO prestamo (id_credencial, id_ejemplar, fecha_prestamo, fecha_devolucion,
                                                        estado_prestamo)
                                  VALUES (?, ?, ?, ?, 'activo')
                                  """, (id_credencial, id_ejemplar, fecha_prestamo, fecha_devolucion))
            return True, fecha_devolucion
        except Exception as e:
            return False, str(e)

    def registrar_devolucion(self, id_prestamo):
        try:
            fecha_devolucion = datetime.now().strftime('%Y-%m-%d')
            with self.conn:
                self.conn.execute(
                    "UPDATE prestamo SET estado_prestamo = 'devuelto', fecha_devolucion = ? WHERE id_prestamo = ?",
                    (fecha_devolucion, id_prestamo))
            return True
        except Exception as e:
            return False

    def obtener_historial_dia(self):
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT a.nombre, a.apellido_paterno, l.nombre, p.fecha_prestamo, p.estado_prestamo
                       FROM prestamo p
                                JOIN credenciales c ON p.id_credencial = c.id_credencial
                                JOIN alumnos a ON c.id_alumno = a.id_alumno
                                JOIN ejemplares e ON p.id_ejemplar = e.id_ejemplar
                                JOIN libros l ON e.id_libro = l.id_libro
                       WHERE p.fecha_prestamo = date ('now', 'localtime') -- <-- AQUÍ ESTÁ EL CAMBIO
                       ORDER BY p.id_prestamo DESC
                       """)
        return [{"nombre": r[0], "apellido_paterno": r[1], "libro": r[2], "fecha_prestamo": r[3],
                 "estado_prestamo": r[4]} for r in cursor.fetchall()]