"""Bitácora TI — aplicación de escritorio (Tkinter).
Uso:  python -m desktop.app
Habla con la API (uvicorn app.main:app) y no toca la base de datos directamente.
"""
import tkinter as tk
from datetime import date
from tkinter import messagebox, simpledialog, ttk

from app.enums import SUBTIPOS, Tipo
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
        self.total = ttk.Label(f, text="")
        self.total.pack(side="right")

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
        subs = [""] + sorted(SUBTIPOS[Tipo(self.n_tipo.get())])
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
            self.e = self.c.evento_completo(self.folio)
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

    def cambiar_estado(self):
        if not self.sig.get():
            return
        nota = simpledialog.askstring("Nota", "Nota del cambio (obligatoria para en_espera y para cerrar con atajo):", parent=self)
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

    def __init__(self, padre, cliente: ClienteApi):
        super().__init__(padre)
        self.c = cliente
        self.title("Pendientes")
        self.geometry("900x520")
        barra = ttk.Frame(self, padding=8)
        barra.pack(fill="x")
        self.venc = tk.BooleanVar()
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


def main():
    login = Login()
    login.mainloop()
    if login.cliente:
        Principal(login.cliente).mainloop()


if __name__ == "__main__":
    main()
