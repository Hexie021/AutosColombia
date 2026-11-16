export interface CeldaCrear {
  codigo: string;
  tipo: string;
}
export type CeldaActualizar = Partial<CeldaCrear>;
export interface Celda extends CeldaCrear {
  id: number;
  habilitada: boolean;
  ocupada: boolean;
  tiene_historial: boolean;
}
export interface FiltrosCeldas {
  codigo: string;
  tipo: string;
  habilitada: string;
  ocupada: string;
}
export interface CeldasPagina {
  items: Celda[];
  total: number;
  offset: number;
  limit: number;
}
