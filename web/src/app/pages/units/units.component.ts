import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Unit, UnitsService } from '../../services/units.service';

@Component({ selector: 'app-units', standalone: false, templateUrl: './units.component.html', styleUrl: './units.component.scss' })
export class UnitsComponent implements OnInit {
  units: Unit[] = [];
  name = '';
  loading = false;
  constructor(private service: UnitsService, private snack: MatSnackBar, private cdr: ChangeDetectorRef) {}
  ngOnInit(): void { this.reload(); }
  reload(): void { this.loading = true; this.service.list().subscribe({ next: units => { this.units = units; this.loading = false; this.cdr.detectChanges(); }, error: () => { this.loading = false; this.snack.open('Einheiten konnten nicht geladen werden.', 'OK'); this.cdr.detectChanges(); } }); }
  create(): void { const name = this.name.trim(); if (!name) return; this.service.create(name).subscribe({ next: () => { this.name = ''; this.reload(); }, error: error => this.snack.open(error.error?.detail ?? 'Einheit konnte nicht erstellt werden.', 'OK') }); }
  remove(unit: Unit): void { if (confirm(`Einheit „${unit.name}“ deaktivieren?`)) this.service.remove(unit.id).subscribe({ next: () => this.reload(), error: () => this.snack.open('Einheit konnte nicht deaktiviert werden.', 'OK') }); }
}
