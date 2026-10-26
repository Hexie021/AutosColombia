import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ControlAcceso } from './control-acceso';

const cat = {
  operadores: [{ id: 1, nombre: 'Ana' }],
  celdas: [{ id: 1, codigo: 'A01', tipo: 'AUTOMOVIL_CAMIONETA', ocupada: false }],
  resumen: { presentes: 0, libres: 80, inscritos: 4, motos_libres: 10, autos_libres: 70 },
};
const stay = {
  id: 7,
  placa: 'ABC123',
  celda: 'A01',
  celda_id: 1,
  tipo: 'AUTOMOVIL',
  cliente: 'Demo',
  entrada: '2026-10-25T15:00:00Z',
  salida: null,
  operador_entrada: 'Ana',
  operador_salida: null,
};
const state = {
  placa: 'ABC123',
  marca: 'Demo',
  modelo: 2022,
  color: 'Gris',
  tipo: 'AUTOMOVIL',
  cliente: 'Demo',
  vigencia: { inicio: '2026-10-21T15:00:00Z', vencimiento: '2026-11-21T15:00:00Z' },
  estancia: null,
};

describe('Operación EA1', () => {
  let http: HttpTestingController;
  let c: ControlAcceso;
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ControlAcceso],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    c = TestBed.createComponent(ControlAcceso).componentInstance;
    http.expectOne('/operacion/catalogos').flush(cat);
  });
  afterEach(() => http.verify());

  it('consulta la placa normalizada y asigna celda solo en el servidor', () => {
    c.cambiarPlaca(' abc123 ');
    c.buscar();
    http.expectOne('/operacion/vehiculo/ABC123').flush(state);
    c.registrarEntrada();
    c.registrarEntrada();
    const req = http.expectOne('/operacion/entrada');
    expect(req.request.body).toEqual({ placa: 'ABC123', operador_id: 1 });
    req.flush(stay);
    http.expectOne('/operacion/catalogos').flush(cat);
    expect(c.comprobante()?.id).toBe(7);
    expect(c.estado()).toBeNull();
  });
  it('descarta una consulta al cambiar la placa', () => {
    c.cambiarPlaca('ABC123');
    c.buscar();
    c.cambiarPlaca('DEF456');
    http.expectOne('/operacion/vehiculo/ABC123').flush(state);
    expect(c.estado()).toBeNull();
    c.registrarEntrada();
    http.expectNone('/operacion/entrada');
  });
  it('bloquea un ingreso sin vigencia y exige comprobante o verificación de pérdida', () => {
    c.estado.set({ ...state, vigencia: null });
    c.registrarEntrada();
    http.expectNone('/operacion/entrada');
    c.estado.set({ ...state, estancia: stay });
    c.registrarSalida();
    http.expectNone('/operacion/salida');
    c.perdido = true;
    c.documento = 'DEMO-001';
    c.motivo = 'Pérdida';
    c.registrarSalida();
    http.expectNone('/operacion/salida');
    c.verificada = true;
    c.registrarSalida();
    const req = http.expectOne('/operacion/salida');
    expect(req.request.body.identidad_verificada).toBe(true);
    req.flush({ ...stay, salida: '2026-10-25T16:00:00Z' });
    http.expectOne('/operacion/catalogos').flush(cat);
    expect(c.mensaje()).toContain('liberada');
  });
  it('no repite escrituras y exige consultar tras un conflicto', () => {
    c.estado.set(state);
    c.registrarEntrada();
    http
      .expectOne('/operacion/entrada')
      .flush({ detail: 'El vehículo ya está dentro.' }, { status: 409, statusText: 'Conflict' });
    http.expectOne('/operacion/catalogos').flush(cat);
    expect(c.estado()).toBeNull();
    expect(c.error()).toContain('ya está dentro');
  });
  it('filtra por fechas y placa con paginación', () => {
    c.filtroPlaca = ' abc123 ';
    c.desde = '2026-10-21';
    c.hasta = '2026-10-25';
    c.cambiarTab('historial');
    const req = http.expectOne((r) => r.url === '/operacion/estancias');
    expect(req.request.params.get('placa')).toBe('ABC123');
    expect(req.request.params.get('desde')).toBe('2026-10-21');
    req.flush({ items: [stay], total: 1, offset: 0, limit: 20 });
    http.expectOne('/operacion/catalogos').flush(cat);
    expect(c.lista().total).toBe(1);
  });
  it('reimprime el mismo número desde la API y usa hora de Bogotá', () => {
    c.reimprimir(7);
    http.expectOne('/operacion/comprobante/7').flush(stay);
    expect(c.comprobante()?.id).toBe(7);
    expect(c.fecha(stay.entrada)).toContain('10:00');
  });
});
