import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { EventCreatePage } from './event-create.page';

const routes: Routes = [
  {
    path: '',
    component: EventCreatePage,
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class EventsCreateRoutingModule {}

