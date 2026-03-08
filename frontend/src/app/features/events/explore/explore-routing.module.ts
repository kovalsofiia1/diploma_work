import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { EventsListPage } from './events-list.page';
import { EventDetailPage } from '../detail/event-detail.page';

const routes: Routes = [
  {
    path: '',
    component: EventsListPage,
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
export class EventsExploreRoutingModule {}

