import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, ElementRef, afterRenderEffect, computed, inject, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { CeldasService } from '../services/celdas.service';
import { Celda, CeldaCrear, FiltrosCeldas } from '../models/celda';
import { ErrorApi } from '../models/vehiculo';

const nonBlank: ValidatorFn = (control) =>
  typeof control.value === 'string' && control.value.trim() ? null : { required: true };
type Field = keyof CeldaCrear;

@Component({
  selector: 'app-celdas',
  imports: [ReactiveFormsModule],
  templateUrl: './celdas.html',
  styleUrl: './celdas.css',
})
export class Celdas {
  private readonly api = inject(CeldasService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  readonly fields = [
    { key: 'codigo' as const, label: 'Código' },
    { key: 'tipo' as const, label: 'Tipo' },
  ];
  readonly types = [
    { value: 'AUTOMOVIL_CAMIONETA', label: 'Automóvil / camioneta' },
    { value: 'MOTO', label: 'Moto' },
  ];

  typeLabel(value: string): string {
    return this.types.find((type) => type.value === value)?.label ?? value;
  }
  readonly form = this.fb.group({
    codigo: this.fb.nonNullable.control('', nonBlank),
    tipo: this.fb.nonNullable.control('', nonBlank),
  });
  readonly filtersForm = this.fb.nonNullable.group({
    codigo: '',
    tipo: '',
    habilitada: '',
    ocupada: '',
  });
  private filters: FiltrosCeldas = this.filtersForm.getRawValue();
  readonly items = signal<Celda[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly limit = 10;
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly busy = computed(() => this.loading() || this.saving());
  readonly showForm = signal(false);
  readonly editing = signal<number | null>(null);
  readonly pendingChange = signal<Celda | null>(null);
  readonly listError = signal('');
  readonly actionError = signal('');
  readonly warning = signal('');
  readonly success = signal('');
  private readonly dialog = viewChild.required<ElementRef<HTMLDialogElement>>('cellDialog');
  readonly dialogTitle = computed(() => {
    const cell = this.pendingChange();
    if (cell) return `${cell.habilitada ? 'Deshabilitar' : 'Habilitar'} celda ${cell.codigo}`;
    return this.editing() === null ? 'Registrar celda' : 'Editar celda';
  });
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));

  constructor() {
    afterRenderEffect(() => {
      const dialog = this.dialog().nativeElement;
      if (this.showForm() || this.pendingChange()) {
        if (!dialog.open) dialog.showModal();
      } else if (dialog.open) {
        dialog.close();
      }
    });
    this.load();
  }

  applyFilters(): void {
    if (this.busy()) return;
    const values = this.filtersForm.getRawValue();
    this.filters = { ...values, codigo: values.codigo.trim() };
    this.load(0);
  }

  load(offset = this.offset()): void {
    if (this.busy()) return;
    this.loading.set(true);
    this.listError.set('');
    this.api
      .list(offset, this.limit, this.filters)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          if (offset > 0 && offset >= data.total) {
            this.load(Math.max(0, Math.floor((data.total - 1) / this.limit) * this.limit));
            return;
          }
          this.items.set(data.items);
          this.total.set(data.total);
          this.offset.set(offset);
        },
        error: (error) => {
          this.loading.set(false);
          this.listError.set(this.errorMessage(error));
        },
      });
  }

  newCell(): void {
    if (this.busy()) return;
    this.form.reset();
    this.editing.set(null);
    this.showForm.set(true);
    this.pendingChange.set(null);
    this.actionError.set('');
    this.warning.set('');
    this.success.set('');
  }

  edit(cell: Celda): void {
    if (this.busy() || cell.tiene_historial) return;
    this.loading.set(true);
    this.actionError.set('');
    this.warning.set('');
    this.success.set('');
    this.pendingChange.set(null);
    this.api
      .get(cell.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          this.editing.set(data.id);
          this.form.reset(data);
          this.showForm.set(true);
        },
        error: (error) => {
          this.loading.set(false);
          this.actionError.set(this.errorMessage(error));
        },
      });
  }

  cancel(): void {
    if (this.busy()) return;
    this.showForm.set(false);
    this.pendingChange.set(null);
    this.actionError.set('');
    this.warning.set('');
  }

  handleEscape(event: Event): void {
    event.preventDefault();
    this.cancel();
  }

  fieldError(field: Field): string {
    const control = this.form.controls[field];
    if (!control.touched || !control.errors) return '';
    if (control.errors['server']) return String(control.errors['server']);
    if (control.errors['required']) return 'Este campo es obligatorio y no puede estar vacío.';
    return 'Revisa este campo.';
  }

  save(): void {
    if (this.busy()) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      this.actionError.set('');
      this.warning.set('Revisa los campos señalados antes de guardar la celda.');
      return;
    }
    const value = this.form.getRawValue();
    const payload: CeldaCrear = {
      codigo: value.codigo.trim().toUpperCase(),
      tipo: value.tipo.trim(),
    };
    this.form.controls.codigo.setValue(payload.codigo);
    this.saving.set(true);
    this.actionError.set('');
    this.warning.set('');
    this.success.set('');
    const id = this.editing();
    const request = id === null ? this.api.create(payload) : this.api.update(id, payload);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (cell) => {
        this.saving.set(false);
        this.showForm.set(false);
        this.success.set(
          `Celda ${cell.codigo} ${id === null ? 'registrada' : 'actualizada'} correctamente.`,
        );
        this.load();
      },
      error: (error: HttpErrorResponse) => {
        this.saving.set(false);
        this.actionError.set(this.errorMessage(error));
        if (error.status === 409 && error.error?.detail === 'Ya existe una celda con ese código.')
          this.setFieldError('codigo', 'Ya existe una celda con ese código.');
        const body = error.error as ErrorApi | null;
        if (error.status === 422 && Array.isArray(body?.detail)) {
          for (const issue of body.detail) {
            const field = issue.loc.at(-1);
            if (typeof field === 'string' && Object.hasOwn(this.form.controls, field)) {
              this.setFieldError(
                field as Field,
                'El servicio rechazó este valor. Revisa el campo.',
              );
            }
          }
        }
      },
    });
  }

  private setFieldError(field: Field, message: string): void {
    this.form.controls[field].setErrors({ server: message });
    this.form.controls[field].markAsTouched();
  }

  confirmChange(cell: Celda): void {
    if (this.busy() || (cell.habilitada && cell.ocupada)) return;
    this.pendingChange.set(cell);
    this.showForm.set(false);
    this.actionError.set('');
    this.success.set('');
  }

  changeEnabled(): void {
    const cell = this.pendingChange();
    if (!cell || this.busy()) return;
    this.saving.set(true);
    this.actionError.set('');
    this.api
      .setEnabled(cell.id, !cell.habilitada)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated) => {
          this.saving.set(false);
          this.pendingChange.set(null);
          this.success.set(`Celda ${cell.codigo} ${updated.habilitada ? 'habilitada' : 'deshabilitada'}.`);
          this.load();
        },
        error: (error) => {
          this.saving.set(false);
          this.actionError.set(this.errorMessage(error));
          if (error.status === 404 || error.status === 409) {
            this.pendingChange.set(null);
            this.load();
          }
        },
      });
  }

  private errorMessage(error: HttpErrorResponse): string {
    if (error.status === 404) return 'La celda ya no existe. Actualiza el listado.';
    if (error.status === 409) {
      const detail = (error.error as ErrorApi | null)?.detail;
      return typeof detail === 'string' ? detail : 'La operación entra en conflicto con el estado actual de la celda.';
    }
    if (error.status === 422)
      return 'Revisa los datos: hay campos que no cumplen las validaciones.';
    return 'No se pudo conectar con el servicio. Comprueba la conexión y actualiza el listado antes de reintentar.';
  }
}

