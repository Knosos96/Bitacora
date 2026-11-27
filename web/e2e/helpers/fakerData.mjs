import { fakerES as faker } from "@faker-js/faker";

const TIPOS_EVENTO = ["solicitud", "incidencia", "tarea", "visita", "otro"];

function sufijoUnico() {
  return `${Date.now().toString(36).slice(-4)}${faker.string.alphanumeric(3).toLowerCase()}`;
}

export function fechaFutura(dias = 5) {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  return d.toISOString().slice(0, 10);
}

export function claveSeguraFalsa() {
  return `${faker.string.alpha({ length: 5, casing: "mixed" })}${faker.string.numeric(3)}Z9`;
}

export function generarCatalogosFalsos() {
  const tag = sufijoUnico();
  const areaBase = faker.commerce.department().replace(/[^A-Za-z0-9 ]/g, "").trim() || "Soporte";
  const subBase = (faker.hacker.noun().toLowerCase().replace(/[^a-z0-9]/g, "") || "red").slice(0, 14);
  return {
    areaNombre: `Area ${areaBase} ${tag}`,
    areaRenombrada: `Area ${areaBase} Edit ${tag}`,
    subtipoTipo: "incidencia",
    subtipoNombre: `fk_${subBase}_${tag}`.replace(/[^a-z0-9_]/g, ""),
    rolNombre: `Rol Faker ${tag}`,
    rolDescripcion: faker.company.catchPhrase().slice(0, 120),
    rolPermisos: [
      "ver_usuarios",
      "ver_kpi",
      "crear_eventos",
      "editar_cabecera",
      "cambiar_estado",
      "cancelar_cerrar",
      "reabrir_eventos",
      "gestionar_compromisos",
      "exportar_csv",
    ],
    claveApiNombre: `API Faker ${tag}`,
    claveApiDescartarNombre: `API Temp ${tag}`,
  };
}

export function generarCuatroUsuariosFalsos(rolCustomNombre) {
  const perfiles = [
    { alias: "U1 Encargado", rolTipo: "encargado", puedeTablero: true, puedeCsv: true, eliminarAlFinal: false },
    { alias: "U2 Asistente", rolTipo: "asistente", puedeTablero: false, puedeCsv: false, eliminarAlFinal: false },
    { alias: "U3 Encargado RolSwap", rolTipo: "encargado", puedeTablero: true, puedeCsv: true, eliminarAlFinal: true },
    { alias: `U4 Custom (${rolCustomNombre})`, rolTipo: "otro", puedeTablero: true, puedeCsv: true, eliminarAlFinal: true },
  ];

  return perfiles.map((p, idx) => {
    const first = faker.person.firstName();
    const last = faker.person.lastName();
    const tag = `${idx + 1}${sufijoUnico()}`;
    const slug = `${first}.${last}`.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "");
    return {
      ...p,
      nombre: `${first} ${last}`,
      correo: `${slug || "usuario"}.${tag}@zgroup-faker.com`,
      clave: claveSeguraFalsa(),
      claveNueva: claveSeguraFalsa(),
    };
  });
}

export function generarActividadUsuarioFalso(usuario, areaNombre) {
  const tag = sufijoUnico();
  const tipoPrincipal = faker.helpers.arrayElement(TIPOS_EVENTO);
  const tipoSecundario = faker.helpers.arrayElement(TIPOS_EVENTO);
  return {
    areaNombre,
    eventoPrincipal: {
      tipo: tipoPrincipal,
      solicitante: faker.person.fullName(),
      titulo: `[Faker ${tag}] ${faker.hacker.phrase().slice(0, 90)}`,
      descripcion: `${faker.lorem.paragraph()} (Generado por ${usuario.nombre})`,
      requiereSeguimiento: true,
      notaSeguimiento: `Nota Faker: ${faker.lorem.sentence()}`,
      compromisoDesc: `Compromiso Faker: ${faker.lorem.words(5)}`,
      compromisoFecha: fechaFutura(faker.number.int({ min: 2, max: 14 })),
      tituloCorregido: `[Faker ${tag}] Corregido: ${faker.company.buzzPhrase().slice(0, 75)}`,
      referenciaNueva: `REF-FK-${tag.toUpperCase()}`,
      notaCambioEstado: `Cambio de estado aleatorio: ${faker.lorem.sentence()}`,
    },
    eventoInformativo: {
      tipo: tipoSecundario,
      solicitante: faker.person.fullName(),
      titulo: `[Faker Info ${tag}] ${faker.lorem.words(5)}`,
      descripcion: faker.lorem.sentences(2),
      requiereSeguimiento: false,
    },
  };
}
