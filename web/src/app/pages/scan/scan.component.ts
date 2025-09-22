import { Component } from '@angular/core';
import { ItemService } from '../../services/api.service';
import { BarcodeFormat } from '@zxing/library';
import {MatSnackBar} from '@angular/material/snack-bar';

@Component({
  selector: 'app-scan',
  standalone: false,
  templateUrl: './scan.component.html',
  styleUrls: ['./scan.component.scss']
})
export class ScanComponent {
  item: any = null;

  // Scanner state
  hasDevices = false;
  hasPermission = false;
  currentDevice?: MediaDeviceInfo;
  torch = false;
  torchAvailable = false;

  // Scan tuning
  allowedFormats = [BarcodeFormat.QR_CODE];
  timeBetweenScans = 300; // ms
  tryHarder = true;

  constructor(private api: ItemService,
              private snackbar: MatSnackBar,
              ) {}

  onScan(result: string) {
    if (!result) return;
    this.api.getItem(result).subscribe({
      next: (data) => this.item = data,
      error: () => this.item = null
    });
  }

  checkout() {
    if (!this.item) return;
    this.api.checkoutItem(this.item.code).subscribe({
      next: () => {
        this.snackbar.open('Eintrag ausgebucht!', 'OK', { duration: 3000, verticalPosition: "top" });
        this.item = null;
      }
    });
  }

  // Scanner events
  onCamerasFound(devices: MediaDeviceInfo[]) {
    this.hasDevices = devices && devices.length > 0;
    // pick environment/back camera if possible
    const env = devices.find(d => /back|rear|environment/i.test(d.label || ''));
    this.currentDevice = env || devices[0];
  }

  onPermission(state: boolean) {
    this.hasPermission = state;
  }

  onTorchCompatible(isCompatible: boolean) {
    this.torchAvailable = isCompatible;
  }

  toggleTorch() {
    if (!this.torchAvailable) return;
    this.torch = !this.torch;
  }
}
