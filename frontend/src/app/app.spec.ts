import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';
import { AccesoService, Rol } from './services/acceso.service';

describe('Navegación por perfil', () => {
  it.each([
    ['OPERADOR', ['/control-acceso', '/gestion/pagos'], ['/gestion/celdas', '/gestion/cuentas']],
    ['ADMINISTRADOR', ['/gestion/celdas', '/gestion/cuentas'], ['/control-acceso', '/gestion/pagos']],
  ] as const)('muestra el menú de %s', (rol: Rol, visibles, ocultos) => {
    TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideRouter([]),
        { provide: AccesoService, useValue: { operador: signal({ id: 1, nombre: 'Prueba', rol }) } },
      ],
    });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const nav = (fixture.nativeElement as HTMLElement).querySelector('nav')!;
    for (const ruta of visibles) expect(nav.querySelector(`a[href="${ruta}"]`)).not.toBeNull();
    for (const ruta of ocultos) expect(nav.querySelector(`a[href="${ruta}"]`)).toBeNull();
  });
});
