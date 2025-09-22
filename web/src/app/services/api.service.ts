import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ItemService {
  private baseUrl = 'http://localhost:8000/items'; // via nginx proxy

  constructor(private http: HttpClient) {}

  createItem(name: string, warehouseId: number | null = null): Observable<any> {
    return this.http.post(this.baseUrl, { name, warehouse_id: warehouseId });
  }

  getItem(code: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/${code}`);
  }

  checkoutItem(code: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/${code}/checkout`, {});
  }
}
