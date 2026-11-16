import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterModule, provideRouter } from '@angular/router';
import { IonicModule } from '@ionic/angular';

import { AppComponent } from './app.component';

describe('AppComponent', () => {
  let fixture: ComponentFixture<AppComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [AppComponent],
      imports: [IonicModule.forRoot(), RouterModule],
      providers: [provideRouter([])],
      schemas: [CUSTOM_ELEMENTS_SCHEMA],
    }).compileComponents();
  });

  afterEach(() => {
    fixture?.destroy();
    fixture?.nativeElement.remove();
  });

  it('creates the app with an Ionic menu connected to its router outlet', async () => {
    fixture = TestBed.createComponent(AppComponent);
    document.body.appendChild(fixture.nativeElement);
    fixture.detectChanges();
    await fixture.whenStable();

    const outlet = fixture.nativeElement.querySelector('ion-router-outlet#main-content');
    const menu = fixture.nativeElement.querySelector('ion-menu') as HTMLElement & {
      contentId: string;
      componentOnReady: () => Promise<unknown>;
    };

    expect(outlet).not.toBeNull();
    expect(document.getElementById('main-content')).toBe(outlet);
    expect(menu.contentId).toBe('main-content');
    await menu.componentOnReady();
  });
});
