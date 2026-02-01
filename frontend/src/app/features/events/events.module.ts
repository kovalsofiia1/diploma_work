import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { EventsRoutingModule } from './events-routing.module';
import { EventsListPage } from './events-list.page';

@NgModule({
  imports: [CommonModule, FormsModule, IonicModule, EventsRoutingModule, EventsListPage],
  declarations: [],
})
export class EventsModule {}

