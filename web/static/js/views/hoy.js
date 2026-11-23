import { TIPOS, esc, hoy } from "../services/api.js";
import { $, cargarSubtipos, tablaEventos, toast } from "../components/ui.js";

export async function vistaHoy(box, { api, actualizarAviso }) {
  const d = hoy();
  const [areas, eventos] = await Promise.all([
    api.areas(),
    api.eventos({ desde: d, hasta: d, page_size: 200 }),
  ]);

  box.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="section-title">Jornada de hoy</h1>
        <p class="section-sub">Registra nuevos eventos del área y consulta la actividad diaria.</p>
      </div>
      <span class="count-pill" id="hoy-contador">${esc(eventos.meta.total)} evento(s)</span>
    </div>

    <section class="panel">
      <div class="panel-header">
        <h2>Nuevo evento</h2>
      </div>
      <form id="form-alta" class="stack">
        <div class="grid-4">
          <label class="field">Tipo
            <select name="tipo">${TIPOS.map((t) => `<option value="${t}">${t}</option>`).join("")}</select>
          </label>
          <label class="field">Subtipo
            <select name="subtipo"><option value="">—</option></select>
          </label>
          <label class="field">Área de origen
            <select name="area_id">
              <option value="">—</option>
              ${areas.map((a) => `<option value="${a.id}">${esc(a.nombre)}</option>`).join("")}
            </select>
          </label>
          <label class="field">Solicitante
            <input name="solicitante_nombre" placeholder="Nombre de quien solicita" />
          </label>
        </div>

        <label class="field">Título
          <input name="titulo" required maxlength="200" placeholder="Resumen breve del evento" />
        </label>

        <label class="field">Descripción
          <textarea name="descripcion" required placeholder="Detalla lo ocurrido, acciones realizadas o contexto relevante…"></textarea>
        </label>

        <div class="row spread">
          <label class="check-row">
            <input type="checkbox" name="requiere_seguimiento" />
            <span>Requiere seguimiento</span>
          </label>
          <button class="btn primary" type="submit">Guardar evento</button>
        </div>
      </form>
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2>Eventos registrados</h2>
        <div class="filters-bar">
          <input type="date" id="filtro-desde" value="${d}" aria-label="Desde" />
          <input type="date" id="filtro-hasta" value="${d}" aria-label="Hasta" />
          <select id="filtro-tipo" aria-label="Tipo">
            <option value="">Todos los tipos</option>
            ${TIPOS.map((t) => `<option value="${t}">${t}</option>`).join("")}
          </select>
          <button type="button" class="btn soft" id="btn-filtrar">Filtrar</button>
          <button type="button" class="btn ghost" id="btn-hoy">Hoy</button>
        </div>
      </div>
      <div id="lista-hoy"></div>
    </section>`;

  const pintar = (r) => {
    $("#lista-hoy").innerHTML = tablaEventos(r.data, { vacio: "No hay eventos registrados para este rango." });
    const pill = $("#hoy-contador");
    if (pill) pill.textContent = `${r.meta.total} evento(s)`;
  };

  pintar(eventos);
  await cargarSubtipos(api, $("#form-alta [name=tipo]").value, $("#form-alta [name=subtipo]"));

  $("#form-alta [name=tipo]").addEventListener("change", async (e) => {
    await cargarSubtipos(api, e.target.value, $("#form-alta [name=subtipo]"));
  });

  $("#form-alta").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('[type="submit"]');
    btn.disabled = true;
    const fd = new FormData(e.target);
    try {
      const ev = await api.crearEvento({
        tipo: fd.get("tipo"),
        subtipo: fd.get("subtipo") || null,
        titulo: fd.get("titulo").trim(),
        descripcion: fd.get("descripcion").trim(),
        area_id: fd.get("area_id") || null,
        solicitante_nombre: fd.get("solicitante_nombre").trim() || null,
        requiere_seguimiento: fd.get("requiere_seguimiento") === "on",
      });
      toast(`Evento guardado: ${ev.folio}`, "ok");
      e.target.reset();
      await cargarSubtipos(api, TIPOS[0], $("#form-alta [name=subtipo]"));
      const fechaHoy = hoy();
      $("#filtro-desde").value = fechaHoy;
      $("#filtro-hasta").value = fechaHoy;
      $("#filtro-tipo").value = "";
      const r = await api.eventos({ desde: fechaHoy, hasta: fechaHoy, page_size: 200 });
      pintar(r);
      actualizarAviso();
    } catch (ex) {
      toast(ex.message, "error");
    } finally {
      btn.disabled = false;
    }
  });

  const recargarFiltro = async () => {
    try {
      const params = {
        desde: $("#filtro-desde").value || undefined,
        hasta: $("#filtro-hasta").value || undefined,
        tipo: $("#filtro-tipo").value || undefined,
        page_size: 200,
      };
      pintar(await api.eventos(params));
    } catch (ex) {
      toast(ex.message, "error");
    }
  };

  $("#btn-filtrar").onclick = recargarFiltro;
  $("#btn-hoy").onclick = () => {
    $("#filtro-desde").value = hoy();
    $("#filtro-hasta").value = hoy();
    $("#filtro-tipo").value = "";
    recargarFiltro();
  };
}

