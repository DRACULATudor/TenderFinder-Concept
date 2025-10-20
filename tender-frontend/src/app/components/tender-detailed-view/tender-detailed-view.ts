import {
  Component,
  Input,
  OnInit,
  AfterViewInit,
  ElementRef,
  ViewEncapsulation,
  OnDestroy,
  OnChanges,
  SimpleChanges,
  inject,
} from '@angular/core';
import type { Tender, TenderDetails } from '../../types/tender';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { TenderService } from '../../services/tender.service';

@Component({
  selector: 'app-tender-detailed-view',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tender-detailed-view.html',
  styleUrl: './tender-detailed-view.css',
  encapsulation: ViewEncapsulation.None,
})
export class TenderDetailedView implements OnInit, AfterViewInit, OnDestroy, OnChanges {
  @Input() tender!: TenderDetails;

  // Data validation flags
  hasValidData = false;
  dataValidationErrors: string[] = [];
  isLoading = false;

  private route = inject(ActivatedRoute);
  public router = inject(Router);
  private tenderService = inject(TenderService);

  constructor(private readonly elementRef: ElementRef) {}

  ngOnInit(): void {
    console.log('=== TenderDetailedView ngOnInit ===');
    console.log('Initial tender data:', this.tender);
    console.log('Route snapshot params:', this.route.snapshot.params);
    console.log('Current URL:', this.router.url);
    
    // If no tender data passed as input, try to get from route
    if (!this.tender) {
      const tenderId = this.route.snapshot.paramMap.get('id');
      console.log('Extracted tender ID from route:', tenderId);
      
      if (tenderId) {
        console.log('Fetching tender data for ID:', tenderId);
        this.isLoading = true;
        
        // Add timeout to prevent infinite loading
        const timeoutId = setTimeout(() => {
          if (this.isLoading) {
            console.error('=== REQUEST TIMEOUT ===');
            this.isLoading = false;
            this.dataValidationErrors = ['Request timed out. Please check if backend is running on port 4002.'];
          }
        }, 10000);
        
        this.tenderService.getTenderById(tenderId).subscribe({
          next: (data) => {
            clearTimeout(timeoutId);
            console.log('=== TENDER DATA RECEIVED ===');
            console.log('Received tender data:', data);
            this.tender = data;
            this.isLoading = false;
            this.validateTenderData();
          },
          error: (error) => {
            clearTimeout(timeoutId);
            console.error('=== TENDER FETCH ERROR ===');
            console.error('Error fetching tender:', error);
            console.error('Error details:', error.error);
            console.error('Error status:', error.status);
            console.error('Error url:', error.url);
            this.isLoading = false;
            
            let errorMsg = 'Unknown error';
            if (error.status === 0) {
              errorMsg = 'Cannot connect to backend. Is the server running on port 4002?';
            } else if (error.status === 404) {
              errorMsg = `Tender not found (ID: ${tenderId})`;
            } else if (error.message) {
              errorMsg = error.message;
            }
            
            this.dataValidationErrors = [`Failed to load tender: ${errorMsg}`];
          }
        });
        return;
      } else {
        console.log('No tender ID found in route');
        this.isLoading = false;
        this.dataValidationErrors = ['No tender ID provided in route'];
      }
    } else {
      // Skip validation during SSR or when tender is undefined
      if (typeof window === 'undefined' || !this.tender) {
        console.log('Skipping validation - SSR mode or no tender data');
        this.hasValidData = false;
        this.dataValidationErrors = ['Tender data not available'];
        return;
      }
      
      this.validateTenderData();
    }
  }

  // Test method to check backend connectivity
  testBackend(): void {
    console.log('=== TESTING BACKEND CONNECTIVITY ===');
    fetch('http://localhost:4002/tenders/welcome')
      .then(response => {
        console.log('Backend test response status:', response.status);
        return response.json();
      })
      .then(data => {
        console.log('Backend is accessible:', data);
      })
      .catch(error => {
        console.error('Backend is not accessible:', error);
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['tender'] && changes['tender'].currentValue) {
      console.log('TenderDetailedView ngOnChanges - new tender data:', this.tender);
      
      // Only validate if we're in browser mode and have data
      if (typeof window !== 'undefined' && this.tender) {
        this.validateTenderData();
      }
    }
  }

  ngAfterViewInit(): void {
    // Only run scroll animations in browser environment
    if (typeof window !== 'undefined' && this.elementRef?.nativeElement) {
      this.initScrollAnimations();
    }
  }

  ngOnDestroy(): void {
    console.log('TenderDetailedView component is being destroyed');
    
    // Only cleanup DOM elements in browser environment
    if (typeof window !== 'undefined' && this.elementRef?.nativeElement) {
      this.cleanupScrollAnimations();
    }
  }

  private validateTenderData(): void {
    console.log('TenderDetailedView validateTenderData - tender data:', this.tender);
    if (!this.tender) {
      this.hasValidData = false;
      this.dataValidationErrors = ['Tender data is null or undefined'];
      return;
    }

    const errors: string[] = [];

    // Check for required fields
    if (!this.tender.id && !this.tender['uniq_id']) {
      errors.push('Missing tender ID');
    }

    if (!this.tender.title) {
      errors.push('Missing tender title');
    }

    // Check for content availability
    const hasContent =
      this.tender.procurement ||
      this.tender.cpv_and_labels ||
      this.tender['award_criteria'] ||
      this.tender['terms_and_conditions'] ||
      this.tender['project_publication_date'];

    if (!hasContent) {
      errors.push('No detailed content available');
    }

    this.dataValidationErrors = errors;
    this.hasValidData = errors.length === 0;

    console.log('Data validation errors:', errors);
    console.log('Data validation result:', this.hasValidData);
  }

  private initScrollAnimations(): void {
    try {
      // Check if elementRef and nativeElement exist
      if (!this.elementRef?.nativeElement) {
        console.log('ElementRef not available for scroll animations');
        return;
      }

      const elements = this.elementRef.nativeElement.querySelectorAll('[data-animate]');
      if (elements && elements.forEach) {
        elements.forEach((element: Element) => {
          // Add animation logic here if needed
          element.classList.add('animate-in');
        });
      }
    } catch (error) {
      console.warn('Error initializing scroll animations:', error);
    }
  }

  private cleanupScrollAnimations(): void {
    try {
      // Check if elementRef and nativeElement exist
      if (!this.elementRef?.nativeElement) {
        return;
      }

      const elements = this.elementRef.nativeElement.querySelectorAll('[data-animate]');
      if (elements && elements.forEach) {
        elements.forEach((element: Element) => {
          // Remove animation classes if needed
          element.classList.remove('animate-in');
        });
      }
    } catch (error) {
      console.warn('Error cleaning up scroll animations:', error);
    }
  }

  // Helper method to safely access nested properties
  safeGet(obj: any, path: string, defaultValue: any = null): any {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : defaultValue;
    }, obj);
  }

  /**
   * Extract text from multilingual objects
   * Handles both old format (DE, EN, FR, IT) and new format (de, en, fr, it)
   */
  getMultilingualText(textObj: any): string {
    if (!textObj) return '';
    
    if (typeof textObj === 'string') {
      return textObj;
    }

    if (typeof textObj === 'object') {
      // Try uppercase language codes first
      const languages = ['EN', 'DE', 'FR', 'IT', 'en', 'de', 'fr', 'it'];
      
      for (const lang of languages) {
        if (textObj[lang] && textObj[lang].trim()) {
          return textObj[lang];
        }
      }
    }
    
    return '';
  }

  /**
   * Format date strings for display
   */
  formatDate(dateString: string): string {
    if (!dateString) return '';
    
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  }

  /**
   * Check if a value exists and is not empty
   */
  hasValue(value: any): boolean {
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return value.trim().length > 0;
    if (typeof value === 'object') return Object.keys(value).length > 0;
    if (Array.isArray(value)) return value.length > 0;
    return true;
  }
}