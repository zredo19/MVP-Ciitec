// Cola de carga offline (RF-010): mientras no hay red, los documentos se guardan
// en IndexedDB y se reenvían al reconectar. Las cargas son append-only, así que
// no hay conflictos de escritura.
import { openDB } from "idb";
import { api } from "./api";

const DB = "briefings-offline";
const STORE = "cola_cargas";

async function db() {
  return openDB(DB, 1, {
    upgrade(d) {
      if (!d.objectStoreNames.contains(STORE)) d.createObjectStore(STORE, { autoIncrement: true });
    },
  });
}

export async function encolarCargas(files: File[], nivel: string) {
  const d = await db();
  for (const f of files) {
    await d.add(STORE, { name: f.name, type: f.type, nivel, blob: f });
  }
}

export async function pendientes(): Promise<number> {
  const d = await db();
  return d.count(STORE);
}

export async function sincronizar(): Promise<number> {
  const d = await db();
  const keys = await d.getAllKeys(STORE);
  let enviados = 0;
  for (const k of keys) {
    const item: any = await d.get(STORE, k);
    const file = new File([item.blob], item.name, { type: item.type });
    try {
      await api.upload([file], item.nivel);
      await d.delete(STORE, k);
      enviados++;
    } catch {
      break; // sigue sin red; se reintenta luego
    }
  }
  return enviados;
}

// Reintenta automáticamente al volver la conexión.
window.addEventListener("online", () => {
  sincronizar().catch(() => {});
});
