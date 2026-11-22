import { Routes } from '@angular/router';

import { requiereSesion } from './services/acceso.service';

export const routes: Routes = [
  {
    path: 'iniciar-sesion',
    loadComponent: () => import('./acceso-operador').then((m) => m.AccesoOperador),
  },
  {
    path: 'mi-cuenta',
    canActivate: [requiereSesion()],
    data: { cambio: true },
    loadComponent: () => import('./acceso-operador').then((m) => m.AccesoOperador),
  },
  {
    path: 'control-acceso',
    canActivate: [requiereSesion('OPERADOR')],
    title: 'Control de acceso | Autos Colombia',
    loadComponent: () => import('./control-acceso/control-acceso').then((m) => m.ControlAcceso),
  },
  {
    path: 'gestion/cuentas',
    canActivate: [requiereSesion('ADMINISTRADOR')],
    title: 'Cuentas de operador | Autos Colombia',
    loadComponent: () => import('./gestion-cuentas').then((m) => m.GestionCuentas),
  },
  { path: 'gestion/operadores', redirectTo: 'gestion/cuentas', pathMatch: 'full' },
  {
    path: 'gestion/pagos',
    canActivate: [requiereSesion('OPERADOR')],
    title: 'Pagos | Autos Colombia',
    loadComponent: () => import('./pagos/pagos').then((m) => m.Pagos),
  },
  {
    path: 'gestion/celdas',
    canActivate: [requiereSesion('ADMINISTRADOR')],
    title: 'Celdas | Autos Colombia',
    loadComponent: () => import('./celdas/celdas').then((m) => m.Celdas),
  },
  { path: '', pathMatch: 'full', redirectTo: 'control-acceso' },
  {
    path: 'gestion/vehiculos',
    canActivate: [requiereSesion('OPERADOR')],
    title: 'Vehículos | Autos Colombia',
    loadComponent: () => import('./vehiculos/vehiculos').then((m) => m.Vehiculos),
  },
  { path: '**', redirectTo: '' },
];
