import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { FormsModule } from '@angular/forms';
import { HomePage } from './home.page';

import { HomePageRoutingModule } from './home-routing.module';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';
import { EventCardComponent } from 'src/app/shared/components/event-card/event-card.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    HomePageRoutingModule,
    EventCardComponent,
    AppHeaderComponent
  ],
  declarations: [HomePage]
})
export class HomePageModule {}
