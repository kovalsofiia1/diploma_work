import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { EventsListPage } from './events-list.page';
import { EventDetailPage } from './event-detail.page';
import { EventCreatePage } from './event-create.page';

const routes: Routes = [
  {
    path: '',
    component: EventsListPage,
  },
  {
    path: 'create',
    component: EventCreatePage,
  },
  {
    path: ':uid',
    component: EventDetailPage,
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class EventsRoutingModule {}


