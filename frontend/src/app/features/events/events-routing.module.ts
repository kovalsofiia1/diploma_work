import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { EventsListPage } from './events-list.page';

const routes: Routes = [
  {
    path: '',
    component: EventsListPage,
  },
  {
    path: ':uid',
    component: EventsListPage, // placeholder for detail route wiring later
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class EventsRoutingModule {}


