import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { StoreModule } from '@ngrx/store';
import { EffectsModule } from '@ngrx/effects';

import { EventsRoutingModule } from './events-routing.module';
import { EventCreatePage } from './pages/create/event-create.page';
import { EventDetailPage } from './pages/detail/event-detail.page';
import { EventsListPage } from './pages/explore/events-list.page';

import { eventsReducer } from './redux/events.reducer';
import { EventsEffects } from './redux/events.effects';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    EventsRoutingModule,
    EventsListPage,
    EventDetailPage,
    EventCreatePage,
    StoreModule.forFeature('events', eventsReducer),
    EffectsModule.forFeature([EventsEffects])
  ],
  declarations: []
})
export class EventsModule {}

