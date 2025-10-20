import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { TenderService } from '../../services/tender.service';
import { SearchResult, SearchParams, TenderDetails } from '../../types/tender';
import { TenderDetailedView } from '../tender-detailed-view/tender-detailed-view';

@Component({
  selector: 'app-tender-search',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, TenderDetailedView],
  template: `
    <div class="search-container">
      <header class="search-header">
        <div class="hero-section">
          <h1 class="main-title">TenderFinder Search</h1>
          <p class="subtitle">Find the perfect tender opportunities with AI-powered search</p>
        </div>
      </header>
      
      <main class="search-main">
        <!-- Search Form -->
        <section class="search-form-section">
          <div class="search-form">
            <div class="search-input-group">
              <input 
                type="text" 
                class="search-input"
                [(ngModel)]="searchQuery"
                (keyup.enter)="performSearch()"
                placeholder="Search for tenders... (e.g., 'office furniture', 'IT services', 'construction')"
                [disabled]="isLoading()"
              />
              <button 
                class="search-button"
                (click)="performSearch()"
                [disabled]="isLoading() || !searchQuery.trim()"
              >
                {{ isLoading() ? 'Searching...' : 'Search' }}
              </button>
            </div>
            
            <div class="search-filters">
              <div class="filter-group">
                <label for="searchType">Search Type:</label>
                <select id="searchType" [(ngModel)]="searchType" class="filter-select">
                  <option value="hybrid">Hybrid (AI + Traditional)</option>
                  <option value="semantic">AI Semantic Search</option>
                  <option value="traditional">Traditional Search</option>
                </select>
              </div>
              
              <div class="filter-group">
                <label for="resultLimit">Results:</label>
                <select id="resultLimit" [(ngModel)]="resultLimit" class="filter-select">
                  <option value="10">10 results</option>
                  <option value="25">25 results</option>
                  <option value="50">50 results</option>
                  <option value="100">100 results</option>
                </select>
              </div>
            </div>
          </div>
        </section>

        <!-- Search Results -->
        <section class="search-results-section" *ngIf="hasSearched()">
          <div class="results-header">
            <h2>Search Results</h2>
            <span class="results-count" *ngIf="searchResults().length > 0">
              Found {{ searchResults().length }} tender{{ searchResults().length !== 1 ? 's' : '' }}
              {{ searchQuery ? 'for "' + searchQuery + '"' : '' }}
            </span>
            <span class="no-results" *ngIf="searchResults().length === 0 && !isLoading()">
              No tenders found{{ searchQuery ? ' for "' + searchQuery + '"' : '' }}
            </span>
          </div>

          <!-- Loading State -->
          <div class="loading-state" *ngIf="isLoading()">
            <div class="spinner"></div>
            <p>Searching tenders...</p>
          </div>

          <!-- Results List -->
          <div class="results-list" *ngIf="!isLoading()">
            <div 
              class="result-card" 
              *ngFor="let result of searchResults(); trackBy: trackByResultId"
              (click)="viewTenderDetails(result)"
            >
              <div class="result-header">
                <h3 class="result-title">{{ result.title }}</h3>
                <div class="result-badges">
                  <span class="search-type-badge" [class]="'badge-' + result.search_type">
                    {{ result.search_type }}
                  </span>
                  <span class="score-badge">
                    Score: {{ formatScore(result.score) }}
                  </span>
                </div>
              </div>
              
              <div class="result-details">
                <p class="result-category" *ngIf="result.category">
                  <strong>Category:</strong> {{ result.category }}
                </p>
                <p class="result-cpv" *ngIf="result.main_label">
                  <strong>CPV:</strong> {{ result.main_cpv_code }} - {{ result.main_label }}
                </p>
                
                <!-- Score breakdown for hybrid results -->
                <div class="score-breakdown" *ngIf="result.search_type === 'hybrid' && (result.trad_score || result.semantic_score)">
                  <span class="score-item" *ngIf="result.trad_score">
                    Traditional: {{ formatScore(result.trad_score) }}
                  </span>
                  <span class="score-item" *ngIf="result.semantic_score">
                    Semantic: {{ formatScore(result.semantic_score) }}
                  </span>
                </div>
              </div>
              
              <div class="result-actions">
                <button class="view-details-btn">View Details</button>
              </div>
            </div>
          </div>
        </section>

        <!-- Initial State / Tips -->
        <section class="search-tips" *ngIf="!hasSearched() && !isLoading()">
          <h2>Search Tips</h2>
          <div class="tips-grid">
            <div class="tip-card">
              <h3>🔍 Traditional Search</h3>
              <p>Use exact keywords and terms that appear in tender documents. Best for specific product names or technical terms.</p>
            </div>
            <div class="tip-card">
              <h3>🤖 AI Semantic Search</h3>
              <p>Understands context and meaning. Try phrases like "office furniture" or "IT consulting services" in multiple languages.</p>
            </div>
            <div class="tip-card">
              <h3>⚡ Hybrid Search</h3>
              <p>Combines both approaches for the best results. Recommended for most searches to get comprehensive matches.</p>
            </div>
          </div>
        </section>

        <!-- Tender Detail Popup -->
        <div class="tender-detail-overlay" *ngIf="showDetail()" (click)="closeDetail()">
          <div class="tender-detail-modal" (click)="$event.stopPropagation()">
            <div class="modal-header">
              <h2>Tender Details</h2>
              <button class="close-button" (click)="closeDetail()">×</button>
            </div>
            
            <div class="modal-content">
              <div *ngIf="detailLoading()" class="loading-container">
                <div class="spinner"></div>
                <p>Loading tender details...</p>
              </div>
              
              <div *ngIf="detailError()" class="error-container">
                <p>{{ detailError() }}</p>
                <button (click)="retryDetailLoad()" class="retry-button">Retry</button>
              </div>
              
              <app-tender-detailed-view 
                *ngIf="detailedTender && !detailLoading()" 
                [tender]="detailedTender">
              </app-tender-detailed-view>
            </div>
          </div>
        </div>
      </main>
    </div>
  `,
  styles: [`
    .search-container {
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 2rem;
    }

    .search-header {
      text-align: center;
      margin-bottom: 2rem;
    }

    .hero-section {
      background: rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(10px);
      border-radius: 20px;
      padding: 2rem;
      border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .main-title {
      font-size: 3rem;
      font-weight: bold;
      color: white;
      margin-bottom: 0.5rem;
      text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }

    .subtitle {
      font-size: 1.2rem;
      color: rgba(255, 255, 255, 0.9);
      margin: 0;
    }

    .search-main {
      max-width: 1200px;
      margin: 0 auto;
    }

    .search-form-section {
      margin-bottom: 2rem;
    }

    .search-form {
      background: white;
      border-radius: 15px;
      padding: 2rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }

    .search-input-group {
      display: flex;
      gap: 1rem;
      margin-bottom: 1.5rem;
      align-items: center;
    }

    .search-input {
      flex: 1;
      padding: 1rem;
      border: 2px solid #e0e0e0;
      border-radius: 10px;
      font-size: 1rem;
      transition: border-color 0.3s ease;
    }

    .search-input:focus {
      outline: none;
      border-color: #667eea;
    }

    .search-input:disabled {
      background: #f5f5f5;
      cursor: not-allowed;
    }

    .search-button {
      padding: 1rem 2rem;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      border-radius: 10px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s ease;
      min-width: 120px;
    }

    .search-button:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }

    .search-button:disabled {
      background: #ccc;
      cursor: not-allowed;
      transform: none;
    }

    .search-filters {
      display: flex;
      gap: 2rem;
      flex-wrap: wrap;
    }

    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .filter-group label {
      font-weight: 600;
      color: #333;
      font-size: 0.9rem;
    }

    .filter-select {
      padding: 0.5rem;
      border: 1px solid #ddd;
      border-radius: 5px;
      font-size: 0.9rem;
    }

    .search-results-section {
      background: white;
      border-radius: 15px;
      padding: 2rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }

    .results-header {
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 2px solid #f0f0f0;
    }

    .results-header h2 {
      margin: 0 0 0.5rem 0;
      color: #333;
    }

    .results-count {
      color: #666;
      font-size: 0.9rem;
    }

    .no-results {
      color: #999;
      font-style: italic;
    }

    .loading-state {
      text-align: center;
      padding: 3rem;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 4px solid #f3f3f3;
      border-top: 4px solid #667eea;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 1rem;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .results-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .result-card {
      border: 1px solid #e0e0e0;
      border-radius: 10px;
      padding: 1.5rem;
      transition: all 0.3s ease;
      cursor: pointer;
      background: #fafafa;
    }

    .result-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
      border-color: #667eea;
    }

    .result-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .result-title {
      flex: 1;
      margin: 0;
      color: #333;
      font-size: 1.2rem;
      line-height: 1.4;
    }

    .result-badges {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .search-type-badge, .score-badge {
      padding: 0.25rem 0.75rem;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .badge-traditional {
      background: #e3f2fd;
      color: #1976d2;
    }

    .badge-semantic {
      background: #f3e5f5;
      color: #7b1fa2;
    }

    .badge-hybrid {
      background: #e8f5e8;
      color: #388e3c;
    }

    .score-badge {
      background: #fff3e0;
      color: #f57c00;
    }

    .result-details {
      margin-bottom: 1rem;
    }

    .result-details p {
      margin: 0.5rem 0;
      color: #666;
      font-size: 0.9rem;
    }

    .score-breakdown {
      display: flex;
      gap: 1rem;
      margin-top: 0.5rem;
    }

    .score-item {
      font-size: 0.8rem;
      color: #888;
      background: #f5f5f5;
      padding: 0.25rem 0.5rem;
      border-radius: 5px;
    }

    .result-actions {
      display: flex;
      justify-content: flex-end;
    }

    .view-details-btn {
      padding: 0.5rem 1rem;
      background: #667eea;
      color: white;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      font-size: 0.9rem;
      transition: background 0.3s ease;
    }

    .view-details-btn:hover {
      background: #5a67d8;
    }

    .search-tips {
      background: white;
      border-radius: 15px;
      padding: 2rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }

    .search-tips h2 {
      text-align: center;
      color: #333;
      margin-bottom: 2rem;
    }

    .tips-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.5rem;
    }

    .tip-card {
      background: #f8f9fa;
      padding: 1.5rem;
      border-radius: 10px;
      border-left: 4px solid #667eea;
    }

    .tip-card h3 {
      margin: 0 0 1rem 0;
      color: #333;
    }

    .tip-card p {
      margin: 0;
      color: #666;
      line-height: 1.5;
    }

    @media (max-width: 768px) {
      .search-container {
        padding: 1rem;
      }

      .main-title {
        font-size: 2rem;
      }

      .search-input-group {
        flex-direction: column;
        align-items: stretch;
      }

      .search-filters {
        flex-direction: column;
        gap: 1rem;
      }

      .result-header {
        flex-direction: column;
        align-items: flex-start;
      }

      .tips-grid {
        grid-template-columns: 1fr;
      }
    }

    /* Modal Styles */
    .tender-detail-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
      padding: 1rem;
    }

    .tender-detail-modal {
      background: white;
      border-radius: 15px;
      max-width: 1000px;
      max-height: 90vh;
      width: 100%;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem 2rem;
      border-bottom: 1px solid #eee;
      background: #f8f9fa;
    }

    .modal-header h2 {
      margin: 0;
      color: #333;
      font-size: 1.5rem;
    }

    .close-button {
      background: none;
      border: none;
      font-size: 2rem;
      color: #666;
      cursor: pointer;
      padding: 0;
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      transition: all 0.2s;
    }

    .close-button:hover {
      background: #e9ecef;
      color: #333;
    }

    .modal-content {
      padding: 2rem;
      max-height: calc(90vh - 100px);
      overflow-y: auto;
    }

    .loading-container {
      text-align: center;
      padding: 3rem;
    }

    .error-container {
      text-align: center;
      padding: 3rem;
      color: #dc3545;
    }

    .retry-button {
      background: #007bff;
      color: white;
      border: none;
      padding: 0.5rem 1rem;
      border-radius: 5px;
      cursor: pointer;
      margin-top: 1rem;
    }

    .retry-button:hover {
      background: #0056b3;
    }
  `]
})
export class TenderSearchComponent implements OnInit {
  private tenderService = inject(TenderService);
  private router = inject(Router);

  // Search form state
  searchQuery = '';
  searchType: 'traditional' | 'semantic' | 'hybrid' = 'hybrid';
  resultLimit = 25;

  // Component state signals
  isLoading = signal(false);
  hasSearched = signal(false);
  searchResults = signal<SearchResult[]>([]);

  // Popup state (same as tender-list)
  selectedResult: SearchResult | null = null;
  detailedTender: TenderDetails | null = null;
  showDetail = signal(false);
  detailLoading = signal(false);
  detailError = signal<string | null>(null);

  ngOnInit() {
    // You could initialize with URL parameters here if needed
  }

  performSearch() {
    const query = this.searchQuery.trim();
    if (!query) {
      return;
    }

    this.isLoading.set(true);
    this.hasSearched.set(true);

    const searchParams: SearchParams = {
      query: query,
      limit: this.resultLimit,
      search_type: this.searchType
    };

    console.log('=== SEARCH DEBUG ===');
    console.log('Performing search with params:', searchParams);
    console.log('Backend URL will be:', 'http://localhost:4002/search?query=' + encodeURIComponent(query));

    this.tenderService.performSearch(searchParams).subscribe({
      next: (results) => {
        console.log('=== SEARCH SUCCESS ===');
        console.log('Search results received:', results);
        console.log('Results count:', results?.length || 0);
        this.searchResults.set(results);
        this.isLoading.set(false);
      },
      error: (error) => {
        console.error('=== SEARCH ERROR ===');
        console.error('Search failed:', error);
        console.error('Error details:', {
          message: error.message,
          status: error.status,
          statusText: error.statusText,
          url: error.url
        });
        this.searchResults.set([]);
        this.isLoading.set(false);
        alert('Search failed: ' + (error.message || 'Unknown error. Check console for details.'));
      }
    });
  }

  formatScore(score: number): string {
    if (score === null || score === undefined) {
      return 'N/A';
    }
    return score.toFixed(2);
  }

  trackByResultId(index: number, result: SearchResult): string {
    return result.id;
  }

  viewTenderDetails(result: SearchResult) {
    console.log('=== DEBUG: viewTenderDetails called ===');
    console.log('Search result object:', result);
    console.log('Result ID:', result.id);
    console.log('Result pub_id:', result.pub_id);
    
    // Let's see ALL properties of the result
    console.log('ALL result properties:', Object.keys(result));
    for (const key in result) {
      console.log(`  ${key}:`, result[key as keyof SearchResult]);
    }

    this.selectedResult = result;
    this.detailedTender = null;
    this.showDetail.set(true);
    this.detailLoading.set(true);
    this.detailError.set(null);

    // Single API call with proper error handling and retry logic - same as welcome page
    if (result.pub_id) {
      console.log('Using getTenderDetails with pub_id:', result.pub_id);
      this.loadTenderDetailsWithRetry(result.id, result.pub_id, true);
    } else {
      console.log('Using getTenderById as fallback with id:', result.id);
      this.loadTenderDetailsWithRetry(result.id, null, false);
    }
  }

  private loadTenderDetailsWithRetry(
    tenderId: string, 
    publicationId: string | null, 
    usePublicationId: boolean,
    retryCount: number = 0
  ): void {
    console.log('=== DEBUG: loadTenderDetailsWithRetry called ===');
    console.log('tenderId:', tenderId);
    const maxRetries = 2;
    
    // Same logic as welcome page - try getTenderDetails if publication_id available
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

  closeDetail(): void {
    this.showDetail.set(false);
    this.selectedResult = null;
    this.detailedTender = null;
    this.detailError.set(null);
  }

  retryDetailLoad(): void {
    if (this.selectedResult) {
      const detailId = this.selectedResult.pub_id || this.selectedResult.id;
      this.detailLoading.set(true);
      this.detailError.set(null);
      this.loadTenderDetailsWithRetry(detailId, null, false);
    }
  }
}