import { Component, OnInit } from '@angular/core';
import { LocationsService, StorageLocation } from '../../services/locations.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import {ItemService} from '../../services/api.service';
import {MatDialog} from '@angular/material/dialog';
import {ItemCreatedDialogComponent} from './item-created-dialog.component';

@Component({
  selector: 'app-create-label',
  standalone: false,
  templateUrl: './create-label.component.html',
  styleUrl: './create-label.component.scss'
})
export class LabelCreateComponent implements OnInit {
  name = '';
  date = new Date().toISOString().split('T')[0];
  menge = '';

  locations: StorageLocation[] = [];
  locationsLoading = false;
  selectedWarehouseId: number | null = null;

  private recognition?: any;
  listening = false;

  constructor(
    private api: ItemService,
    private locationsService: LocationsService,
    private snackBar: MatSnackBar,
    private itemService: ItemService,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.loadWarehouses();
  }

  private loadWarehouses(): void {
    this.locationsLoading = true;
    this.locationsService.list().subscribe({
      next: (data) => {
        this.locations = data ?? [];
        this.locationsLoading = false;
      },
      error: () => {
        this.locations = [];
        this.locationsLoading = false;
        this.snackBar.open('Fehler beim Laden der Lagerorte.', 'OK', { duration: 3000, verticalPosition: "top" });
      }
    });
  }

  saveLabel(): void {
    const trimmed = (this.name ?? '').trim();
    if (!trimmed) {
      this.snackBar.open('Bitte einen gültigen Namen eingeben.', 'OK', { duration: 3000, verticalPosition: "top" });
      return;
    }

    const warehouseId = this.selectedWarehouseId ?? null;

    this.itemService.createItem(trimmed, warehouseId).subscribe({
      next: (created) => {
        this.snackBar.open('Label erfolgreich erstellt.', 'OK', { duration: 3000, verticalPosition: "top" });

        this.dialog.open(ItemCreatedDialogComponent, {
          width: '420px',
          data: created,
          autoFocus: false,
          restoreFocus: true
        });

      },
      error: (err) => {
        let msg = 'Fehler beim Erstellen des Labels.';
        if (err?.status === 404) {
          msg = 'Ausgewähltes Lager nicht gefunden oder inaktiv.';
        } else if (err?.error?.detail) {
          msg = err.error.detail;
        }
        this.snackBar.open(msg, 'OK', { duration: 3000, verticalPosition: "top" });
      }
    });
  }

  startVoiceInput(field: 'name' | 'menge') {
    // Vorherige Erkennung sauber stoppen
    if (this.recognition) {
      try { this.recognition.stop(); } catch {}
      this.recognition = undefined;
    }

    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    if (!SpeechRecognition) {
      this.snackBar?.open?.('Spracheingabe wird von diesem Browser nicht unterstützt.', 'OK', { duration: 3000 });
      return;
    }

    const recognition = new SpeechRecognition();
    this.recognition = recognition;

    recognition.lang = 'de-DE';
    recognition.continuous = false;       // nur eine Äußerung, endet automatisch
    recognition.interimResults = false;   // nur finale Ergebnisse

    let endGuard: any;

    recognition.onstart = () => {
      this.listening = true;
      // Fallback: falls onspeechend nicht feuert, nach 3.5s stoppen
      endGuard = setTimeout(() => {
        try { recognition.stop(); } catch {}
      }, 3500);
    };

    recognition.onresult = (event: any) => {
      // Nimm das letzte (finale) Ergebnis
      const res = event.results[event.results.length - 1];
      const text = res[0]?.transcript ?? '';
      if (field === 'name') this.name = text;
      if (field === 'menge') this.menge = text;
      // Nach Ergebnis beenden (da continuous=false meist automatisch endet)
      try { recognition.stop(); } catch {}
    };

    recognition.onspeechend = () => {
      // Stille erkannt -> stoppen
      try { recognition.stop(); } catch {}
    };

    recognition.onend = () => {
      this.listening = false;
      if (endGuard) { clearTimeout(endGuard); endGuard = undefined; }
      // Aufräumen
      if (this.recognition === recognition) {
        this.recognition = undefined;
      }
    };

    recognition.onerror = (e: any) => {
      this.listening = false;
      if (endGuard) { clearTimeout(endGuard); endGuard = undefined; }
      // Optionale, kurze Nutzerinfo
      const type = e?.error;
      let msg = 'Fehler bei der Spracheingabe.';
      if (type === 'no-speech') msg = 'Keine Sprache erkannt.';
      else if (type === 'audio-capture') msg = 'Kein Mikrofon gefunden.';
      else if (type === 'not-allowed') msg = 'Mikrofon-Zugriff verweigert.';
      this.snackBar?.open?.(msg, 'OK', { duration: 2500 });
    };

    recognition.start();

  }
}
