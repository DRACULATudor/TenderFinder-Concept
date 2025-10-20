export interface Tender {
  // Basic tender fields
  id: string;
  publication_id?: string;
  search_index?: string;
  title: string;
  type: string;
  category?: string;
  date: string;
  city?: string;
  postal_code?: string;
  status?: string;

  // Detailed fields that will come from /welcome endpoint
  procurement?: any;
  pricing?: any;
  order_description?: any;
  cpv_and_labels?: any;
  award_details?: any;
  abandonment_details?: any;
  vendor_details?: any;

  // Allow any additional fields from backend
  [key: string]: any;
}

// Search result interface specifically for search endpoint responses
export interface SearchResult {
  id: string;
  pub_id?: string;
  title: string;
  category?: string;
  main_cpv_code?: string;
  main_label?: string;
  full_text?: string;
  score: number;
  search_type: 'hybrid' | 'traditional' | 'semantic';
  trad_score?: number;
  semantic_score?: number;
}

// Search request parameters
export interface SearchParams {
  query: string;
  limit?: number;
  search_type?: 'traditional' | 'semantic' | 'hybrid';
}

export interface TenderDetails {
  // Basic tender fields
  id: string;
  publication_id?: string;
  search_index?: string;
  title?: MultilangTenderTitle;
  type?: string;
  category?: string;
  date?: string;
  city?: string;
  postal_code?: string;
  status?: string;

  // Detailed fields
  procurement?: any;
  pricing?: any;
  order_description?: any;
  cpv_and_labels?: any;
  award_details?: any;
  abandonment_details?: any;
  vendor_details?: any;

  // Allow any additional fields from backend
  [key: string]: any;
}

export enum TenderLanguage {
  EN = 'EN',
  DE = 'DE',
  FR = 'FR',
  IT = 'IT',
}
export interface MultilangTenderTitle {
  [TenderLanguage.EN]?: string;
  [TenderLanguage.DE]?: string;
  [TenderLanguage.FR]?: string;
  [TenderLanguage.IT]?: string;
}
