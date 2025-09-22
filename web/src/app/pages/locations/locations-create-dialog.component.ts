import { Component } from '@angular/core';
import { MatDialogRef } from '@angular/material/dialog';
import { LocationsService } from '../../services/locations.service';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-locations-create-dialog',
  standalone: false,
  templateUrl: './locations-create-dialog.component.html',
  styleUrls: ['./locations-create-dialog.component.scss']
})
export class LocationsCreateDialogComponent {
  name = '';

  constructor(
    private dialogRef: MatDialogRef<LocationsCreateDialogComponent>,
    private locationsService: LocationsService,
    private snackBar: MatSnackBar
  ) {}

  save(): void {
    const trimmed = this.name.trim();
    if (!trimmed) {
      this.snackBar.open('Bitte einen gültigen Namen eingeben.', 'OK', { duration: 3000, verticalPosition: "top" });
      return;
    }
    this.locationsService.create(trimmed).subscribe({
      next: (loc) => {
        this.snackBar.open('Standort erfolgreich erstellt.', 'OK', { duration: 3000, verticalPosition: "top" });
        this.dialogRef.close(loc);
      },
      error: () => {
        this.snackBar.open('Fehler beim Erstellen des Standorts.', 'OK', { duration: 3000, verticalPosition: "top" });
        this.dialogRef.close(null);
      }
    });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
