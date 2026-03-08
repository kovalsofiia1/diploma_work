import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { EventsRoutingModule } from './events-routing.module';
import { EventCreatePage } from './create/event-create.page';
import { EventDetailPage } from './detail/event-detail.page';
import { EventsListPage } from './explore/events-list.page';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    EventsRoutingModule,
    EventsListPage,
    EventDetailPage,
    EventCreatePage
  ],
  declarations: [],
})
export class EventsModule {}

