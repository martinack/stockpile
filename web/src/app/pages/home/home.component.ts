// src/app/pages/home/home.component.ts
import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  standalone: false,
  styleUrls: ['./home.component.scss']
})
export class HomeComponent {
  constructor(private router: Router) {}

  /** Navigation per Methode (optional, falls du (click) statt routerLink verwenden willst) */
  goCreate(): void {
    this.router.navigate(['/create']);
  }

  goScan(): void {
    this.router.navigate(['/scan']);
  }
}
