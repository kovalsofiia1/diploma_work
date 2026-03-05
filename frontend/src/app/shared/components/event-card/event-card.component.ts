import { Component, Input, OnInit } from '@angular/core';
import { PopularEventItem } from '../../interfaces/events/events.interface';
import { Router } from '@angular/router';
import { IonicModule } from '@ionic/angular';

@Component({
  selector: 'app-event-card',
  templateUrl: './event-card.component.html',
  styleUrls: ['./event-card.component.scss'],
  standalone: true,
  imports: [IonicModule]
})
export class EventCardComponent  implements OnInit {

  @Input() item: any;

  constructor(private router: Router) { }

  ngOnInit() {}

  openEvent(item: PopularEventItem): void {
    this.router.navigate(['/tabs/events', encodeURIComponent(item.uid)], {
      state: {
        item: {
          title: item.title,
          city: item.city,
          date: item.date,
          image: 'assets/shapes.svg',
          uid: item.uid,
        },
      },
    });
  }
}
