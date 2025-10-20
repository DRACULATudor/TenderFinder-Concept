import { Injectable, inject } from '@angular/core';
import {
  HttpClient,
  HttpHeaders,
  HttpErrorResponse,
} from '@angular/common/http';
import { Observable, throwError, catchError, map } from 'rxjs';
import { Tender, TenderDetails, SearchResult, SearchParams } from '../types/tender';

@Injectable({
  providedIn: 'root',
})
export class TenderService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://localhost:4002'; // FastAPI backend URL

  private readonly httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
      Accept: 'application/json',
    }),
  };

  getAllTenders(): Observable<Tender[]> {
    return this.http
      .get<any>(`${this.apiUrl}/tenders/welcome`, this.httpOptions)
      .pipe(
        map((response) => {
          // Handle different response structures from your FastAPI backend
          if (Array.isArray(response)) {
            return response;
          } else if (response.data && Array.isArray(response.data)) {
            return response.data;
          } else if (response.tenders && Array.isArray(response.tenders)) {
            return response.tenders;
          }
          return [];
        }),
        catchError(this.handleError)
      );
  }

  getTenderById(id: string): Observable<TenderDetails> {
    console.log(
      `Making request to: ${this.apiUrl}/tenders/detailed_view/${id}`
    );
    return this.http
      .get<TenderDetails>(
        `${this.apiUrl}/tenders/detailed_view/${id}`,
        this.httpOptions
      )
      .pipe(
        map((response) => {
          console.log(`Response from /tenders/detailed_view/${id}:`, response);
          
          // Validate response data
          if (!response) {
            throw new Error('Empty response received from server');
          }
          
          if (!response.id && !response['uniq_id']) {
            throw new Error('Response missing tender ID');
          }
          
          return response;
        }),
        catchError((error) => {
          console.error(`Error in getTenderById(${id}):`, error);
          return this.handleError(error);
        })
      );
  }

  getTendersByType(type: string): Observable<Tender[]> {
    return this.http
      .get<Tender[]>(`${this.apiUrl}/tenders/type/${type}`, this.httpOptions)
      .pipe(catchError(this.handleError));
  }

  getTendersByCategory(category: string): Observable<Tender[]> {
    return this.http
      .get<Tender[]>(
        `${this.apiUrl}/tenders/category/${category}`,
        this.httpOptions
      )
      .pipe(catchError(this.handleError));
  }

  // Search tenders with query parameters (legacy method)
  searchTenders(searchParams: any): Observable<Tender[]> {
    const params = new URLSearchParams();
    Object.keys(searchParams).forEach((key) => {
      if (searchParams[key]) {
        params.append(key, searchParams[key]);
      }
    });

    return this.http
      .get<Tender[]>(
        `${this.apiUrl}/search?${params.toString()}`,
        this.httpOptions
      )
      .pipe(catchError(this.handleError));
  }

  // New semantic/hybrid search method
  performSearch(searchParams: SearchParams): Observable<SearchResult[]> {
    const params = new URLSearchParams();
    
    // Add query parameter (required)
    params.append('query', searchParams.query);
    
    // Add optional parameters with defaults
    if (searchParams.limit) {
      params.append('limit', searchParams.limit.toString());
    }
    
    if (searchParams.search_type) {
      params.append('search_type', searchParams.search_type);
    }

    console.log(`Searching with params: ${params.toString()}`);
    
    return this.http
      .get<SearchResult[]>(
        `${this.apiUrl}/search?${params.toString()}`,
        this.httpOptions
      )
      .pipe(
        map((response: any) => {
          console.log('Search response received:', response);
          console.log('Response type:', typeof response);
          console.log('Is array:', Array.isArray(response));
          
          // Handle different response structures
          if (Array.isArray(response)) {
            console.log('Returning array directly, length:', response.length);
            return response as SearchResult[];
          } else if (response && response['Results based on your search'] && Array.isArray(response['Results based on your search'])) {
            console.log('Found results in "Results based on your search" key');
            return response['Results based on your search'] as SearchResult[];
          } else if (response.results && Array.isArray(response.results)) {
            console.log('Found results in "results" key');
            return response.results as SearchResult[];
          } else if (response.data && Array.isArray(response.data)) {
            console.log('Found results in "data" key');
            return response.data as SearchResult[];
          } else if (response && typeof response === 'object' && !Array.isArray(response)) {
            console.log('Response is object, checking for error messages');
            if (response.error) {
              console.error('Backend returned error:', response.error);
            }
            return [];
          }
          
          console.warn('Unexpected response structure:', response);
          return [];
        }),
        catchError((error) => {
          console.error('Search error:', error);
          return this.handleError(error);
        })
      );
  }

  // Get detailed tender information
    // Fix Line 155-167 in tender.service.ts
  getTenderDetails(tenderId: string, publicationId?: string): Observable<TenderDetails> {
    console.log(`Making request to: ${this.apiUrl}/tenders/detailed_view/${tenderId}`);
    return this.http
      .get<TenderDetails>(
        `${this.apiUrl}/tenders/detailed_view/${tenderId}`,  // ✅ FIXED URL
        this.httpOptions
      )
      .pipe(
        map((response) => {
          console.log(`Response from /tenders/detailed_view/${tenderId}:`, response);
          
          if (!response) {
            throw new Error('Empty response received from server');
          }
          
          return response;
        }),
        catchError((error) => {
          console.error(`Error in getTenderDetails(${tenderId}):`, error);
          return this.handleError(error);
        })
      );
  }
  // Get statistics about tenders
  getStats(): Observable<any> {
    return this.http
      .get<any>(`${this.apiUrl}/stats`, this.httpOptions)
      .pipe(catchError(this.handleError));
  }

  // Get data status
  getDataStatus(): Observable<any> {
    return this.http
      .get<any>(`${this.apiUrl}/data-status`, this.httpOptions)
      .pipe(catchError(this.handleError));
  }

  // Refresh data from SIMAP
  refreshData(): Observable<any> {
    return this.http
      .post<any>(`${this.apiUrl}/refresh-data`, {}, this.httpOptions)
      .pipe(catchError(this.handleError));
  }

  private handleError(error: HttpErrorResponse) {
    let errorMessage = 'An unknown error occurred!';

    // Check if this is a client-side error (SSR-safe)
    if (error.error && typeof error.error === 'object' && 'message' in error.error && error.status === 0) {
      // Client-side/network error
      errorMessage = `Network Error: ${error.error.message || 'Unable to connect to server'}`;
    } else {
      // Server-side error
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;

      if (error.status === 0) {
        errorMessage =
          'Unable to connect to the server. Please check if the FastAPI backend is running.';
      } else if (error.status === 404) {
        errorMessage = 'Tender data not found.';
      } else if (error.status === 500) {
        errorMessage = 'Internal server error. Please try again later.';
      }
    }

    console.error('TenderService Error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
