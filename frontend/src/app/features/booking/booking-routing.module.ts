import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { BookingPage } from './booking.page';
import { AuthGuard } from '../../core/auth.guard';

const routes: Routes = [
  { path: '', component: BookingPage, canActivate: [AuthGuard] },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class BookingRoutingModule {}

