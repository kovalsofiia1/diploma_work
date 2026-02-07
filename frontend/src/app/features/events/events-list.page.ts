import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-events-list',
  templateUrl: './events-list.page.html',
  styleUrls: ['./events-list.page.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule, RouterModule],
})
export class EventsListPage {
  items = [
    {
      title: 'Океанаріум Львів',
      city: 'Львів',
      date: '2026-01-29 11:00',
      image: 'https://images.karabas.com/some_image.jpeg',
      uid: 'external:1',
    },
    {
      title: 'Мій Music Hall',
      city: 'Київ',
      date: '2026-04-04 17:00',
      image: 'https://images.karabas.com/some_image2.jpeg',
      uid: 'external:2',
    },
  ];
}

