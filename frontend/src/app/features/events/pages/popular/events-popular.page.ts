import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { IonicModule } from '@ionic/angular';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';
import { EventsListComponent } from 'src/app/shared/components/events-list/events-list.component';
import { EventInterface } from '../../interfaces/events.interface';
import { EventsService } from '../../services/events.service';

@Component({
  selector: 'app-events-popular-page',
  templateUrl: './events-popular.page.html',
  styleUrls: ['./events-popular.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule, AppHeaderComponent, EventsListComponent],
})
export class EventsPopularPage implements OnInit {
  private eventsService = inject(EventsService);

  popularEvents: EventInterface[] = [];
  isLoading = false;
  hasError = false;

  ngOnInit(): void {
    this.loadPopularEvents();
  }

  loadPopularEvents(): void {
    this.isLoading = true;
    this.hasError = false;
    this.eventsService.getPopularEvents(24).subscribe({
      next: (response) => {
        this.popularEvents = response.items ?? [];
      },
      error: () => {
        this.hasError = true;
        this.isLoading = false;
        this.popularEvents = [];
      },
      complete: () => {
        this.isLoading = false;
      },
    });
  }
}
