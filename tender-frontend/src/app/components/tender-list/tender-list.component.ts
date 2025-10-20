import { Component, OnInit, signal, inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, JsonPipe, isPlatformBrowser } from '@angular/common';
import { TenderService } from '../../services/tender.service';
import { Tender, TenderDetails } from '../../types/tender';
import { TenderDetailedView } from '../tender-detailed-view/tender-detailed-view';

@Component({
  selector: 'app-tender-list',
  standalone: true,
  imports: [CommonModule, TenderDetailedView],
  templateUrl: './tender-list.component.html',
  styleUrl: './tender-list.component.css',
})
export class TenderListComponent implements OnInit {
  tenders = signal<Tender[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);

  selectedTender: Tender | null = null;
  detailedTender: TenderDetails | null = null;
  showDetail = signal(false);
  detailLoading = signal(false);
  detailError = signal<string | null>(null);

  private platformId = inject(PLATFORM_ID);

  constructor(private readonly tenderService: TenderService) {}

  ngOnInit(): void {
    // Only load data on the client side, not during SSR
    if (isPlatformBrowser(this.platformId)) {
      this.loadTenders();
    }
  }

  loadTenders(): void {
    this.loading.set(true);
    this.error.set(null);

    this.tenderService.getAllTenders().subscribe({
      next: (data) => {
        console.log('Received tender data:', data);
        this.tenders.set(data || []);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading tenders:', error);
        this.error.set(
          error.message ||
            'Failed to load tenders. Please check if your FastAPI backend is running on http://localhost:8000'
        );
        this.loading.set(false);
        this.tenders.set([]);
      },
    });
  }

  getTenderTypes(): string[] {
    const types = this.tenders()
      .map((tender) => tender.type)
      .filter((type) => type);
    return [...new Set(types)];
  }

  getTendersByType(type: string): Tender[] {
    return this.tenders().filter((tender) => tender.type === type);
  }

  onViewDetails(tender: Tender): void {
    console.log('=== DEBUG: onViewDetails called ===');
    console.log('Tender object:', tender);
    console.log('Tender ID:', tender.id);

    this.selectedTender = tender;
    this.detailedTender = null;
    this.showDetail.set(true);
    this.detailLoading.set(true);
    this.detailError.set(null);

    // Single API call with proper error handling and retry logic
    if (tender.publication_id) {
      console.log('Using getTenderDetails with publication_id:', tender.publication_id);
      this.loadTenderDetailsWithRetry(tender.id, tender.publication_id, true);
    } else {
      console.log('Using getTenderById as fallback');
      this.loadTenderDetailsWithRetry(tender.id, null, false);
    }
  }

  private loadTenderDetailsWithRetry(
    tenderId: string, 
    publicationId: string | null, 
    usePublicationId: boolean,
    retryCount: number = 0
  ): void {
    console.log('=== DEBUG: loadTenderDetailsWithRetry called ===, publicationID', publicationId);
    const maxRetries = 2;
    
    const apiCall = usePublicationId 
      ? this.tenderService.getTenderDetails(tenderId, publicationId!)
      : this.tenderService.getTenderById(tenderId);

    apiCall.subscribe({
      next: (data) => {
        console.log('SUCCESS: Received detailed data:', data);
        this.detailedTender = data;
        this.detailLoading.set(false);
      },
      error: (err) => {
        console.error('ERROR: Failed to get tender details:', err);
        
        // Retry logic for network errors
        if (retryCount < maxRetries && (err.status === 0 || err.status >= 500)) {
          console.log(`Retrying... Attempt ${retryCount + 1}/${maxRetries}`);
          setTimeout(() => {
            this.loadTenderDetailsWithRetry(tenderId, publicationId, usePublicationId, retryCount + 1);
          }, 1000 * (retryCount + 1)); // Exponential backoff
        } else {
          this.detailError.set(err.message || 'Failed to load details.');
          this.detailLoading.set(false);
        }
      },
    });
  }

  // Helper method for debug information
  getDataKeys(obj: any): string {
    if (!obj || typeof obj !== 'object') {
      return 'None';
    }
    try {
      return Object.keys(obj).join(', ');
    } catch (error) {
      return 'Error getting keys';
    }
  }

  closeDetail(): void {
    this.showDetail.set(false);
    this.selectedTender = null;
    this.detailedTender = null;
    this.detailError.set(null);
  }

  retryLoad(): void {
    this.loadTenders();
  }
}
