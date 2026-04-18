import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { BookingRoutingModule } from './booking-routing.module';
import { BookingPage } from './booking.page';
import { VerifyTicketPage } from './verify/verify-ticket.page';
import { BookingCreatePage } from './create/booking-create.page';

@NgModule({
  imports: [
    CommonModule,
    IonicModule,
    BookingRoutingModule,
    BookingPage,
    BookingCreatePage,
    VerifyTicketPage,
  ],
})
export class BookingModule {}

