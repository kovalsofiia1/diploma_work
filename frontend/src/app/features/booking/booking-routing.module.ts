import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { BookingPage } from './booking.page';
import { AuthGuard } from '../../core/auth.guard';
import { VerifyTicketPage } from './verify/verify-ticket.page';

const routes: Routes = [
  { path: '', component: BookingPage, canActivate: [AuthGuard] },
  { path: 'verify', component: VerifyTicketPage, canActivate: [AuthGuard] },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class BookingRoutingModule {}

