import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { FormsModule } from '@angular/forms';
import { HomePage } from './home.page';

import { HomePageRoutingModule } from './home-routing.module';
import { EventsListComponent } from 'src/app/shared/components/events-list/events-list.component';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    HomePageRoutingModule,
    EventsListComponent,
    AppHeaderComponent
  ],
  declarations: [HomePage]
})
export class HomePageModule {}
