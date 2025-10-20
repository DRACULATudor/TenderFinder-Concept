import { Component, OnInit, signal, ViewChild, ElementRef, AfterViewInit, inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { TenderService } from '../../services/tender.service';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

// Register Chart.js components
Chart.register(...registerables);

@Component({
  selector: 'app-tender-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="chart-container">
      <div class="chart-header">
        <h3>Tender Categories Overview</h3>
        <div class="chart-controls">
          <button 
            *ngFor="let type of chartTypes" 
            [class]="'chart-btn ' + (selectedChartType() === type.value ? 'active' : '')"
            (click)="changeChartType(type.value)">
            {{ type.label }}
          </button>
        </div>
      </div>
      
      <div class="chart-wrapper">
        <canvas #chartCanvas></canvas>
      </div>
      
      <div class="chart-stats" *ngIf="stats()">
        <div class="stat-grid">
          <div class="stat-card">
            <div class="stat-value">{{ getTotalCategories() }}</div>
            <div class="stat-label">Categories</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ getMostPopularCategory().name }}</div>
            <div class="stat-label">Top Category</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ getMostPopularCategory().count }}</div>
            <div class="stat-label">Top Count</div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .chart-container {
      background: white;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      margin: 20px 0;
    }

    .chart-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 16px;
    }

    .chart-header h3 {
      margin: 0;
      color: #333;
      font-size: 1.5rem;
      font-weight: 600;
    }

    .chart-controls {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .chart-btn {
      padding: 8px 16px;
      border: 2px solid #e0e0e0;
      background: white;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.9rem;
      font-weight: 500;
      transition: all 0.3s ease;
    }

    .chart-btn:hover {
      border-color: #667eea;
      color: #667eea;
    }

    .chart-btn.active {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border-color: transparent;
    }

    .chart-wrapper {
      position: relative;
      height: 400px;
      margin-bottom: 24px;
    }

    .chart-stats {
      border-top: 1px solid #e0e0e0;
      padding-top: 20px;
    }

    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
    }

    .stat-card {
      text-align: center;
      padding: 16px;
      background: #f8f9fa;
      border-radius: 8px;
      border: 1px solid #e9ecef;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: #333;
      margin-bottom: 4px;
    }

    .stat-label {
      font-size: 0.85rem;
      color: #666;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    @media (max-width: 768px) {
      .chart-container {
        padding: 16px;
        margin: 16px 0;
      }

      .chart-header {
        flex-direction: column;
        align-items: stretch;
      }

      .chart-header h3 {
        text-align: center;
        font-size: 1.3rem;
      }

      .chart-controls {
        justify-content: center;
      }

      .chart-wrapper {
        height: 300px;
      }

      .stat-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class TenderChartComponent implements OnInit, AfterViewInit {
  @ViewChild('chartCanvas', { static: true }) chartCanvas!: ElementRef<HTMLCanvasElement>;
  
  private chart: Chart | null = null;
  
  stats = signal<any>({
    total_tenders: 0,
    by_type: {},
    by_category: {},
    by_status: {},
    by_city: {}
  });

  selectedChartType = signal<string>('doughnut');
  
  chartTypes = [
    { value: 'doughnut', label: 'Doughnut' },
    { value: 'bar', label: 'Bar' },
    { value: 'pie', label: 'Pie' }
  ];

  // Color palette for categories
  private categoryColors = [
    '#667eea', '#764ba2', '#f093fb', '#f5576c',
    '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
    '#ffecd2', '#fcb69f', '#a8edea', '#fed6e3',
    '#ff9a9e', '#fecfef', '#ffeaa7', '#fd79a8'
  ];

  private tenderService = inject(TenderService);
  private platformId = inject(PLATFORM_ID);

  ngOnInit(): void {
    this.loadStats();
  }

  ngAfterViewInit(): void {
    // Chart will be created after stats are loaded and only in browser
  }

  loadStats(): void {
    this.tenderService.getStats().subscribe({
      next: (data) => {
        this.stats.set(data);
        // Only create chart in browser environment
        if (isPlatformBrowser(this.platformId)) {
          this.createChart();
        }
      },
      error: (error) => {
        console.error('Error loading stats:', error);
      }
    });
  }

  changeChartType(type: string): void {
    this.selectedChartType.set(type);
    // Only create chart in browser environment
    if (isPlatformBrowser(this.platformId)) {
      this.createChart();
    }
  }

  private createChart(): void {
    // Ensure we're in browser environment before creating charts
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    if (this.chart) {
      this.chart.destroy();
    }

    // Ensure canvas element exists
    if (!this.chartCanvas?.nativeElement) {
      return;
    }

    const categories = this.stats().by_category || {};
    const categoryEntries = Object.entries(categories);
    
    if (categoryEntries.length === 0) {
      return;
    }

    // Sort categories by count (descending)
    const sortedCategories = categoryEntries.sort((a, b) => (b[1] as number) - (a[1] as number));
    
    const labels = sortedCategories.map(([category, _]) => 
      category === 'Unknown' ? 'Other/Unknown' : this.formatCategoryName(category)
    );
    const data = sortedCategories.map(([_, count]) => count as number);
    const colors = this.categoryColors.slice(0, labels.length);

    const chartType = this.selectedChartType();
    let config: ChartConfiguration;

    if (chartType === 'bar') {
      config = {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Number of Tenders',
            data,
            backgroundColor: colors,
            borderColor: colors.map(color => color + '80'),
            borderWidth: 2,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          elements: {
            bar: {
              borderRadius: 4,
            }
          },
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              callbacks: {
                label: (context) => `${context.parsed.y} tenders`
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                stepSize: 1
              },
              grid: {
                color: '#f0f0f0'
              }
            },
            x: {
              grid: {
                display: false
              },
              ticks: {
                maxRotation: 45,
                minRotation: 0
              }
            }
          }
        }
      };
    } else {
      config = {
        type: chartType === 'doughnut' ? 'doughnut' : 'pie',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: colors,
            borderColor: '#ffffff',
            borderWidth: 2,
            hoverBorderWidth: 3,
            hoverBorderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                padding: 20,
                usePointStyle: true,
                font: {
                  size: 11
                }
              }
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const dataArray = context.dataset.data as number[];
                  const total = dataArray.reduce((a: number, b: number) => a + b, 0);
                  const value = context.parsed as number;
                  const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0';
                  return `${context.label}: ${value} (${percentage}%)`;
                }
              }
            }
          },
          ...(chartType === 'doughnut' && { cutout: '60%' })
        }
      };
    }

    this.chart = new Chart(this.chartCanvas.nativeElement, config);
  }

  private formatCategoryName(category: string): string {
    return category.charAt(0).toUpperCase() + category.slice(1);
  }

  getTotalCategories(): number {
    return Object.keys(this.stats().by_category || {}).length;
  }

  getMostPopularCategory(): { name: string, count: number } {
    const categories = this.stats().by_category || {};
    const entries = Object.entries(categories);
    
    if (entries.length === 0) {
      return { name: 'N/A', count: 0 };
    }

    const [name, count] = entries.reduce((max, current) => 
      (current[1] as number) > (max[1] as number) ? current : max
    );

    return { 
      name: name === 'Unknown' ? 'Other/Unknown' : this.formatCategoryName(name), 
      count: count as number 
    };
  }
}