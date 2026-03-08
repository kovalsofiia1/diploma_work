import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { EventsCreateRoutingModule } from './create-routing.module';
import { EventCreatePage } from './event-create.page';

@NgModule({
  imports: [CommonModule, IonicModule, EventsCreateRoutingModule, EventCreatePage],
})
export class EventsCreateModule {}

