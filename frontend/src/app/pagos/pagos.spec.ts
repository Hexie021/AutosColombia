import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { Pagos } from './pagos';

describe('Gestión de pagos', () => {
  let fixture: ComponentFixture<Pagos>;
  let http: HttpTestingController;
  let pantalla: HTMLElement;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Pagos],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    fixture = TestBed.createComponent(Pagos);
    http = TestBed.inject(HttpTestingController);
    pantalla = fixture.nativeElement;
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function pulsar(etiqueta: string) {
    const boton = Array.from(pantalla.querySelectorAll('button')).find(
      (boton) => boton.textContent?.trim() === etiqueta,
    );
    expect(boton).toBeDefined();
    boton!.click();
    fixture.detectChanges();
  }

  it('confirma un pago y reutiliza el identificador cuando falla la confirmación', () => {
    const entrada = pantalla.querySelector('input')!;
    entrada.value = 'abc12d';
    entrada.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    pantalla.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
    const inicio = '2026-11-19T20:00:00Z';
    const vencimiento = '2026-12-19T20:00:00Z';
    http.expectOne('/pagos/vehiculo/ABC12D').flush({
      placa: 'ABC12D', tipo: 'MOTO', cliente: 'Cliente', tarifa: 100000,
      vigencia_actual: null, ultima_vigencia: null, mora_pendiente: [],
      periodo_estimado: { inicio, vencimiento },
    });
    fixture.detectChanges();
    expect(pantalla.textContent).toContain('Sin mensualidad registrada');
    pulsar('Registrar primera mensualidad');
    pulsar('Confirmar pago');
    const intento = http.expectOne('/pagos/mensualidad');
    expect(intento.request.body.importe).toBe(100000);
    pulsar('Confirmar pago');
    http.expectNone('/pagos/mensualidad');

    intento.flush({ detail: 'No se pudo completar la operación.' }, { status: 503, statusText: 'Sin conexión' });
    fixture.detectChanges();
    pulsar('Confirmar pago');
    const reintento = http.expectOne('/pagos/mensualidad');
    expect(reintento.request.body).toEqual(intento.request.body);
    reintento.flush({
      referencia: 'PAG-20261119-001', placa: 'ABC12D', tipo: 'MOTO', cliente: 'Cliente',
      operador: 'Ana', fecha: inicio, concepto: 'PRIMERA_MENSUALIDAD', importe: 100000,
      vigencia: { id: 1, inicio, vencimiento },
      estancias_regularizadas: [],
    });
    fixture.detectChanges();
    expect(pantalla.textContent).toContain('Comprobante interno');
    expect(pantalla.textContent).toContain('PAG-20261119-001');
  });
});
