import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { BookingRoutingModule } from './booking-routing.module';
import { BookingPage } from './booking.page';

@NgModule({
  imports: [CommonModule, IonicModule, BookingRoutingModule, BookingPage],
})
export class BookingModule {}

