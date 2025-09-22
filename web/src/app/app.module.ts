import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module'; // <— hier
import { AppComponent } from './app.component';

import { HomeComponent } from './pages/home/home.component';
import { LabelCreateComponent } from './pages/create-label/create-label.component';
import { ScanComponent } from './pages/scan/scan.component';
import { ZXingScannerModule } from '@zxing/ngx-scanner';

// Add these:
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import {MatNativeDateModule, MatOption} from '@angular/material/core';
import { MatSliderModule } from '@angular/material/slider';
// Add these for list view
import { MatListModule } from '@angular/material/list';
import { MatDividerModule } from '@angular/material/divider';
// Neu: Dialog und FormField
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
// Declare new component
import { LocationsComponent } from './pages/locations/locations.component';
import { LocationsCreateDialogComponent } from './pages/locations/locations-create-dialog.component';
import {MatSelectModule} from '@angular/material/select';
import {ItemCreatedDialogComponent} from './pages/create-label/item-created-dialog.component';

@NgModule({
  declarations: [
    AppComponent,
    HomeComponent,
    LabelCreateComponent,
    ScanComponent,
    LocationsComponent,
    LocationsCreateDialogComponent,
    ItemCreatedDialogComponent,
  ],
  imports: [
    ZXingScannerModule,
    BrowserModule,
    FormsModule,
    HttpClientModule,
    AppRoutingModule,   // <— wichtig
    BrowserAnimationsModule,
    MatToolbarModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatSliderModule,
    MatListModule,
    MatDividerModule,
    MatDialogModule,
    MatFormFieldModule,
    MatSnackBarModule,
    FormsModule,
    MatSelectModule,
    MatDialogModule,
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {}
