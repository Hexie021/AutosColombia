import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

describe('Navegación', () => {
  it('ofrece acceso a la operación EA1', async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('nav a[href="/control-acceso"]')
        ?.textContent,
    ).toContain('Entrada y salida');
  });
});
