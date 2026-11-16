import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { RouterModule, provideRouter } from '@angular/router';
import { IonicModule } from '@ionic/angular';

import { AppComponent } from './app.component';

describe('AppComponent', () => {
  let fixture: ComponentFixture<AppComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [AppComponent],
      imports: [IonicModule.forRoot(), RouterModule],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
      schemas: [CUSTOM_ELEMENTS_SCHEMA],
    }).compileComponents();
  });

  afterEach(() => {
    fixture?.destroy();
    fixture?.nativeElement.remove();
  });

  it('should create the app with an Ionic menu outlet', async () => {
    fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    document.body.appendChild(fixture.nativeElement);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(app).toBeTruthy();
    const outlet = fixture.nativeElement.querySelector('ion-router-outlet#main-content');
    const menu = fixture.nativeElement.querySelector('ion-menu') as HTMLElement;
    expect(outlet).not.toBeNull();
    expect(document.getElementById('main-content')).toBe(outlet);
    const ionicMenu = menu as HTMLElement & {
      contentId: string;
      componentOnReady: () => Promise<unknown>;
    };
    expect(ionicMenu.contentId).toBe('main-content');
    await ionicMenu.componentOnReady();
  });
});
