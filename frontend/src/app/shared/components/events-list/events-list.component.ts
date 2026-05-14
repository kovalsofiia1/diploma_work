import { Component, Input } from '@angular/core';
import { EventInterface } from 'src/app/features/events/interfaces/events.interface';
import { EventCardComponent } from '../event-card/event-card.component';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';

@Component({
  selector: 'app-events-list',
  templateUrl: './events-list.component.html',
  styleUrls: ['./events-list.component.scss'],
  standalone: true,
  imports: [EventCardComponent, CommonModule, IonicModule]
})
export class EventsListComponent {
  @Input() events: EventInterface[] = [];

  trackByUid(_: number, item: EventInterface): string {
    return item.uid ?? '';
  }
}
