import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ItemService {
  private readonly baseUrl = '/api/items';

  constructor(private http: HttpClient) {}

  createItem(name: string, quantityValue: number, unitId: number, warehouseId: number | null, storageDate: string | null): Observable<any> {
    return this.http.post(`${this.baseUrl}/`, { name, quantity_value: quantityValue, unit_id: unitId, warehouse_id: warehouseId, storage_date: storageDate });
  }

  getItem(code: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/${code}`);
  }

  checkoutItem(code: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/${code}/checkout`, {});
  }

  searchItems(params: Record<string, string | number | null>): Observable<any> {
    const query = Object.entries(params).filter(([, value]) => value !== null && value !== '').map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`).join('&');
    return this.http.get(`${this.baseUrl}/search/${query ? `?${query}` : ''}`);
  }

  deleteItem(itemId: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/${itemId}`);
  }
}
