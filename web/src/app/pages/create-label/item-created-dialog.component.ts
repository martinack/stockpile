import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-item-created-dialog',
  standalone: false,
  template: `
    <h2 mat-dialog-title>Label erstellt</h2>
    <mat-dialog-content class="content">
      <div class="meta">
        <div><strong>Name:</strong> {{ data.name }}</div>
        <div><strong>Code:</strong> {{ data.code }}</div>
        <div *ngIf="data?.warehouse_id !== undefined">
          <strong>Warehouse-ID:</strong> {{ data.warehouse_id ?? 'Keines' }}
        </div>
      </div>

      <div class="qr-wrap" *ngIf="qrUrl as url">
        <img [src]="url" alt="QR Code" class="qr-img">
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-stroked-button (click)="print()">QR drucken</button>
      <button mat-raised-button color="primary" (click)="close()">Schließen</button>
    </mat-dialog-actions>
  `,
  styles: [`
    .content { display: flex; flex-direction: column; gap: 16px; }
    .qr-wrap { display: flex; justify-content: center; }
    .qr-img { width: 220px; height: 220px; image-rendering: pixelated; }
    @media print {
      mat-dialog-actions, h2[mat-dialog-title], .meta { display: none !important; }
      .qr-img { width: 350px; height: 350px; }
      :host { background: #fff; }
    }
  `]
})
export class ItemCreatedDialogComponent {
  // Passe diese URL bei Bedarf an deine Backend-Base an
  private readonly baseUrl = 'http://localhost:8000';
  qrUrl: string | null = null;

  constructor(
    private dialogRef: MatDialogRef<ItemCreatedDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { id: number; code: string; name: string; warehouse_id: number | null }
  ) {
    this.qrUrl = data?.code ? `${this.baseUrl}/qrcode/${data.code}` : null;
  }

  print(): void {
    // Druckt den Dialog-Inhalt. Für beste Ergebnisse kann eine eigene Print-Route verwendet werden.
    window.print();
  }

  close(): void {
    this.dialogRef.close(true);
  }
}
