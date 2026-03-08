import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { EventsExploreRoutingModule } from './explore-routing.module';
import { EventsListPage } from './events-list.page';
import { EventDetailPage } from '../detail/event-detail.page';

@NgModule({
  imports: [CommonModule, IonicModule, EventsExploreRoutingModule, EventsListPage, EventDetailPage],
})
export class EventsExploreModule {}

