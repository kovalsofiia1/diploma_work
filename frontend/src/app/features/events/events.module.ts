import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { EventsRoutingModule } from './events-routing.module';
import { EventsListPage } from './events-list.page';
import { EventDetailPage } from './event-detail.page';

@NgModule({
  imports: [CommonModule, FormsModule, IonicModule, EventsRoutingModule, EventsListPage, EventDetailPage],
  declarations: [],
})
export class EventsModule {}

