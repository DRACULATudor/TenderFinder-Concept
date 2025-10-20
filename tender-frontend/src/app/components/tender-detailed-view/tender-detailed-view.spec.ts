import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TenderDetailedView } from './tender-detailed-view';

describe('TenderDetailedView', () => {
  let component: TenderDetailedView;
  let fixture: ComponentFixture<TenderDetailedView>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TenderDetailedView]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TenderDetailedView);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
