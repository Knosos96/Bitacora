"""Bitácora TI — aplicación de escritorio (Tkinter).
Uso:  python -m desktop.app
Habla con la API (uvicorn app.main:app) y no toca la base de datos directamente.
"""
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, simpledialog, ttk

from app.enums import SUBTIPOS, Estado, Tipo
from desktop.api_client import ClienteApi, ErrorApi

TIPOS = [t.value for t in Tipo]


class Login(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bitácora TI — Iniciar sesión")
        self.resizable(False, False)
        self.cliente: ClienteApi | None = None
        f = ttk.Frame(self, padding=16)
        f.grid()
        self.url = tk.StringVar(value="http://localhost:8000")
        self.correo = tk.StringVar()
        self.clave = tk.StringVar()
        for i, (txt, var, oculto) in enumerate(
            [("Servidor", self.url, False), ("Correo", self.correo, False), ("Clave", self.clave, True)]
        ):
            ttk.Label(f, text=txt).grid(row=i, column=0, sticky="w", pady=4)
            e = ttk.Entry(f, textvariable=var, width=32, show="•" if oculto else "")
            e.grid(row=i, column=1, pady=4)
            if i == 1:
                e.focus()
        ttk.Button(f, text="Entrar", command=self.entrar).grid(row=3, column=1, sticky="e", pady=8)
        self.bind("<Return>", lambda _e: self.entrar())

    def entrar(self):
        try:
            c = ClienteApi(self.url.get())
            c.login(self.correo.get().strip(), self.clave.get())
        except ErrorApi as e:
            messagebox.showerror("No se pudo entrar", str(e), parent=self)
            return
        self.cliente = c
        self.destroy()


class Principal(tk.Tk):
    COLUMNAS = [("folio", "Folio", 110), ("fecha", "Fecha", 90), ("tipo", "Tipo", 90),
                ("titulo", "Título", 330), ("estado", "Estado", 100), ("resp", "Responsable", 130)]

    def __init__(self, cliente: ClienteApi):
        super().__init__()
        self.c = cliente
        self.title(f"Bitácora TI — {cliente.usuario['nombre']} ({cliente.usuario['rol']})")
        self.geometry("1000x620")
        self.areas: dict[str, str] = {}
        self._armar_filtros()
        self._armar_lista()
        self._armar_alta()
        self.cargar_areas()
        self.recargar()

    # --- filtros -------------------------------------------------------
    def _armar_filtros(self):
        f = ttk.Frame(self, padding=(10, 10, 10, 0))
        f.pack(fill="x")
        hoy = date.today().isoformat()
        self.desde, self.hasta = tk.StringVar(value=hoy), tk.StringVar(value=hoy)
        self.f_tipo = tk.StringVar(value="todos")
        ttk.Label(f, text="Desde (AAAA-MM-DD)").pack(side="left")
        ttk.Entry(f, textvariable=self.desde, width=12).pack(side="left", padx=4)
        ttk.Label(f, text="Hasta").pack(side="left")
        ttk.Entry(f, textvariable=self.hasta, width=12).pack(side="left", padx=4)
        ttk.Label(f, text="Tipo").pack(side="left", padx=(8, 0))
        ttk.Combobox(f, textvariable=self.f_tipo, values=["todos"] + TIPOS, width=11,
                     state="readonly").pack(side="left", padx=4)
        ttk.Button(f, text="Buscar", command=self.recargar).pack(side="left", padx=6)
        ttk.Button(f, text="Hoy", command=self.ir_a_hoy).pack(side="left")
        ttk.Button(f, text="Pendientes", command=lambda: Pendientes(self, self.c)).pack(side="left", padx=6)
        ttk.Button(f, text="Búsqueda…", command=lambda: Busqueda(self, self.c)).pack(side="left")
        if self.c.usuario["rol"] in ("encargado", "jefe"):
            ttk.Button(f, text="Tablero", command=lambda: Tablero(self, self.c)).pack(side="left", padx=6)
            ttk.Button(f, text="Administración", command=lambda: Administracion(self, self.c)).pack(side="left")
        self.total = ttk.Label(f, text="")
        self.total.pack(side="right")
        # Aviso de compromisos vencidos: visible en la pantalla de inicio, clic para verlos.
        self.aviso = tk.Label(self, text="", fg="#b00020", cursor="hand2", anchor="w", padx=12)
        self.aviso.pack(fill="x")
        self.aviso.bind("<Button-1>", lambda _e: Pendientes(self, self.c, solo_vencidos=True))

    def ir_a_hoy(self):
        hoy = date.today().isoformat()
        self.desde.set(hoy)
        self.hasta.set(hoy)
        self.f_tipo.set("todos")
        self.recargar()

    # --- lista ---------------------------------------------------------
    def _armar_lista(self):
        f = ttk.Frame(self, padding=10)
        f.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(f, columns=[c[0] for c in self.COLUMNAS], show="headings", height=10)
        for k, txt, ancho in self.COLUMNAS:
            self.tabla.heading(k, text=txt)
            self.tabla.column(k, width=ancho, anchor="w")
        sb = ttk.Scrollbar(f, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tabla.bind("<Double-1>", self.ver_detalle)

    def recargar(self):
        tipos = None if self.f_tipo.get() == "todos" else [self.f_tipo.get()]
        try:
            r = self.c.eventos(self.desde.get().strip() or None, self.hasta.get().strip() or None, tipos)
        except ErrorApi as e:
            messagebox.showerror("Error", str(e), parent=self)
            return
        self.tabla.delete(*self.tabla.get_children())
        for e in r["data"]:
            self.tabla.insert("", "end", iid=e["folio"], values=(
                e["folio"], e["fecha_hecho"], e["tipo"], e["titulo"], e["estado"],
                (e["responsable"] or {}).get("nombre", "—")))
        self.total.config(text=f"{r['meta']['total']} evento(s)")
        self._actualizar_aviso()

    def _actualizar_aviso(self):
        try:
            n = len(self.c.pendientes(solo_vencidos=True)["compromisos"])
        except ErrorApi:
            n = 0
        self.aviso.config(text=f"⚠ {n} compromiso(s) vencido(s) — clic para verlos" if n else "")

    def ver_detalle(self, _evento):
        sel = self.tabla.selection()
        if sel:
            Detalle(self, self.c, sel[0], al_cambiar=self.recargar)

    # --- alta rápida ---------------------------------------------------
    def _armar_alta(self):
        f = ttk.LabelFrame(self, text="Nuevo evento", padding=10)
        f.pack(fill="x", padx=10, pady=(0, 10))
        self.n_tipo = tk.StringVar(value="otro")
        self.n_sub = tk.StringVar()
        self.n_titulo = tk.StringVar()
        self.n_area = tk.StringVar()
        self.n_solic = tk.StringVar()
        self.n_seg = tk.BooleanVar(value=False)

        ttk.Label(f, text="Tipo").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(f, textvariable=self.n_tipo, values=TIPOS, width=11, state="readonly")
        cb.grid(row=0, column=1, padx=4)
        cb.bind("<<ComboboxSelected>>", self._cambio_tipo)
        ttk.Label(f, text="Subtipo").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.cb_sub = ttk.Combobox(f, textvariable=self.n_sub, width=13, state="readonly")
        self.cb_sub.grid(row=0, column=3, padx=4)
        ttk.Label(f, text="Título").grid(row=0, column=4, sticky="w", padx=(8, 0))
        ttk.Entry(f, textvariable=self.n_titulo, width=42).grid(row=0, column=5, padx=4, sticky="we")
        f.columnconfigure(5, weight=1)

        ttk.Label(f, text="Área").grid(row=1, column=0, sticky="w", pady=4)
        self.cb_area = ttk.Combobox(f, textvariable=self.n_area, width=11, state="readonly")
        self.cb_area.grid(row=1, column=1, padx=4)
        ttk.Label(f, text="Solicitante").grid(row=1, column=2, sticky="w", padx=(8, 0))
        ttk.Entry(f, textvariable=self.n_solic, width=15).grid(row=1, column=3, padx=4)
        ttk.Checkbutton(f, text="Requiere seguimiento", variable=self.n_seg).grid(row=1, column=5, sticky="w", padx=4)

        ttk.Label(f, text="Texto").grid(row=2, column=0, sticky="nw")
        self.n_texto = tk.Text(f, height=4, wrap="word")
        self.n_texto.grid(row=2, column=1, columnspan=5, sticky="we", padx=4)
        ttk.Button(f, text="Guardar", command=self.guardar).grid(row=3, column=5, sticky="e", pady=(6, 0))
        self._cambio_tipo()

    def _cambio_tipo(self, _e=None):
        try:
            nombres = sorted(x["nombre"] for x in self.c.subtipos(self.n_tipo.get()))
        except ErrorApi:
            nombres = sorted(SUBTIPOS[Tipo(self.n_tipo.get())])
        subs = [""] + nombres
        self.cb_sub.config(values=subs)
        self.n_sub.set("")

    def cargar_areas(self):
        try:
            self.areas = {a["nombre"]: a["id"] for a in self.c.areas()}
        except ErrorApi:
            self.areas = {}
        self.cb_area.config(values=[""] + list(self.areas))

    def guardar(self):
        datos = {
            "tipo": self.n_tipo.get(),
            "subtipo": self.n_sub.get() or None,
            "titulo": self.n_titulo.get().strip(),
            "descripcion": self.n_texto.get("1.0", "end").strip(),
            "area_id": self.areas.get(self.n_area.get()),
            "solicitante_nombre": self.n_solic.get().strip() or None,
            "requiere_seguimiento": self.n_seg.get(),
        }
        if not datos["titulo"] or not datos["descripcion"]:
            messagebox.showwarning("Faltan datos", "Título y texto son obligatorios.", parent=self)
            return
        try:
            e = self.c.crear_evento(datos)
        except ErrorApi as ex:
            messagebox.showerror("No se guardó", str(ex), parent=self)
            return
        self.n_titulo.set("")
        self.n_texto.delete("1.0", "end")
        self.n_solic.set("")
        self.n_seg.set(False)
        self.ir_a_hoy()
        messagebox.showinfo("Guardado", f"Evento registrado: {e['folio']}", parent=self)


ESTADOS_SIGUIENTES = {
    "abierto": ["en_proceso", "en_espera", "resuelto", "cancelado"],
    "en_proceso": ["en_espera", "resuelto", "cerrado", "cancelado"],
    "en_espera": ["en_proceso", "resuelto", "cerrado", "cancelado"],
    "resuelto": ["en_proceso", "cerrado"],
    "cerrado": ["abierto"],  # reabrir (solo encargado/jefe; el servidor lo valida y pide el motivo)
}


class Detalle(tk.Toplevel):
    """Ficha del evento: notas, compromisos y cambio de estado. El servidor decide qué se permite."""

    def __init__(self, padre, cliente: ClienteApi, folio: str, al_cambiar=None):
        super().__init__(padre)
        self.c, self.folio, self.al_cambiar = cliente, folio, al_cambiar
        self.title(folio)
        self.geometry("720x720")
        self.ficha = tk.Text(self, wrap="word", height=10, padx=10, pady=8)
        self.ficha.pack(fill="x")

        barra = ttk.Frame(self, padding=(10, 6))
        barra.pack(fill="x")
        self.sig = tk.StringVar()
        self.cb_estado = ttk.Combobox(barra, textvariable=self.sig, width=12, state="readonly")
        self.cb_estado.pack(side="left")
        ttk.Button(barra, text="Cambiar estado", command=self.cambiar_estado).pack(side="left", padx=4)
        self.btn_seg = ttk.Button(barra, text="Activar seguimiento", command=self.alternar_seguimiento)
        self.btn_seg.pack(side="right")
        ttk.Button(barra, text="Corregir datos", command=self.corregir).pack(side="right", padx=4)
        ttk.Button(barra, text="Auditoría", command=self.ver_auditoria).pack(side="right")

        ttk.Label(self, text="Historial de notas", padding=(10, 4)).pack(anchor="w")
        self.notas = tk.Text(self, wrap="word", height=10, padx=10, state="disabled")
        self.notas.pack(fill="both", expand=True, padx=10)
        fila = ttk.Frame(self, padding=(10, 6))
        fila.pack(fill="x")
        self.n_nota = tk.StringVar()
        e = ttk.Entry(fila, textvariable=self.n_nota)
        e.pack(side="left", fill="x", expand=True)
        e.bind("<Return>", lambda _e: self.agregar_nota())
        ttk.Button(fila, text="Agregar nota", command=self.agregar_nota).pack(side="left", padx=4)

        ttk.Label(self, text="Compromisos", padding=(10, 4)).pack(anchor="w")
        self.tabla = ttk.Treeview(self, columns=("fecha", "desc", "resp", "estado"), show="headings", height=4)
        for k, t, a in (("fecha", "Fecha límite", 100), ("desc", "Compromiso", 330), ("resp", "Responsable", 110), ("estado", "Estado", 90)):
            self.tabla.heading(k, text=t)
            self.tabla.column(k, width=a, anchor="w")
        self.tabla.pack(fill="x", padx=10)
        fila = ttk.Frame(self, padding=(10, 6))
        fila.pack(fill="x")
        self.c_desc, self.c_fecha = tk.StringVar(), tk.StringVar(value=date.today().isoformat())
        ttk.Entry(fila, textvariable=self.c_desc).pack(side="left", fill="x", expand=True)
        ttk.Entry(fila, textvariable=self.c_fecha, width=11).pack(side="left", padx=4)
        ttk.Button(fila, text="Agregar", command=self.agregar_compromiso).pack(side="left")
        ttk.Button(fila, text="Marcar cumplido", command=lambda: self.resolver("cumplido")).pack(side="left", padx=4)
        ttk.Button(fila, text="Cancelar", command=lambda: self.resolver("cancelado")).pack(side="left")
        self.cargar()

    def _error(self, ex):
        messagebox.showerror("No se pudo", str(ex), parent=self)

    def _avisar(self):
        self.cargar()
        if self.al_cambiar:
            self.al_cambiar()

    def cargar(self):
        try:
            self.e = self.c.evento_con_auditoria(self.folio)
        except ErrorApi as ex:
            self._error(ex)
            return
        e = self.e
        lineas = [
            f"{e['folio']}  ·  {e['tipo']}" + (f" / {e['subtipo']}" if e["subtipo"] else ""),
            f"Fecha del hecho: {e['fecha_hecho']}",
            f"Estado: {e['estado']}" + (f"   Prioridad: {e['prioridad']}" if e["prioridad"] else ""),
            f"Área: {(e['area_origen'] or {}).get('nombre', '—')}   Solicitante: {e['solicitante'] or '—'}",
            f"Registró: {e['autor']['nombre']}   Responsable: {(e['responsable'] or {}).get('nombre', '—')}",
            f"Referencia: {e['referencia'] or '—'}",
            "", e["titulo"], "", e["descripcion"],
        ]
        self.ficha.config(state="normal")
        self.ficha.delete("1.0", "end")
        self.ficha.insert("1.0", "\n".join(lineas))
        self.ficha.config(state="disabled")

        self.cb_estado.config(values=ESTADOS_SIGUIENTES.get(e["estado"], []))
        self.sig.set("")
        self.btn_seg.config(text="Quitar seguimiento" if e["requiere_seguimiento"] else "Activar seguimiento")

        self.notas.config(state="normal")
        self.notas.delete("1.0", "end")
        for n in e["seguimientos"]:
            self.notas.insert("end", f"[{n['creado_en'][:16].replace('T', ' ')}] {n['autor']['nombre']}: {n['nota']}\n")
        self.notas.config(state="disabled")
        self.notas.see("end")

        self.tabla.delete(*self.tabla.get_children())
        for c in e["compromisos"]:
            est = "VENCIDO" if c["vencido"] else c["estado"]
            self.tabla.insert("", "end", iid=c["id"], values=(c["fecha_limite"], c["descripcion"], c["responsable"]["nombre"], est))

    def corregir(self):
        Corregir(self, self.c, self.e, al_guardar=self._avisar)

    def ver_auditoria(self):
        filas = self.e.get("auditoria") or []
        if not filas:
            messagebox.showinfo("Auditoría", "Este evento no tiene correcciones.", parent=self)
            return
        texto = "\n".join(
            f"[{a['creado_en'][:16].replace('T', ' ')}] {a['usuario']['nombre']}: {a['campo']}  "
            f"«{a['valor_anterior'] or '—'}» → «{a['valor_nuevo'] or '—'}»" for a in filas)
        messagebox.showinfo("Auditoría", texto, parent=self)

    def cambiar_estado(self):
        if not self.sig.get():
            return
        pide = "Motivo de la reapertura (obligatorio):" if self.e["estado"] == "cerrado" else \
            "Nota del cambio (obligatoria para en_espera y para cerrar con atajo):"
        nota = simpledialog.askstring("Nota", pide, parent=self)
        try:
            try:
                self.c.cambiar_estado(self.folio, self.sig.get(), nota)
            except ErrorApi as ex:
                if "compromiso" in str(ex).lower() and "pendiente" in str(ex).lower():
                    op = messagebox.askyesnocancel(
                        "Compromisos pendientes",
                        f"{ex}\n\nSí = marcarlos cumplidos · No = cancelarlos · Cancelar = no cerrar", parent=self)
                    if op is None:
                        return
                    self.c.cambiar_estado(self.folio, self.sig.get(), nota, "cumplir" if op else "cancelar")
                else:
                    raise
        except ErrorApi as ex:
            self._error(ex)
            return
        self._avisar()

    def alternar_seguimiento(self):
        try:
            self.c.modificar_evento(self.folio, {"requiere_seguimiento": not self.e["requiere_seguimiento"]})
        except ErrorApi as ex:
            self._error(ex)
            return
        self._avisar()

    def agregar_nota(self):
        texto = self.n_nota.get().strip()
        if not texto:
            return
        try:
            self.c.agregar_nota(self.folio, texto)
        except ErrorApi as ex:
            self._error(ex)
            return
        self.n_nota.set("")
        self._avisar()

    def agregar_compromiso(self):
        if not self.c_desc.get().strip():
            return
        try:
            self.c.crear_compromiso(self.folio, self.c_desc.get().strip(), self.c_fecha.get().strip())
        except ErrorApi as ex:
            self._error(ex)
            return
        self.c_desc.set("")
        self._avisar()

    def resolver(self, estado):
        sel = self.tabla.selection()
        if not sel:
            return
        try:
            self.c.resolver_compromiso(sel[0], estado)
        except ErrorApi as ex:
            self._error(ex)
            return
        self._avisar()


class Pendientes(tk.Toplevel):
    """CU-15: eventos con seguimiento sin cerrar y compromisos abiertos."""

    def __init__(self, padre, cliente: ClienteApi, solo_vencidos: bool = False):
        super().__init__(padre)
        self.c = cliente
        self.title("Pendientes")
        self.geometry("900x520")
        barra = ttk.Frame(self, padding=8)
        barra.pack(fill="x")
        self.venc = tk.BooleanVar(value=solo_vencidos)
        ttk.Checkbutton(barra, text="Solo vencidos", variable=self.venc, command=self.cargar).pack(side="left")
        ttk.Button(barra, text="Actualizar", command=self.cargar).pack(side="left", padx=8)

        ttk.Label(self, text="Eventos con seguimiento", padding=(8, 0)).pack(anchor="w")
        self.t_ev = ttk.Treeview(self, columns=("folio", "tipo", "titulo", "estado", "resp"), show="headings", height=8)
        for k, t, a in (("folio", "Folio", 110), ("tipo", "Tipo", 90), ("titulo", "Título", 380), ("estado", "Estado", 100), ("resp", "Responsable", 130)):
            self.t_ev.heading(k, text=t)
            self.t_ev.column(k, width=a, anchor="w")
        self.t_ev.pack(fill="both", expand=True, padx=8)
        self.t_ev.bind("<Double-1>", lambda _e: self._abrir(self.t_ev))

        ttk.Label(self, text="Compromisos pendientes", padding=(8, 6, 8, 0)).pack(anchor="w")
        self.t_co = ttk.Treeview(self, columns=("fecha", "folio", "desc", "resp", "estado"), show="headings", height=8)
        for k, t, a in (("fecha", "Fecha límite", 100), ("folio", "Evento", 110), ("desc", "Compromiso", 360), ("resp", "Responsable", 130), ("estado", "", 80)):
            self.t_co.heading(k, text=t)
            self.t_co.column(k, width=a, anchor="w")
        self.t_co.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.t_co.bind("<Double-1>", lambda _e: self._abrir(self.t_co, col=1))
        self.cargar()

    def _abrir(self, tabla, col=0):
        sel = tabla.selection()
        if sel:
            Detalle(self, self.c, tabla.item(sel[0])["values"][col], al_cambiar=self.cargar)

    def cargar(self):
        try:
            r = self.c.pendientes(solo_vencidos=self.venc.get())
        except ErrorApi as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return
        self.t_ev.delete(*self.t_ev.get_children())
        for e in r["eventos"]:
            self.t_ev.insert("", "end", values=(e["folio"], e["tipo"], e["titulo"], e["estado"], (e["responsable"] or {}).get("nombre", "—")))
        self.t_co.delete(*self.t_co.get_children())
        for c in r["compromisos"]:
            self.t_co.insert("", "end", values=(c["fecha_limite"], c["evento_folio"], c["descripcion"], c["responsable"]["nombre"], "VENCIDO" if c["vencido"] else ""))


class Corregir(tk.Toplevel):
    """CU-23: corrige título, descripción, referencia, solicitante, fecha y subtipo. Queda en auditoría."""

    CAMPOS = [("titulo", "Título"), ("descripcion", "Descripción"), ("referencia", "Referencia"),
              ("solicitante_nombre", "Solicitante"), ("fecha_hecho", "Fecha del hecho (AAAA-MM-DD)"),
              ("subtipo", "Subtipo")]

    def __init__(self, padre, cliente: ClienteApi, evento: dict, al_guardar=None):
        super().__init__(padre)
        self.c, self.ev, self.al_guardar = cliente, evento, al_guardar
        self.title(f"Corregir {evento['folio']}")
        self.vars: dict[str, tk.StringVar] = {}
        actual = {"solicitante_nombre": evento.get("solicitante")}
        for i, (k, etiqueta) in enumerate(self.CAMPOS):
            ttk.Label(self, text=etiqueta).grid(row=i, column=0, sticky="w", padx=10, pady=4)
            v = tk.StringVar(value=str(actual.get(k, evento.get(k)) or ""))
            self.vars[k] = v
            ttk.Entry(self, textvariable=v, width=60).grid(row=i, column=1, padx=10, pady=4)
        ttk.Label(self, text="El autor corrige el mismo día; después, encargado o jefe.").grid(
            row=len(self.CAMPOS), column=0, columnspan=2, pady=4)
        ttk.Button(self, text="Guardar", command=self.guardar).grid(row=len(self.CAMPOS) + 1, column=1, sticky="e", padx=10, pady=8)

    def guardar(self):
        antes = {"solicitante_nombre": self.ev.get("solicitante")}
        cambios = {}
        for k, v in self.vars.items():
            nuevo = v.get().strip()
            previo = str(antes.get(k, self.ev.get(k)) or "")
            if nuevo != previo:
                cambios[k] = nuevo or None
        if not cambios:
            self.destroy()
            return
        try:
            self.c.corregir_evento(self.ev["folio"], cambios)
        except ErrorApi as ex:
            messagebox.showerror("No se pudo", str(ex), parent=self)
            return
        if self.al_guardar:
            self.al_guardar()
        self.destroy()


ESTADOS = [e.value for e in Estado]


class Busqueda(tk.Toplevel):
    """CU-11 y CU-12: texto libre (sin acentos, en cualquier campo) más filtros."""

    def __init__(self, padre, cliente: ClienteApi):
        super().__init__(padre)
        self.c = cliente
        self.title("Búsqueda")
        self.geometry("1000x560")
        f = ttk.Frame(self, padding=8)
        f.pack(fill="x")
        self.q = tk.StringVar()
        e = ttk.Entry(f, textvariable=self.q, width=34)
        e.pack(side="left")
        e.bind("<Return>", lambda _e: self.buscar())
        e.focus_set()
        self.tipo, self.estado = tk.StringVar(value="todos"), tk.StringVar(value="todos")
        self.seg = tk.StringVar(value="todos")
        self.venc = tk.BooleanVar()
        for var, valores, ancho in ((self.tipo, ["todos"] + TIPOS, 10), (self.estado, ["todos"] + ESTADOS, 11),
                                    (self.seg, ["todos", "con", "sin"], 7)):
            ttk.Combobox(f, textvariable=var, values=valores, width=ancho, state="readonly").pack(side="left", padx=3)
        ttk.Checkbutton(f, text="Vencidos", variable=self.venc).pack(side="left", padx=4)
        ttk.Button(f, text="Buscar", command=self.buscar).pack(side="left", padx=4)
        if self.c.usuario["rol"] in ("encargado", "jefe"):
            ttk.Button(f, text="Exportar CSV", command=self.exportar).pack(side="left", padx=4)

        f2 = ttk.Frame(self, padding=(8, 0))
        f2.pack(fill="x")
        self.desde, self.hasta = tk.StringVar(), tk.StringVar()
        ttk.Label(f2, text="Desde (opcional)").pack(side="left")
        ttk.Entry(f2, textvariable=self.desde, width=11).pack(side="left", padx=4)
        ttk.Label(f2, text="Hasta").pack(side="left")
        ttk.Entry(f2, textvariable=self.hasta, width=11).pack(side="left", padx=4)
        ttk.Label(f2, text="Sin fechas se busca en todo el histórico. Un folio abre ese evento.").pack(side="left", padx=10)
        self.total = ttk.Label(f2, text="")
        self.total.pack(side="right")

        cols = (("folio", "Folio", 105), ("fecha", "Fecha", 85), ("tipo", "Tipo", 80), ("titulo", "Título", 250),
                ("estado", "Estado", 85), ("frag", "Coincidencia", 360))
        self.tabla = ttk.Treeview(self, columns=[c[0] for c in cols], show="headings")
        for k, t, a in cols:
            self.tabla.heading(k, text=t)
            self.tabla.column(k, width=a, anchor="w")
        self.tabla.pack(fill="both", expand=True, padx=8, pady=8)
        self.tabla.bind("<Double-1>", self._abrir)

    def _abrir(self, _e):
        sel = self.tabla.selection()
        if sel:
            Detalle(self, self.c, sel[0], al_cambiar=self.buscar)

    def _filtros(self) -> dict:
        pick = lambda v: None if v.get() == "todos" else v.get()  # noqa: E731
        return dict(q=self.q.get().strip(), desde=self.desde.get().strip(), hasta=self.hasta.get().strip(),
                    tipo=pick(self.tipo), estado=pick(self.estado), seguimiento=pick(self.seg),
                    vencidos=True if self.venc.get() else None)

    def exportar(self):
        """CU-22: el CSV usa exactamente el filtro que tienes en pantalla."""
        destino = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile="bitacora.csv",
                                               filetypes=[("CSV", "*.csv")])
        if not destino:
            return
        try:
            datos = self.c.exportar_csv(**self._filtros())
        except ErrorApi as ex:
            messagebox.showerror("No se pudo exportar", str(ex), parent=self)
            return
        with open(destino, "wb") as f:
            f.write(datos)
        messagebox.showinfo("Exportado", f"Archivo guardado en:\n{destino}", parent=self)

    def buscar(self):
        pick = lambda v: None if v.get() == "todos" else v.get()  # noqa: E731
        try:
            r = self.c.buscar(q=self.q.get().strip(), desde=self.desde.get().strip(), hasta=self.hasta.get().strip(),
                              tipo=pick(self.tipo), estado=pick(self.estado), seguimiento=pick(self.seg),
                              vencidos=True if self.venc.get() else None, page_size=200)
        except ErrorApi as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return
        self.tabla.delete(*self.tabla.get_children())
        for e in r["data"]:
            self.tabla.insert("", "end", iid=e["folio"], values=(
                e["folio"], e["fecha_hecho"], e["tipo"], e["titulo"], e["estado"], e.get("fragmento") or ""))
        n = r["meta"]["total"]
        self.total.config(text=f"{n} resultado(s)" + (" — mostrando 200" if n > 200 else ""))


class Tablero(tk.Toplevel):
    """CU-14: K1 a K12. Doble clic en un indicador abre la lista que lo explica."""

    def __init__(self, padre, cliente: ClienteApi):
        super().__init__(padre)
        self.c = cliente
        self.title("Tablero")
        self.geometry("780x520")
        f = ttk.Frame(self, padding=8)
        f.pack(fill="x")
        self.desde, self.hasta = tk.StringVar(), tk.StringVar()
        ttk.Label(f, text="Desde").pack(side="left")
        ttk.Entry(f, textvariable=self.desde, width=11).pack(side="left", padx=4)
        ttk.Label(f, text="Hasta").pack(side="left")
        ttk.Entry(f, textvariable=self.hasta, width=11).pack(side="left", padx=4)
        ttk.Button(f, text="Esta semana", command=self.cargar_semana).pack(side="left", padx=4)
        ttk.Button(f, text="Hoy", command=self.cargar_hoy).pack(side="left")
        ttk.Button(f, text="Este mes", command=self.cargar_mes).pack(side="left", padx=4)
        ttk.Button(f, text="Aplicar rango", command=self.cargar).pack(side="left")
        self.info = ttk.Label(f, text="")
        self.info.pack(side="right")
        self.tabla = ttk.Treeview(self, columns=("id", "nombre", "valor", "detalle"), show="headings")
        for k, t, a in (("id", "", 45), ("nombre", "Indicador", 230), ("valor", "Valor", 130), ("detalle", "Detalle", 330)):
            self.tabla.heading(k, text=t)
            self.tabla.column(k, width=a, anchor="w")
        self.tabla.pack(fill="both", expand=True, padx=8, pady=8)
        self.tabla.bind("<Double-1>", self._abrir)
        ttk.Label(self, text="K3, K4, K8, K9 y K11 son del momento actual y no dependen del rango.").pack(pady=(0, 6))
        self.cargar()

    def cargar_semana(self):
        self.desde.set(""), self.hasta.set("")
        self.cargar()

    def cargar_hoy(self):
        self.desde.set(date.today().isoformat()), self.hasta.set(date.today().isoformat())
        self.cargar()

    def cargar_mes(self):
        hoy = date.today()
        self.desde.set(hoy.replace(day=1).isoformat()), self.hasta.set(hoy.isoformat())
        self.cargar()

    @staticmethod
    def _detalle(i: dict) -> str:
        d = i.get("detalle") or {}
        if i["id"] == "K1":
            return ", ".join(f"{t} {n}" for t, n in d["por_tipo"].items())
        if i["id"] == "K2":
            return f"con seguimiento {d['con_seguimiento']} · informativos {d['informativos']}"
        if i["id"] == "K5":
            return f"{d['cerrados']} cerrados · " + ", ".join(f"{t} {h} h" for t, h in d["por_tipo"].items())
        if i["id"] == "K7":
            return f"{d['cumplidos_a_tiempo']} de {d['total']} a tiempo"
        if i["id"] == "K9":
            return ", ".join(f"{p['nombre']} {p['abiertos']}" for p in d["por_responsable"])
        if i["id"] == "K10":
            return ", ".join(f"{a['nombre']} {a['total']}" for a in d["top"])
        if i["id"] == "K11" and d:
            return f"{d['folio']} — {d['titulo']}"
        return ""

    def cargar(self):
        try:
            r = self.c.tablero(self.desde.get().strip() or None, self.hasta.get().strip() or None)
        except ErrorApi as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return
        self.rango = (r["desde"], r["hasta"])
        self.info.config(text=f"Rango {r['desde']} a {r['hasta']}")
        self.tabla.delete(*self.tabla.get_children())
        for i in r["indicadores"]:
            valor = "sin datos" if i["valor"] is None else f"{i['valor']} {i.get('unidad') or ''}".strip()
            self.tabla.insert("", "end", iid=i["id"], values=(i["id"], i["nombre"], valor, self._detalle(i)))

    def _abrir(self, _e):
        sel = self.tabla.selection()
        if sel:
            ListaKpi(self, self.c, sel[0], *self.rango)


class ListaKpi(tk.Toplevel):
    def __init__(self, padre, cliente: ClienteApi, kid: str, desde: str, hasta: str):
        super().__init__(padre)
        self.c = cliente
        try:
            r = cliente.lista_kpi(kid, desde, hasta)
        except ErrorApi as ex:
            messagebox.showerror("Error", str(ex), parent=padre)
            self.destroy()
            return
        self.title(f"{kid} — {r['nombre']}")
        self.geometry("860x420")
        if not r["eventos"] and not r["compromisos"]:
            ttk.Label(self, text=r.get("texto_vacio") or "Sin resultados", padding=20).pack()
            return
        cols = ("folio", "titulo", "estado", "extra")
        t = ttk.Treeview(self, columns=cols, show="headings")
        for k, h, a in (("folio", "Folio", 110), ("titulo", "Título / compromiso", 430), ("estado", "Estado", 100), ("extra", "", 190)):
            t.heading(k, text=h)
            t.column(k, width=a, anchor="w")
        for e in r["eventos"]:
            t.insert("", "end", iid=e["folio"], values=(e["folio"], e["titulo"], e["estado"], e["fecha_hecho"]))
        for c in r["compromisos"]:
            t.insert("", "end", values=(c["evento_folio"], c["descripcion"],
                                        "VENCIDO" if c["vencido"] else c["estado"],
                                        f"{c['fecha_limite']} · {c['responsable']['nombre']}"))
        t.pack(fill="both", expand=True, padx=8, pady=8)
        t.bind("<Double-1>", lambda _e: self._abrir(t))

    def _abrir(self, t):
        sel = t.selection()
        if sel:
            Detalle(self, self.c, t.item(sel[0])["values"][0])


class Administracion(tk.Toplevel):
    """CU-16, CU-17 y CU-18. Usuarios y claves de API: solo el jefe. Áreas y subtipos: encargado y jefe."""

    def __init__(self, padre, cliente: ClienteApi):
        super().__init__(padre)
        self.c = cliente
        self.es_jefe = cliente.usuario["rol"] == "jefe"
        self.title("Administración")
        self.geometry("820x480")
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.t_areas = self._pestana(nb, "Áreas", ("nombre", "activa"), ("Área", "Activa"), (400, 100),
                                     [("Agregar…", self.area_nueva), ("Renombrar…", self.area_renombrar),
                                      ("Activar / desactivar", self.area_alternar)])
        self.t_sub = self._pestana(nb, "Subtipos", ("tipo", "nombre", "activo", "origen"),
                                   ("Tipo", "Subtipo", "Activo", "Origen"), (120, 260, 90, 120),
                                   [("Agregar…", self.sub_nuevo), ("Activar / desactivar", self.sub_alternar)])
        if self.es_jefe:
            self.t_usr = self._pestana(nb, "Usuarios", ("nombre", "correo", "rol", "activo"),
                                       ("Nombre", "Correo", "Rol", "Activo"), (200, 240, 100, 80),
                                       [("Agregar…", self.usr_nuevo), ("Cambiar rol…", self.usr_rol),
                                        ("Restablecer clave…", self.usr_clave), ("Activar / desactivar", self.usr_alternar)])
            self.t_api = self._pestana(nb, "Claves API", ("nombre", "prefijo", "creada", "ultimo", "usos", "estado"),
                                       ("Nombre", "Empieza con", "Creada", "Último uso", "Usos", "Estado"),
                                       (170, 90, 120, 130, 60, 90),
                                       [("Emitir clave…", self.api_nueva), ("Revocar", self.api_revocar)])
        self.recargar()

    def _pestana(self, nb, titulo, cols, encabezados, anchos, botones):
        marco = ttk.Frame(nb)
        nb.add(marco, text=titulo)
        barra = ttk.Frame(marco, padding=6)
        barra.pack(fill="x")
        for texto, cmd in botones:
            ttk.Button(barra, text=texto, command=cmd).pack(side="left", padx=3)
        t = ttk.Treeview(marco, columns=cols, show="headings")
        for k, h, a in zip(cols, encabezados, anchos):
            t.heading(k, text=h)
            t.column(k, width=a, anchor="w")
        t.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        return t

    def _hacer(self, accion):
        try:
            accion()
        except ErrorApi as ex:
            messagebox.showerror("No se pudo", str(ex), parent=self)
            return
        self.recargar()

    def _sel(self, tabla):
        s = tabla.selection()
        return s[0] if s else None

    def recargar(self):
        try:
            self._llenar()
        except ErrorApi as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _llenar(self):
        def poner(t, filas):
            t.delete(*t.get_children())
            for iid, vals in filas:
                t.insert("", "end", iid=iid, values=vals)
        poner(self.t_areas, [(a["id"], (a["nombre"], "sí" if a["activa"] else "no")) for a in self.c.areas_todas()])
        poner(self.t_sub, [(f"{s['tipo']}/{s['nombre']}", (s["tipo"], s["nombre"], "sí" if s["activo"] else "no",
                                                           "de fábrica" if s["base"] else "agregado"))
                           for s in self.c.subtipos(incluir_inactivos=True)])
        if self.es_jefe:
            poner(self.t_usr, [(u["id"], (u["nombre"], u["correo"], u["rol"], "sí" if u["activo"] else "no"))
                               for u in self.c.usuarios()])
            poner(self.t_api, [(k["id"], (k["nombre"], k["prefijo"] + "…", (k["creado_en"] or "")[:10],
                                          (k["ultimo_uso"] or "nunca")[:16].replace("T", " "), k["usos"],
                                          "revocada" if k["revocada_en"] else "activa")) for k in self.c.claves_api()])

    # --- áreas
    def area_nueva(self):
        n = simpledialog.askstring("Área", "Nombre del área:", parent=self)
        if n:
            self._hacer(lambda: self.c.crear_area(n))

    def area_renombrar(self):
        i = self._sel(self.t_areas)
        n = i and simpledialog.askstring("Área", "Nuevo nombre:", parent=self)
        if n:
            self._hacer(lambda: self.c.modificar_area(i, {"nombre": n}))

    def area_alternar(self):
        i = self._sel(self.t_areas)
        if i:
            activa = self.t_areas.item(i)["values"][1] == "sí"
            self._hacer(lambda: self.c.modificar_area(i, {"activa": not activa}))

    # --- subtipos
    def sub_nuevo(self):
        tipo = simpledialog.askstring("Subtipo", f"Tipo ({', '.join(TIPOS)}):", parent=self)
        nombre = tipo and simpledialog.askstring("Subtipo", "Nombre (minúsculas, sin espacios, ej. capacitacion):", parent=self)
        if tipo and nombre:
            self._hacer(lambda: self.c.crear_subtipo(tipo.strip(), nombre.strip()))

    def sub_alternar(self):
        i = self._sel(self.t_sub)
        if i:
            tipo, nombre = i.split("/", 1)
            activo = self.t_sub.item(i)["values"][2] == "sí"
            self._hacer(lambda: self.c.activar_subtipo(tipo, nombre, not activo))

    # --- usuarios
    def usr_nuevo(self):
        nombre = simpledialog.askstring("Usuario", "Nombre:", parent=self)
        correo = nombre and simpledialog.askstring("Usuario", "Correo:", parent=self)
        rol = correo and simpledialog.askstring("Usuario", "Rol (asistente, encargado, jefe):", parent=self)
        clave = rol and simpledialog.askstring("Usuario", "Clave inicial (mínimo 8):", show="*", parent=self)
        if clave:
            self._hacer(lambda: self.c.crear_usuario(nombre, correo, rol.strip(), clave))

    def usr_rol(self):
        i = self._sel(self.t_usr)
        rol = i and simpledialog.askstring("Rol", "Nuevo rol (asistente, encargado, jefe):", parent=self)
        if rol:
            self._hacer(lambda: self.c.modificar_usuario(i, {"rol": rol.strip()}))

    def usr_clave(self):
        i = self._sel(self.t_usr)
        clave = i and simpledialog.askstring("Clave", "Nueva clave (mínimo 8):", show="*", parent=self)
        if clave:
            self._hacer(lambda: self.c.modificar_usuario(i, {"clave": clave}))

    def usr_alternar(self):
        i = self._sel(self.t_usr)
        if i:
            activo = self.t_usr.item(i)["values"][3] == "sí"
            self._hacer(lambda: self.c.modificar_usuario(i, {"activo": not activo}))

    # --- claves de API
    def api_nueva(self):
        n = simpledialog.askstring("Clave de API", "¿Para qué programa es? (nombre):", parent=self)
        if not n:
            return
        try:
            k = self.c.crear_clave_api(n)
        except ErrorApi as ex:
            messagebox.showerror("No se pudo", str(ex), parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(k["clave"])
        messagebox.showinfo(
            "Clave emitida",
            f"{k['clave']}\n\nCópiala ahora (ya está en el portapapeles): no se volverá a mostrar.\n"
            "El programa externo la envía en el encabezado X-API-Key.", parent=self)
        self.recargar()

    def api_revocar(self):
        i = self._sel(self.t_api)
        if i and messagebox.askyesno("Revocar", "El programa que use esta clave perderá el acceso de inmediato. ¿Continuar?", parent=self):
            self._hacer(lambda: self.c.revocar_clave_api(i))


def main():
    login = Login()
    login.mainloop()
    if login.cliente:
        Principal(login.cliente).mainloop()


if __name__ == "__main__":
    main()
