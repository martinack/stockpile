import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { LocationsService, StorageLocation } from '../../services/locations.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import {ItemService} from '../../services/api.service';
import {MatDialog} from '@angular/material/dialog';
import {ItemCreatedDialogComponent} from './item-created-dialog.component';
import { Unit, UnitsService } from '../../services/units.service';

@Component({
  selector: 'app-create-label',
  standalone: false,
  templateUrl: './create-label.component.html',
  styleUrl: './create-label.component.scss'
})
export class LabelCreateComponent implements OnInit, OnDestroy {
  name = '';
  date = new Date().toISOString().split('T')[0];
  quantityValue: number | null = null;
  storageDate: Date | null = new Date();

  locations: StorageLocation[] = [];
  locationsLoading = false;
  selectedWarehouseId: number | null = null;
  units: Unit[] = [];
  selectedUnitId: number | null = null;

  private recognition?: any;
  listeningField: 'name' | 'menge' | null = null;

  constructor(
    private api: ItemService,
    private locationsService: LocationsService,
    private unitsService: UnitsService,
    private snackBar: MatSnackBar,
    private itemService: ItemService,
    private dialog: MatDialog,
    private changeDetector: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.loadWarehouses();
    this.loadUnits();
  }

  private loadUnits(): void {
    this.unitsService.list().subscribe({ next: units => { this.units = units; this.selectedUnitId = units[0]?.id ?? null; this.changeDetector.detectChanges(); }, error: () => { this.snackBar.open('Bitte zuerst eine Einheit anlegen.', 'OK'); this.changeDetector.detectChanges(); } });
  }

  ngOnDestroy(): void {
    try { this.recognition?.stop(); } catch {}
    this.recognition = undefined;
  }

  private loadWarehouses(): void {
    this.locationsLoading = true;
    this.locationsService.list().subscribe({
      next: (data) => {
        this.locations = data ?? [];
        this.selectedWarehouseId = this.locations[0]?.id ?? null;
        this.locationsLoading = false;
        this.changeDetector.detectChanges();
      },
      error: () => {
        this.locations = [];
        this.locationsLoading = false;
        this.snackBar.open('Fehler beim Laden der Lagerorte.', 'OK', { duration: 3000, verticalPosition: "top" });
        this.changeDetector.detectChanges();
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
    if (this.quantityValue === null || this.quantityValue <= 0 || this.selectedUnitId === null) { this.snackBar.open('Bitte eine positive Menge und Einheit angeben.', 'OK'); return; }

    this.itemService.createItem(trimmed, this.quantityValue, this.selectedUnitId, warehouseId, this.storageDate ? this.storageDate.toISOString().slice(0, 10) : null).subscribe({
      next: (created) => {
        this.snackBar.open('Label erfolgreich erstellt.', 'OK', { duration: 3000, verticalPosition: "top" });

        this.dialog.open(ItemCreatedDialogComponent, {
          width: '420px',
          data: { ...created, title: 'Label erstellt' },
          autoFocus: false,
          restoreFocus: true
        });
        this.changeDetector.detectChanges();

      },
      error: (err) => {
        let msg = 'Fehler beim Erstellen des Labels.';
        if (err?.status === 404) {
          msg = 'Ausgewähltes Lager nicht gefunden oder inaktiv.';
        } else if (err?.error?.detail) {
          msg = err.error.detail;
        }
        this.snackBar.open(msg, 'OK', { duration: 3000, verticalPosition: "top" });
        this.changeDetector.detectChanges();
      }
    });
  }

  startVoiceInput(field: 'name' | 'menge'): void {
    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    if (!SpeechRecognition) {
      this.snackBar.open('Spracherkennung wird von diesem Browser nicht unterstützt. Bitte Chrome verwenden.', 'OK', { duration: 4500, verticalPosition: 'top' });
      return;
    }
    if (!window.isSecureContext) {
      this.snackBar.open('Spracherkennung benötigt HTTPS (localhost ist ausgenommen).', 'OK', { duration: 4500, verticalPosition: 'top' });
      return;
    }

    // A stopped older instance may still emit onend; its callbacks are ignored.
    if (this.recognition) {
      try { this.recognition.stop(); } catch {}
    }

    const recognition = new SpeechRecognition();
    this.recognition = recognition;

    recognition.lang = 'de-DE';
    recognition.continuous = false;       // nur eine Äußerung, endet automatisch
    recognition.interimResults = false;   // nur finale Ergebnisse

    let endGuard: any;

    recognition.onstart = () => {
      if (this.recognition !== recognition) return;
      this.listeningField = field;
      this.changeDetector.detectChanges();

      // Fallback: falls onspeechend nicht feuert, nach sechs Sekunden stoppen.
      endGuard = setTimeout(() => {
        try { recognition.stop(); } catch {}
      }, 6000);
    };

    recognition.onresult = (event: any) => {
      if (this.recognition !== recognition) return;
      // Nimm das letzte (finale) Ergebnis
      const res = event.results[event.results.length - 1];
      const text = res[0]?.transcript ?? '';
      if (field === 'name') this.name = text;
      if (field === 'menge') this.quantityValue = Number(text.replace(',', '.').match(/[0-9]+(?:[.,][0-9]+)?/)?.[0] ?? null);
      this.changeDetector.detectChanges();
      // Nach Ergebnis beenden (da continuous=false meist automatisch endet)
      try { recognition.stop(); } catch {}
    };

    recognition.onspeechend = () => {
      // Stille erkannt -> stoppen
      try { recognition.stop(); } catch {}
    };

    recognition.onend = () => {
      if (this.recognition !== recognition) return;
      this.listeningField = null;
      if (endGuard) { clearTimeout(endGuard); endGuard = undefined; }
      this.recognition = undefined;
      this.changeDetector.detectChanges();
    };

    recognition.onerror = (e: any) => {
      if (this.recognition !== recognition) return;
      this.listeningField = null;
      if (endGuard) { clearTimeout(endGuard); endGuard = undefined; }
      const type = e?.error;
      let msg = 'Fehler bei der Spracheingabe.';
      if (type === 'no-speech') msg = 'Keine Sprache erkannt.';
      else if (type === 'audio-capture') msg = 'Kein Mikrofon gefunden.';
      else if (type === 'not-allowed') msg = 'Mikrofon-Zugriff verweigert.';
      else if (type === 'service-not-allowed') msg = 'Der Spracherkennungsdienst ist in diesem Browser deaktiviert.';
      else if (type === 'network') msg = 'Der Spracherkennungsdienst ist nicht erreichbar.';
      this.snackBar.open(msg, 'OK', { duration: 3500, verticalPosition: 'top' });
      this.changeDetector.detectChanges();
    };

    try {
      recognition.start();
    } catch {
      if (this.recognition === recognition) {
        this.recognition = undefined;
        this.listeningField = null;
      }
      this.snackBar.open('Spracherkennung konnte nicht gestartet werden.', 'OK', { duration: 3500, verticalPosition: 'top' });
      this.changeDetector.detectChanges();
    }
  }
}
