import { Component, OnInit, signal, inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { TenderListComponent } from '../tender-list/tender-list.component';
import { TenderChartComponent } from '../tender-chart/tender-chart.component';
import { TenderService } from '../../services/tender.service';

@Component({
  selector: 'app-welcome',
  standalone: true,
  imports: [TenderListComponent, TenderChartComponent, CommonModule],
  template: `
    <div class="welcome-container">
      <header class="welcome-header">
        <div class="hero-section">
          <h1 class="main-title">Welcome to TenderFinder</h1>
          <p class="subtitle">Discover and explore tender opportunities with ease</p>
          <div class="stats-bar">
            <div class="stat-item">
              <span class="stat-number">{{ stats().total_tenders || 0 }}</span>
              <span class="stat-label">Active Tenders</span>
            </div>
          </div>
        </div>
      </header>
      
      <main class="main-content">
        <section class="intro-section">
          <h2>Explore Tender Types and Opportunities</h2>
          <p>Browse through various tender types and find the perfect opportunities for your business. Our platform obtains tenders from multiple sources to provide you with complete coverage.</p>
        </section>
        
        <!-- Add the chart component here -->
        <app-tender-chart></app-tender-chart>
        
        <app-tender-list></app-tender-list>
      </main>
    </div>
  `,
  styles: [`
    .welcome-container {
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .welcome-header {
      padding: 60px 20px;
      text-align: center;
      color: white;
    }

    .hero-section {
      max-width: 800px;
      margin: 0 auto;
    }

    .main-title {
      font-size: 3.5rem;
      font-weight: 700;
      margin-bottom: 20px;
      text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
      animation: fadeInUp 1s ease-out;
    }

    .subtitle {
      font-size: 1.4rem;
      margin-bottom: 40px;
      opacity: 0.9;
      animation: fadeInUp 1s ease-out 0.2s both;
    }

    .stats-bar {
      display: flex;
      justify-content: center;
      gap: 60px;
      margin-top: 40px;
      animation: fadeInUp 1s ease-out 0.4s both;
    }

    .stat-item {
      text-align: center;
    }

    .stat-number {
      display: block;
      font-size: 2.5rem;
      font-weight: 700;
      margin-bottom: 5px;
    }

    .stat-label {
      font-size: 1rem;
      opacity: 0.8;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .main-content {
      background: #f8f9fa;
      min-height: calc(100vh - 300px);
      padding: 60px 20px;
    }

    .intro-section {
      max-width: 800px;
      margin: 0 auto 50px;
      text-align: center;
    }

    .intro-section h2 {
      font-size: 2.5rem;
      color: #333;
      margin-bottom: 20px;
      font-weight: 600;
    }

    .intro-section p {
      font-size: 1.2rem;
      color: #666;
      line-height: 1.6;
      max-width: 600px;
      margin: 0 auto;
    }

    @keyframes fadeInUp {
      from {
        opacity: 0;
        transform: translateY(30px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @media (max-width: 768px) {
      .main-title {
        font-size: 2.5rem;
      }
      
      .subtitle {
        font-size: 1.1rem;
      }
      
      .stats-bar {
        flex-direction: column;
        gap: 30px;
      }
      
      .stat-number {
        font-size: 2rem;
      }
      
      .intro-section h2 {
        font-size: 2rem;
      }
      
      .intro-section p {
        font-size: 1.1rem;
      }
    }

    @media (max-width: 480px) {
      .welcome-header {
        padding: 40px 15px;
      }
      
      .main-content {
        padding: 40px 15px;
      }
      
      .main-title {
        font-size: 2rem;
      }
      
      .stats-bar {
        gap: 20px;
      }
    }
  `]
})
export class WelcomeComponent implements OnInit {
  stats = signal<any>({
    total_tenders: 0,
    by_type: {},
    by_category: {},
    by_status: {},
    by_city: {}
  });

  private tenderService = inject(TenderService);
  private platformId = inject(PLATFORM_ID);

  ngOnInit(): void {
    // Only load data on the client side, not during SSR
    if (isPlatformBrowser(this.platformId)) {
      this.loadStats();
    }
  }

  loadStats(): void {
    this.tenderService.getStats().subscribe({
      next: (data) => {
        this.stats.set(data);
      },
      error: (error) => {
        console.error('Error loading stats:', error);
      }
    });
  }

  getTypeCount(): number {
    return Object.keys(this.stats().by_type || {}).length;
  }

  getCityCount(): number {
    return Object.keys(this.stats().by_city || {}).length;
  }
}