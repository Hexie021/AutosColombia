import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { GestionCuentas } from './gestion-cuentas';

describe('Cuentas de operador', () => {
  it('consulta, crea y desactiva una cuenta desde la pantalla', async () => {
    TestBed.configureTestingModule({
      imports: [GestionCuentas],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(GestionCuentas);
    const http = TestBed.inject(HttpTestingController);
    const pantalla = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();

    const url = '/acceso/cuentas';
    const listado = url + '?offset=0&limit=20';
    http.expectOne(listado).flush({ items: [], total: 0 });
    fixture.detectChanges();
    const pulsar = (texto: string) => {
      const boton = [...pantalla.querySelectorAll('button')].find((b) => b.textContent?.trim() === texto);
      expect(boton).toBeDefined();
      boton!.click();
      fixture.detectChanges();
    };
    const enviar = () => pantalla.querySelector('form')!.dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true }),
    );

    pulsar('Crear cuenta');
    await fixture.whenStable();

    const perfil = { nombre: 'Turno tarde', telefono: '000', usuario: 'tarde' };
    const contrasena = 'nueva clave ficticia';
    for (const [campo, valor] of Object.entries({ ...perfil, contrasena, confirmacion: contrasena })) {
      const input = pantalla.querySelector<HTMLInputElement>(`input[name="${campo}"]`)!;
      input.value = valor;
      input.dispatchEvent(new Event('input'));
      fixture.detectChanges();
    }
    await fixture.whenStable();
    enviar();

    const alta = http.expectOne({ url, method: 'POST' });
    expect(alta.request.body).toEqual({ ...perfil, contrasena });
    const cuenta = { ...perfil, id: 2, activa: true };
    alta.flush(cuenta, { status: 201, statusText: 'Created' });
    http.expectOne(listado).flush({ items: [cuenta], total: 1 });
    fixture.detectChanges();
    expect(pantalla.querySelector('tbody')?.textContent).toContain('Activa');

    pulsar('Editar');
    await fixture.whenStable();
    pantalla.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click();
    enviar();

    const modificar = http.expectOne({ url: url + '/2', method: 'PUT' });
    expect(modificar.request.body.activa).toBe(false);
    modificar.flush({ ...cuenta, activa: false });
    http.expectOne(listado).flush({ items: [{ ...cuenta, activa: false }], total: 1 });
    fixture.detectChanges();
    expect(pantalla.querySelector('tbody')?.textContent).toContain('Inactiva');
    http.verify();
  });
});
