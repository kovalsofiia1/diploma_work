import { Component, Input, OnInit } from '@angular/core';
import { PopularEventItem } from '../../interfaces/events/events.interface';
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
export class EventsListComponent  implements OnInit {

  @Input() popularEvents: PopularEventItem[] = [];
  
  constructor() { }

  ngOnInit() {}

  trackByUid(_: number, item: PopularEventItem): string {
    return item.uid;
  }
}
