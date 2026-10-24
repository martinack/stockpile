import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { ItemService } from '../../services/api.service';
import { ItemCreatedDialogComponent } from '../create-label/item-created-dialog.component';
import { LocationsService, StorageLocation } from '../../services/locations.service';
import { Unit, UnitsService } from '../../services/units.service';

export interface Item { id: number; name: string; code: string; quantity_value: number; unit_name: string; unit_id: number; warehouse_name: string | null; warehouse_id: number | null; storage_date: string | null; }

@Component({ selector: 'app-items', standalone: false, templateUrl: './items.component.html', styleUrl: './items.component.scss' })
export class ItemsComponent implements OnInit {
  items: Item[] = []; total = 0; loading = false; filtersOpen = false;
  query = ''; warehouseId: number | null = null; unitId: number | null = null;
  storageDateFrom: Date | null = null; storageDateTo: Date | null = null;
  sortBy: 'name' | 'storage_date' = 'storage_date';
  sortDirection: 'asc' | 'desc' = 'asc';
  warehouses: StorageLocation[] = []; units: Unit[] = []; facets: any = {};
  constructor(private api: ItemService, private locations: LocationsService, private unitsService: UnitsService, private dialog: MatDialog, private cdr: ChangeDetectorRef) {}
  ngOnInit(): void { this.locations.list().subscribe(data => this.warehouses = data); this.unitsService.list().subscribe(data => this.units = data); this.search(); }
  search(): void { this.loading = true; this.api.searchItems({ q: this.query, warehouse_id: this.warehouseId, unit_id: this.unitId, storage_date_from: this.dateParam(this.storageDateFrom), storage_date_to: this.dateParam(this.storageDateTo), sort_by: this.sortBy, sort_direction: this.sortDirection }).subscribe({ next: result => { this.items = result.items; this.total = result.total; this.facets = result.facets; this.loading = false; this.cdr.detectChanges(); }, error: () => { this.items = []; this.loading = false; this.cdr.detectChanges(); } }); }
  toggleSort(column: 'name' | 'storage_date'): void {
    this.sortDirection = this.sortBy === column && this.sortDirection === 'asc' ? 'desc' : 'asc';
    this.sortBy = column;
    this.search();
  }
  sortIcon(column: 'name' | 'storage_date'): string { return this.sortBy === column && this.sortDirection === 'desc' ? 'arrow_downward' : 'arrow_upward'; }
  clear(): void { this.query = ''; this.warehouseId = this.unitId = null; this.storageDateFrom = this.storageDateTo = null; this.search(); }
  private dateParam(value: Date | null): string | null {
    if (!value) return null;
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  showLabel(item: Item): void {
    this.dialog.open(ItemCreatedDialogComponent, { width: '420px', autoFocus: false, data: { ...item, title: 'QR-Label' } });
  }
  delete(item: Item, event: Event): void {
    event.stopPropagation();
    if (confirm(`Artikel „${item.name}“ löschen?`)) this.api.deleteItem(item.id).subscribe(() => this.search());
  }
}
