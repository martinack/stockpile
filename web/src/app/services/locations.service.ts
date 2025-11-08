// Datei: web/src/app/pages/locations/locations.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';

export interface StorageLocation {
  id: number;
  name: string;
}

@Injectable({ providedIn: 'root' })
export class LocationsService {
  private readonly baseUrl = 'http://lager.lan:9000/warehouses';

  constructor(private http: HttpClient) {}


  list(): Observable<StorageLocation[]> {
    return this.http.get<StorageLocation[]>(this.baseUrl);
  }

  create(name: string): Observable<StorageLocation> {
    return this.http.post<StorageLocation>(this.baseUrl, { name });
  }

  remove(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }


}
