"""Bitácora TI — aplicación de escritorio (Tkinter).
Uso:  python -m desktop.app
Habla con la API (uvicorn app.main:app) y no toca la base de datos directamente.
"""
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

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
        if not sel:
            return
        try:
            e = self.c.evento(sel[0])
        except ErrorApi as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return
        v = tk.Toplevel(self)
        v.title(e["folio"])
        v.geometry("520x420")
        t = tk.Text(v, wrap="word", padx=10, pady=10)
        t.pack(fill="both", expand=True)
        lineas = [
            f"{e['folio']}  ·  {e['tipo']}" + (f" / {e['subtipo']}" if e["subtipo"] else ""),
            f"Fecha del hecho: {e['fecha_hecho']}",
            f"Estado: {e['estado']}" + (f"   Prioridad: {e['prioridad']}" if e["prioridad"] else ""),
            f"Área: {(e['area_origen'] or {}).get('nombre', '—')}   Solicitante: {e['solicitante'] or '—'}",
            f"Registró: {e['autor']['nombre']}   Responsable: {(e['responsable'] or {}).get('nombre', '—')}",
            f"Referencia: {e['referencia'] or '—'}",
            "", e["titulo"], "", e["descripcion"],
        ]
        t.insert("1.0", "\n".join(lineas))
        t.config(state="disabled")

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


def main():
    login = Login()
    login.mainloop()
    if login.cliente:
        Principal(login.cliente).mainloop()


if __name__ == "__main__":
    main()
