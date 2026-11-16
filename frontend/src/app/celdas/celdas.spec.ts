import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Celdas } from './celdas';

describe('Gestión de celdas', () => {
  let fixture: ComponentFixture<Celdas>;
  let http: HttpTestingController;
  const cell = { id: 1, codigo: 'A-01', tipo: 'AUTOMOVIL_CAMIONETA', habilitada: true, ocupada: false, tiene_historial: false };
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Celdas],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Celdas);
    fixture.detectChanges();
    http
      .expectOne('/celdas?offset=0&limit=10')
      .flush({ items: [cell], total: 1, offset: 0, limit: 10 });
  });
  afterEach(() => http.verify());

  it('crea desde el formulario HTML con código normalizado y tipo del catálogo', () => {
    fixture.componentInstance.newCell();
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    for (const [id, value] of Object.entries({
      codigo: ' a-02 ',
      tipo: 'MOTO',
    })) {
      const input = root.querySelector<HTMLInputElement | HTMLSelectElement>(`#${id}`)!;
      input.value = value;
      input.dispatchEvent(new Event(id === 'tipo' ? 'change' : 'input', { bubbles: true }));
    }
    root
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.componentInstance.save();
    const request = http.expectOne({ method: 'POST', url: '/celdas' });
    expect(request.request.body).toEqual({ codigo: 'A-02', tipo: 'MOTO' });
    request.flush({ ...cell, codigo: 'A-02' });
    http
      .expectOne('/celdas?offset=0&limit=10')
      .flush({ items: [cell], total: 1, offset: 0, limit: 10 });
    expect(fixture.componentInstance.success()).toContain('registrada');
  });

  it('rechaza blancos y muestra duplicados junto al código', () => {
    const c = fixture.componentInstance;
    c.newCell();
    c.form.setValue({ codigo: ' ', tipo: ' ' });
    c.save();
    expect(c.form.invalid).toBe(true);
    c.form.setValue({ codigo: 'A-01', tipo: 'MOTO' });
    c.save();
    http.expectOne('/celdas').flush({ detail: 'Ya existe una celda con ese código.' }, { status: 409, statusText: 'Conflict' });
    expect(c.fieldError('codigo')).toContain('Ya existe');
  });

  it('edita mediante PATCH y recarga la lista', () => {
    const c = fixture.componentInstance;
    c.edit(cell);
    http.expectOne('/celdas/1').flush(cell);
    c.form.controls.tipo.setValue('MOTO');
    c.save();
    const request = http.expectOne({ method: 'PATCH', url: '/celdas/1' });
    expect(request.request.body.id).toBeUndefined();
    request.flush({ ...cell, tipo: 'MOTO' });
    http
      .expectOne('/celdas?offset=0&limit=10')
      .flush({ items: [cell], total: 1, offset: 0, limit: 10 });
  });

  it('requiere confirmación para deshabilitar y conserva la celda', () => {
    const c = fixture.componentInstance;
    c.confirmChange(cell);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alertdialog"]').textContent).toContain(
      'A-01',
    );
    c.cancel();
    http.expectNone((request) => request.method === 'PATCH');
    c.confirmChange(cell);
    c.changeEnabled();
    const request = http.expectOne({ method: 'PATCH', url: '/celdas/1/habilitacion' });
    expect(request.request.body).toEqual({ habilitada: false });
    const disabled = { ...cell, habilitada: false };
    request.flush(disabled);
    http
      .expectOne('/celdas?offset=0&limit=10')
      .flush({ items: [disabled], total: 1, offset: 0, limit: 10 });
    expect(c.success()).toContain('deshabilitada');
  });

  it('envía los filtros y vuelve a la primera página', () => {
    const c = fixture.componentInstance;
    c.filtersForm.setValue({ codigo: ' A-0 ', tipo: 'MOTO', habilitada: 'false', ocupada: 'false' });
    c.applyFilters();
    http.expectOne('/celdas?offset=0&limit=10&codigo=A-0&tipo=MOTO&habilitada=false&ocupada=false')
      .flush({ items: [], total: 0, offset: 0, limit: 10 });
  });
});
