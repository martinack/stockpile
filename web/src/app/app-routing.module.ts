import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// Deine Komponenten
import { HomeComponent } from './pages/home/home.component';
import { LabelCreateComponent } from './pages/create-label/create-label.component';
import { ScanComponent } from './pages/scan/scan.component';
import { LocationsComponent } from './pages/locations/locations.component';

const routes: Routes = [
  { path: '', component: HomeComponent },        // Startseite
  { path: 'create', component: LabelCreateComponent }, // Neues Label erstellen
  { path: 'scan', component: ScanComponent },    // QR-Code Scanner
  { path: 'locations', component: LocationsComponent }, // Lagerorte
  { path: '**', redirectTo: '' }                 // Fallback → Home
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { useHash: false })],
  exports: [RouterModule]
})
export class AppRoutingModule {}
