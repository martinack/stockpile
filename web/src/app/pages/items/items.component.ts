import { Component, OnInit, Inject } from '@angular/core';
import { MatDialog, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { ItemService } from '../../services/api.service';

export interface Item {
  id: number;
  name: string;
  quantity: string;
  created_at: string;
  is_active: boolean;
  warehouse_id: number | null;
}

@Component({
  selector: 'app-items',
  templateUrl: './items.component.html',
  standalone: false,
  styleUrls: ['./items.component.scss']
})
export class ItemsComponent implements OnInit {
  items: Item[] = [];
  filteredItems: Item[] = [];
  searchTerm: string = '';
  sortBy: 'name' | 'date' = 'name';
  sortDirection: 'asc' | 'desc' = 'asc';

  displayedColumns: string[] = ['name', 'quantity', 'date', 'actions'];

  constructor(
    private dialog: MatDialog,
    private itemService: ItemService
  ) {}

  ngOnInit(): void {
    this.loadItems();
  }

  loadItems(): void {
    this.itemService.listItems().subscribe({
      next: (data) => {
        this.items = data;
        this.applyFilters();
      },
      error: (error) => {
        console.error('Error loading items:', error);
        this.items = [];
        this.applyFilters();
      }
    });
  }

  applyFilters(): void {
    let filtered = [...this.items];

    // Search filter
    if (this.searchTerm) {
      filtered = filtered.filter(item =>
        item.name.toLowerCase().includes(this.searchTerm.toLowerCase())
      );
    }

    // Sort
    filtered.sort((a, b) => {
      let comparison = 0;
      if (this.sortBy === 'name') {
        comparison = a.name.localeCompare(b.name);
      } else if (this.sortBy === 'date') {
        comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      return this.sortDirection === 'asc' ? comparison : -comparison;
    });

    this.filteredItems = filtered;
  }

  onSearchChange(): void {
    this.applyFilters();
  }

  toggleSort(column: 'name' | 'date'): void {
    if (this.sortBy === column) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortBy = column;
      this.sortDirection = 'asc';
    }
    this.applyFilters();
  }

  deleteItem(item: Item): void {
    const dialogRef = this.dialog.open(DeleteConfirmDialogComponent, {
      width: '350px',
      data: { itemName: item.name }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result === true) {
        this.itemService.deleteItem(item.id).subscribe({
          next: () => {
            this.items = this.items.filter(i => i.id !== item.id);
            this.applyFilters();
          },
          error: (error) => {
            console.error('Error deleting item:', error);
          }
        });
      }
    });
  }

  displayItem(item: Item): void {
    // TODO: Implement display functionality
    console.log('Display item:', item);
  }
}

@Component({
  selector: 'app-delete-confirm-dialog',
  template: `
    <h2 mat-dialog-title>Löschen bestätigen</h2>
    <mat-dialog-content>
      <p>Möchten Sie "{{ data.itemName }}" wirklich löschen?</p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button [mat-dialog-close]="false">Abbrechen</button>
      <button mat-raised-button color="warn" [mat-dialog-close]="true">OK</button>
    </mat-dialog-actions>
  `,
  standalone: false
})
export class DeleteConfirmDialogComponent {
  constructor(@Inject(MAT_DIALOG_DATA) public data: { itemName: string }) {}
}
