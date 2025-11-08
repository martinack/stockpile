import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ItemService {
  private baseUrl = 'http://lager.home/api/items'; // via nginx proxy

  constructor(private http: HttpClient) {}

  createItem(name: string, warehouseId: number | null = null, quantity: string | null = null): Observable<any> {
    return this.http.post(this.baseUrl, { name, quantity, warehouse_id: warehouseId });
  }

  getItem(code: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/${code}`);
  }

  checkoutItem(code: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/${code}/checkout`, {});
  }

  listItems(search?: string): Observable<any> {
    let url = this.baseUrl;
    if (search) {
      url += `?search=${encodeURIComponent(search)}`;
    }
    return this.http.get(url);
  }

  deleteItem(itemId: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/${itemId}`);
  }
}
