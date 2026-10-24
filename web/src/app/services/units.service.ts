import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Unit { id: number; name: string; is_active: boolean; }

@Injectable({ providedIn: 'root' })
export class UnitsService {
  private readonly baseUrl = '/api/units';
  constructor(private http: HttpClient) {}
  list(): Observable<Unit[]> { return this.http.get<Unit[]>(`${this.baseUrl}/`); }
  create(name: string): Observable<Unit> { return this.http.post<Unit>(`${this.baseUrl}/`, { name }); }
  remove(id: number): Observable<void> { return this.http.delete<void>(`${this.baseUrl}/${id}`); }
}
