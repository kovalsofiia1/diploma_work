import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { EventInterface, EventKind } from '../events/interfaces/events.interface';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  standalone: false,

})
export class HomePage {
  organizedEventsCount = 15000;

  popularEvents: EventInterface[] = [
    
  ];

  constructor(private router: Router) {}


}
