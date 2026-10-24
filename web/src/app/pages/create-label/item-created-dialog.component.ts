import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

export interface LabelItemData {
  id: number;
  code: string;
  name: string;
  quantity_value: number;
  unit_name: string;
  storage_date: string | null;
  title?: string;
}

@Component({
  selector: 'app-item-created-dialog',
  standalone: false,
  template: `
    <h2 mat-dialog-title>{{ data.title ?? 'QR-Label' }}</h2>
    <mat-dialog-content class="content">
      <div class="qr-wrap" *ngIf="qrUrl as url">
        <img [src]="url" alt="QR Code" class="qr-img">
      </div>
      <div class="label-details">
        <div class="item-name">{{ data.name }}</div>
        <div><strong>Menge:</strong> {{ data.quantity_value }} {{ data.unit_name }}</div>
        <div *ngIf="data.storage_date"><strong>Einlagerungsdatum:</strong> {{ data.storage_date | date:'dd.MM.yyyy' }}</div>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-stroked-button (click)="print()">Etikett drucken</button>
      <button mat-raised-button color="primary" (click)="close()">Schließen</button>
    </mat-dialog-actions>
  `,
  styles: [`
    .content { display: flex; align-items: center; gap: 24px; }
    .qr-wrap { display: flex; flex: 0 0 auto; justify-content: center; }
    .qr-img { width: 160px; height: 160px; image-rendering: pixelated; }
    .label-details { display: grid; gap: 8px; min-width: 0; overflow-wrap: anywhere; }
    .item-name { font-size: 1.25rem; font-weight: 600; }
    @media print {
      mat-dialog-actions, h2[mat-dialog-title] { display: none !important; }
      .content { gap: 32px; }
      .qr-img { width: 220px; height: 220px; }
      :host { background: #fff; }
    }
    @media (max-width: 480px) {
      .content { align-items: flex-start; gap: 16px; }
      .qr-img { width: 140px; height: 140px; }
      .item-name { font-size: 1.1rem; }
    }
  `]
})
export class ItemCreatedDialogComponent {
  private readonly baseUrl = '/api';
  qrUrl: string | null = null;

  constructor(
    private dialogRef: MatDialogRef<ItemCreatedDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: LabelItemData
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
