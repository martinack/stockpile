// Datei: web/src/app/pages/locations/locations.component.ts
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { LocationsService, StorageLocation } from '../../services/locations.service';
import { MatDialog } from '@angular/material/dialog';
import { LocationsCreateDialogComponent } from './locations-create-dialog.component';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-locations',
  standalone: false,
  templateUrl: './locations.component.html',
  styleUrls: ['./locations.component.scss']
})
export class LocationsComponent implements OnInit {
  locations: StorageLocation[] = [];
  loading = false;

  constructor(
    private locationsService: LocationsService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private changeDetector: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.locationsService.list().subscribe({
      next: (data) => {
        this.locations = data ?? [];
        this.loading = false;
        this.changeDetector.detectChanges();
      },
      error: () => {
        this.locations = [];
        this.loading = false;
        this.snackBar.open('Fehler beim Laden der Lagerorte.', 'OK', { duration: 4000 });
        this.changeDetector.detectChanges();
      }
    });
  }

  openCreateDialog(): void {
    const ref = this.dialog.open(LocationsCreateDialogComponent, {
      width: '400px',
      autoFocus: 'first-tabbable',
      restoreFocus: true,
      data: null
    });
    ref.afterClosed().subscribe((created) => {
      if (created) {
        this.reload();
        // Optional: Erfolg auch in dieser Komponente anzeigen
        this.snackBar.open('Lager erfolgreich angelegt.', 'OK', { duration: 3000 });
      }
    });
  }

  delete(loc: StorageLocation): void {
    if (!confirm(`Lager "${loc.name}" wirklich löschen?`)) { return; }
    this.locationsService.remove(loc.id).subscribe({
      next: () => {
        this.snackBar.open('Lager erfolgreich gelöscht.', 'OK', { duration: 3000 });
        this.reload();
      },
      error: () => {
        this.snackBar.open('Fehler beim Löschen des Lagers.', 'OK', { duration: 4000 });
      }
    });
  }
}
